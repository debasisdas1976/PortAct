"""
Global Liquidity Service — fetches M2 money supply from FRED and asset price
history from Yahoo Finance for the Liquidity Insight dashboard.

Data is cached weekly in AppSettings (as JSON strings) so the dashboard loads
instantly without hitting external APIs on every request.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# FRED series IDs for M2 money supply (monthly, seasonally adjusted where available)
FRED_M2_SERIES: Dict[str, str] = {
    "US": "M2SL",               # Billions of US Dollars           — starts Jan 1959
    "EU": "MABMM301EZM189S",    # Millions of Euro                 — starts Jan 1980
    "CN": "MYAGM2CNM189S",      # Hundreds of millions of CNY      — starts Jan 1978
    "JP": "MYAGM2JPM189S",      # Billions of Japanese Yen         — starts Jan 1955
    "IN": "MYAGM2INM189N",      # Hundreds of millions of INR (NSA)— starts Jan 1972
}

# Fallback series IDs to try (in order) when the primary series returns no data.
# India is not in FRED's standard IMF IFS M2 set, so we try several known alternatives.
FRED_M2_FALLBACKS: Dict[str, List[str]] = {
    "IN": [
        "MYAGM2INM189N",    # IMF IFS — may not be published
        "MYAGM2INM189S",    # IMF IFS seasonally adjusted variant
        "MABMM301INM189N",  # OECD MEI — India covered as associate
        "MABMM301INM189S",  # OECD MEI seasonally adjusted
    ],
}

# ── National Debt series ──────────────────────────────────────────────────────
# US: GFDEBTN — Gross Federal Debt, Millions of Dollars, Quarterly (very current)
FRED_DEBT_SERIES: Dict[str, Dict] = {
    "US": {
        "series_id": "GFDEBTN",
        "factor":    1e-6,        # Millions USD → Trillion USD
        "unit":      "Trillion USD",
        "label":     "US Federal Debt",
    },
}
_CACHE_DEBT_KEY = "liquidity_debt_cache"

# Conversion factors: raw FRED value × factor = Trillions of native currency.
# Each factor is derived from the series unit documented by FRED/IMF/OECD.
FRED_SERIES_TRILLION_FACTOR: Dict[str, float] = {
    "M2SL":              1e-3,   # Billions USD       → Trillion USD
    "MABMM301EZM189S":   1e-6,   # Millions EUR       → Trillion EUR
    "MYAGM2CNM189S":     1e-4,   # ×100M CNY          → Trillion CNY
    "MYAGM2JPM189S":     1e-3,   # Billions JPY       → Trillion JPY
    "MYAGM2INM189N":     1e-4,   # ×100M INR          → Trillion INR
    "MYAGM2INM189S":     1e-4,   # ×100M INR          → Trillion INR
    "MABMM301INM189N":   1e-6,   # Millions INR       → Trillion INR
    "MABMM301INM189S":   1e-6,   # Millions INR       → Trillion INR
}

# After normalization all values are stored as "Trillion <native currency>"
FRED_M2_UNITS: Dict[str, str] = {
    "US": "Trillion USD",
    "EU": "Trillion EUR",
    "CN": "Trillion CNY",
    "JP": "Trillion JPY",
    "IN": "Trillion INR",
}

_CACHE_M2_KEY = "liquidity_m2_cache"
_CACHE_ASSETS_KEY = "liquidity_assets_cache"
_CACHE_UPDATED_KEY = "liquidity_cache_updated_at"
_CACHE_MAX_AGE_DAYS = 7
# Bump this whenever the cached data format changes to force a refresh.
_CACHE_VERSION = "2"
_CACHE_VERSION_KEY = "liquidity_cache_version"

_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_fred_api_key(db: Session) -> str:
    """Read FRED API key from AppSettings; return empty string if not set."""
    row = db.query(AppSettings).filter(AppSettings.key == "fred_api_key").first()
    return (row.value or "").strip() if row else ""


def _read_cache(db: Session, key: str) -> Optional[Any]:
    """Read a JSON value stored in AppSettings; returns None on miss/error."""
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row and row.value:
        try:
            return json.loads(row.value)
        except Exception:
            pass
    return None


def _write_cache(db: Session, key: str, value: Any, label: str = "") -> None:
    """Upsert a JSON value into AppSettings."""
    json_value = json.dumps(value)
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row:
        row.value = json_value
    else:
        db.add(AppSettings(
            key=key,
            value=json_value,
            value_type="string",
            category="liquidity",
            label=label or key,
        ))
    db.commit()


def _is_cache_fresh(db: Session) -> bool:
    """Return True if the cache was updated less than _CACHE_MAX_AGE_DAYS ago."""
    row = db.query(AppSettings).filter(AppSettings.key == _CACHE_UPDATED_KEY).first()
    if not row or not row.value:
        return False
    try:
        updated_at = datetime.fromisoformat(row.value)
        return (datetime.utcnow() - updated_at).days < _CACHE_MAX_AGE_DAYS
    except Exception:
        return False


# ── External data fetchers ────────────────────────────────────────────────────


def _fetch_fred_series(api_key: str, series_id: str) -> tuple:
    """Fetch monthly observations from FRED for one series (maximum history).

    Returns (data: List[Dict], error: str | None).
    On success error is None; on failure data is [] and error contains the FRED message.
    """
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": "1950-01-01",
        "frequency": "m",
        "aggregation_method": "avg",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{FRED_BASE_URL}/series/observations", params=params)
            if not r.is_success:
                # Capture FRED's own error message (e.g. "Bad Request. The series does not exist.")
                try:
                    fred_msg = r.json().get("error_message", r.text[:300])
                except Exception:
                    fred_msg = r.text[:300]
                err = f"HTTP {r.status_code}: {fred_msg}"
                logger.error("FRED fetch failed for %s — %s", series_id, err)
                return [], err
            observations = r.json().get("observations", [])
            result = []
            for obs in observations:
                raw = obs.get("value", ".")
                if raw and raw != ".":
                    try:
                        result.append({"date": obs["date"], "value": float(raw)})
                    except (ValueError, TypeError):
                        pass
            return result, None
    except Exception as exc:
        err = str(exc)
        logger.error("FRED fetch exception for %s: %s", series_id, err)
        return [], err


def _fetch_fred_series_native(api_key: str, series_id: str) -> tuple:
    """Like _fetch_fred_series but uses the series' native frequency (no resampling)."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": "1950-01-01",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{FRED_BASE_URL}/series/observations", params=params)
            if not r.is_success:
                try:
                    fred_msg = r.json().get("error_message", r.text[:300])
                except Exception:
                    fred_msg = r.text[:300]
                err = f"HTTP {r.status_code}: {fred_msg}"
                logger.error("FRED fetch failed for %s — %s", series_id, err)
                return [], err
            observations = r.json().get("observations", [])
            result = []
            for obs in observations:
                raw = obs.get("value", ".")
                if raw and raw != ".":
                    try:
                        result.append({"date": obs["date"], "value": float(raw)})
                    except (ValueError, TypeError):
                        pass
            return result, None
    except Exception as exc:
        err = str(exc)
        logger.error("FRED fetch exception for %s: %s", series_id, err)
        return [], err


def _fetch_yahoo_monthly(symbol: str, range_: str = "15y") -> List[Dict]:
    """Fetch monthly closing prices from Yahoo Finance v8 chart API."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1mo", "range": range_, "includePrePost": "false"}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, params=params, headers=_YF_HEADERS)
            r.raise_for_status()
            result_data = r.json()["chart"]["result"][0]
            timestamps = result_data["timestamp"]
            closes = result_data["indicators"]["quote"][0]["close"]
            output = []
            for ts, close in zip(timestamps, closes):
                if close is not None:
                    dt = datetime.utcfromtimestamp(ts)
                    output.append({
                        "date": dt.strftime("%Y-%m-01"),
                        "value": round(float(close), 4),
                    })
            return output
    except Exception as exc:
        logger.error("Yahoo Finance monthly history failed for %s: %s", symbol, exc)
        return []


# ── Public API ────────────────────────────────────────────────────────────────


def refresh_liquidity_data(db: Session) -> None:
    """Fetch fresh M2 and asset price data from FRED + Yahoo Finance, then cache it."""
    fred_key = _get_fred_api_key(db)

    # ── M2 money supply from FRED ──
    m2_data: Dict[str, List[Dict]] = {}
    m2_errors: Dict[str, str] = {}

    if fred_key:
        for country, primary_series in FRED_M2_SERIES.items():
            # Build the list of series IDs to try: use FALLBACKS if defined, else just primary
            candidates = FRED_M2_FALLBACKS.get(country, [primary_series])
            # Always start with the primary in case fallbacks list omits it
            if primary_series not in candidates:
                candidates = [primary_series] + candidates

            fetched = False
            last_err = ""
            for series_id in candidates:
                obs, err = _fetch_fred_series(fred_key, series_id)
                if obs:
                    # Normalize to Trillions of native currency so the frontend
                    # can display values directly without unit-specific conversion.
                    factor = FRED_SERIES_TRILLION_FACTOR.get(series_id, 1.0)
                    m2_data[country] = [
                        {"date": o["date"], "value": round(o["value"] * factor, 6)}
                        for o in obs
                    ]
                    logger.info(
                        "FRED M2 %s (%s): %d observations → Trillion factor %.2e",
                        country, series_id, len(obs), factor,
                    )
                    fetched = True
                    break
                last_err = f"{series_id}: {err}"
                logger.warning("FRED M2 %s (%s): no data — %s", country, series_id, err)

            if not fetched:
                tried = ", ".join(candidates)
                m2_errors[country] = f"No data from any series [{tried}]. Last error: {last_err}"
                logger.error("FRED M2 %s: all candidates failed", country)
    else:
        logger.warning("No FRED API key configured — M2 data will not be fetched")

    _write_cache(db, "liquidity_m2_errors_cache", m2_errors, "M2 Fetch Errors")

    # ── National debt from FRED ──
    debt_data: Dict[str, List[Dict]] = {}
    if fred_key:
        for country, cfg in FRED_DEBT_SERIES.items():
            obs, err = _fetch_fred_series_native(fred_key, cfg["series_id"])
            if obs:
                factor = cfg["factor"]
                debt_data[country] = [
                    {"date": o["date"], "value": round(o["value"] * factor, 6)}
                    for o in obs
                ]
                logger.info("FRED Debt %s (%s): %d observations", country, cfg["series_id"], len(obs))
            else:
                logger.warning("FRED Debt %s (%s): no data — %s", country, cfg["series_id"], err)
    _write_cache(db, _CACHE_DEBT_KEY, debt_data, "National Debt Cache")

    # ── Asset price history from Yahoo Finance ──
    spx = _fetch_yahoo_monthly("^GSPC")
    gold = _fetch_yahoo_monthly("GC=F")
    btc = _fetch_yahoo_monthly("BTC-USD")

    _write_cache(db, _CACHE_M2_KEY, m2_data, "Global M2 Money Supply Cache")
    _write_cache(db, _CACHE_ASSETS_KEY, {"spx": spx, "gold": gold, "btc": btc}, "Asset Price History Cache")

    # ── Update the timestamp ──
    ts = datetime.utcnow().isoformat()
    row = db.query(AppSettings).filter(AppSettings.key == _CACHE_UPDATED_KEY).first()
    if row:
        row.value = ts
    else:
        db.add(AppSettings(
            key=_CACHE_UPDATED_KEY,
            value=ts,
            value_type="string",
            category="liquidity",
            label="Liquidity Cache Last Updated",
        ))
    db.commit()
    _write_cache(db, _CACHE_VERSION_KEY, _CACHE_VERSION, "Liquidity Cache Version")
    logger.info("Liquidity data cache refreshed successfully")


def _cached_series_complete(db: Session) -> bool:
    """Return False if any series in FRED_M2_SERIES is missing from the cached M2 data."""
    cached = _read_cache(db, _CACHE_M2_KEY)
    if not cached:
        return False
    missing = [k for k in FRED_M2_SERIES if k not in cached]
    if missing:
        logger.info("Cached M2 missing series %s — will refresh", missing)
        return False
    return True


def _cache_version_ok(db: Session) -> bool:
    """Return True if the cached data was built with the current cache version."""
    # Use _read_cache so the JSON-parsed value is compared (not the raw JSON string).
    return _read_cache(db, _CACHE_VERSION_KEY) == _CACHE_VERSION


# Approximate Trillion-unit ranges per country used for auto-detection.
# These bounds are generous to cover historical values and future growth.
_COUNTRY_TRILLION_RANGE: Dict[str, tuple] = {
    "US": (3, 500),
    "EU": (2, 300),
    "CN": (20, 20_000),
    "JP": (100, 100_000),
    "IN": (2, 10_000),
}

# Candidate factors tried in order when auto-normalizing legacy cache.
_AUTO_NORM_FACTORS = [1e-3, 1e-4, 1e-6]


def _normalize_m2_cache_inplace(db: Session) -> None:
    """Convert raw FRED values in the M2 cache to Trillion units without re-fetching.

    This runs instantly (no external API calls) and handles the case where the
    cache was populated by old backend code that stored raw FRED values.
    If the values are already in Trillion the function is a no-op.
    """
    m2 = _read_cache(db, _CACHE_M2_KEY)
    if not m2:
        logger.info("No M2 cache to normalize — skipping in-place normalization")
        _write_cache(db, _CACHE_VERSION_KEY, _CACHE_VERSION, "Liquidity Cache Version")
        return

    normalized: Dict[str, list] = {}
    for country, obs in m2.items():
        if not obs:
            normalized[country] = obs
            continue
        latest = obs[-1]["value"]
        lo, hi = _COUNTRY_TRILLION_RANGE.get(country, (0.001, 1_000_000))
        if lo <= latest <= hi:
            # Already in Trillion range — keep as-is.
            normalized[country] = obs
            logger.info("M2 %s: value %.4g already in Trillion range — no conversion", country, latest)
            continue
        # Find the factor that brings the latest value into the expected range.
        applied = False
        for factor in _AUTO_NORM_FACTORS:
            converted = latest * factor
            if lo <= converted <= hi:
                normalized[country] = [
                    {"date": o["date"], "value": round(o["value"] * factor, 6)}
                    for o in obs
                ]
                logger.info(
                    "M2 %s: normalizing %.4g → %.4g T (factor %.2e)",
                    country, latest, converted, factor,
                )
                applied = True
                break
        if not applied:
            logger.warning("M2 %s: could not auto-normalize %.4g — keeping raw", country, latest)
            normalized[country] = obs

    _write_cache(db, _CACHE_M2_KEY, normalized, "Global M2 Money Supply Cache")
    _write_cache(db, _CACHE_VERSION_KEY, _CACHE_VERSION, "Liquidity Cache Version")
    logger.info("In-place M2 Trillion normalization complete")


def _ensure_trillion(m2: Dict[str, list]) -> Dict[str, list]:
    """Return M2 data guaranteed to be in Trillion units.

    Applied on every API response so the frontend always receives Trillion values,
    regardless of whether the cache was built by old or new backend code.
    Uses per-country expected ranges to detect raw FRED values and apply the
    correct factor automatically.
    """
    result: Dict[str, list] = {}
    for country, obs in m2.items():
        if not obs:
            result[country] = obs
            continue
        latest = obs[-1]["value"]
        lo, hi = _COUNTRY_TRILLION_RANGE.get(country, (0.001, 1_000_000))
        if lo <= latest <= hi:
            result[country] = obs  # already in Trillion
            continue
        applied = False
        for factor in _AUTO_NORM_FACTORS:
            converted = latest * factor
            if lo <= converted <= hi:
                result[country] = [
                    {"date": o["date"], "value": round(o["value"] * factor, 6)}
                    for o in obs
                ]
                logger.info("M2 %s: on-the-fly Trillion conversion %.4g → %.4g T (%.2e)", country, latest, converted, factor)
                applied = True
                break
        if not applied:
            logger.warning("M2 %s: could not convert %.4g to Trillion — returning raw", country, latest)
            result[country] = obs
    return result


def get_liquidity_data(db: Session) -> Dict[str, Any]:
    """Return cached liquidity data, refreshing from APIs if the cache is stale or incomplete."""
    if not _cache_version_ok(db) or not _is_cache_fresh(db) or not _cached_series_complete(db):
        try:
            refresh_liquidity_data(db)
        except Exception as exc:
            logger.error("Liquidity refresh failed: %s", exc)

    m2_raw = _read_cache(db, _CACHE_M2_KEY) or {}
    assets = _read_cache(db, _CACHE_ASSETS_KEY) or {}
    debt = _read_cache(db, _CACHE_DEBT_KEY) or {}
    m2_errors = _read_cache(db, "liquidity_m2_errors_cache") or {}
    row = db.query(AppSettings).filter(AppSettings.key == _CACHE_UPDATED_KEY).first()
    last_updated = row.value if row else None
    fred_key = _get_fred_api_key(db)

    return {
        "m2": _ensure_trillion(m2_raw),   # always in Trillion units for the frontend
        "assets": assets,
        "debt": debt,
        "debt_meta": {k: {"unit": v["unit"], "label": v["label"]} for k, v in FRED_DEBT_SERIES.items()},
        "m2_errors": m2_errors,
        "last_updated": last_updated,
        "fred_configured": bool(fred_key),
        "m2_series": list(FRED_M2_SERIES.keys()),
        "m2_units": FRED_M2_UNITS,
    }
