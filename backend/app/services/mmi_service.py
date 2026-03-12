"""
Market sentiment indices service.

1. India Market Mood Index (MMI) — scraped from Tickertape's SSR page.
2. Bitcoin Fear & Greed Index  — fetched from Alternative.me's free API.

Both are cached in macro_data_points (series + YYYY-MM-DD period) so each
source is only hit once per day.

Storage layout in macro_data_points
------------------------------------
  series  : 'india_mmi'  |  'btc_fng'
  period  : 'YYYY-MM-DD'  (today's date — unique key per series)
  label   : sentiment zone, e.g. 'Extreme Fear'
  value   : numeric score, e.g. 22.65 / 18.0
"""

import re
from datetime import date, timezone, timedelta
from loguru import logger
import httpx

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.macro_data import MacroDataPoint
from app.models.app_settings import AppSettings

# ── Constants ────────────────────────────────────────────────────────────────

_MMI_SERIES       = "india_mmi"
_FNG_SERIES       = "btc_fng"        # Alternative.me cache key
_FNG_CMC_SERIES   = "btc_fng_cmc"   # CoinMarketCap cache key (separate so switching sources works instantly)
_US_FNG_SERIES    = "us_fng"         # CNN Fear & Greed cache key

_TICKERTAPE_PAGE  = "https://www.tickertape.in/market-mood-index"
_ALTME_FNG_URL    = "https://api.alternative.me/fng/?limit=1"
_CMC_FNG_URL      = "https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest"
_CNN_FNG_URL      = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

_MMI_ZONE_MAP = {
    "ef":    "Extreme Fear",
    "fear":  "Fear",
    "greed": "Greed",
    "eg":    "Extreme Greed",
}
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# IST is UTC+5:30 — use this to decide "today" for Indian market data
_IST = timezone(timedelta(hours=5, minutes=30))


# ── Shared helpers ────────────────────────────────────────────────────────────

def _today_ist() -> str:
    """Return today's date in IST as 'YYYY-MM-DD'."""
    return date.today().strftime("%Y-%m-%d")


def _get_cmc_api_key(db: Session) -> str | None:
    """Read CMC API key from AppSettings DB; fall back to .env value."""
    row = db.query(AppSettings).filter(AppSettings.key == "cmc_api_key").first()
    if row and row.value and row.value.strip():
        return row.value.strip()
    from app.core.config import settings as _settings
    v = getattr(_settings, "CMC_API_KEY", None)
    return v if v and v.strip() else None


def _get_cached(db: Session, series: str, period: str) -> MacroDataPoint | None:
    return (
        db.query(MacroDataPoint)
        .filter(MacroDataPoint.series == series, MacroDataPoint.period == period)
        .first()
    )


def _upsert(db: Session, series: str, period: str, value: float, label: str | None) -> None:
    db.execute(
        text(
            "INSERT INTO macro_data_points (series, period, label, value) "
            "VALUES (:series, :period, :label, :value) "
            "ON CONFLICT (series, period) DO UPDATE "
            "SET value = EXCLUDED.value, label = EXCLUDED.label"
        ),
        {"series": series, "period": period, "label": label or "", "value": value},
    )
    db.commit()


# ── India MMI (Tickertape) ────────────────────────────────────────────────────

def _scrape_tickertape() -> tuple[float, str] | tuple[None, None]:
    """
    Fetch Tickertape's market-mood-index page and extract the MMI value and zone.
    Tickertape uses Next.js SSR so the value is present in initial HTML.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=15.0) as client:
            r = client.get(_TICKERTAPE_PAGE, headers=_BROWSER_HEADERS)
            r.raise_for_status()
            html = r.text

        value_m = re.search(r'class="[^"]*\bnumber\b[^"]*">(\d+\.?\d*)<', html)
        if not value_m:
            logger.warning("MMI: could not find value in Tickertape page HTML")
            return None, None

        mmi = round(float(value_m.group(1)), 2)
        zone_m = re.search(r'indicator_parts/([a-z_]+)\.(?:svg|webp)', html)
        sentiment = _MMI_ZONE_MAP.get(zone_m.group(1), zone_m.group(1)) if zone_m else None
        return mmi, sentiment

    except Exception as exc:
        logger.error(f"MMI scrape failed: {exc}")
        return None, None


def get_mmi(db: Session) -> dict:
    """
    Return today's India MMI from DB if available; otherwise scrape and store.
    Response: { "value": float|None, "sentiment": str|None,
                "source": "db"|"tickertape"|"error", "date": str }
    """
    today = _today_ist()
    cached = _get_cached(db, _MMI_SERIES, today)
    if cached is not None:
        return {"value": cached.value, "sentiment": cached.label or None,
                "source": "db", "date": today}

    mmi, sentiment = _scrape_tickertape()
    if mmi is None:
        return {"value": None, "sentiment": None, "source": "error", "date": today}

    try:
        _upsert(db, _MMI_SERIES, today, mmi, sentiment)
    except Exception as exc:
        logger.error(f"MMI DB write failed: {exc}")

    return {"value": mmi, "sentiment": sentiment, "source": "tickertape", "date": today}


def refresh_mmi(db: Session) -> None:
    """Always scrape and upsert — called by daily scheduler."""
    today = _today_ist()
    mmi, sentiment = _scrape_tickertape()
    if mmi is None:
        logger.warning("MMI daily refresh: scrape returned no data")
        return
    try:
        _upsert(db, _MMI_SERIES, today, mmi, sentiment)
        logger.info(f"MMI refreshed: {mmi} ({sentiment}) for {today}")
    except Exception as exc:
        logger.error(f"MMI daily refresh DB write failed: {exc}")


# ── Bitcoin Fear & Greed Index (Alternative.me) ───────────────────────────────

def _fetch_btc_fng_cmc(api_key: str) -> tuple[float, str] | tuple[None, None]:
    """Fetch BTC Fear & Greed from CoinMarketCap API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(_CMC_FNG_URL, headers={"X-CMC_PRO_API_KEY": api_key})
            r.raise_for_status()
            data = r.json()

        entry = data["data"]
        value = round(float(entry["value"]), 2)
        label = entry.get("value_classification", "")
        return value, label

    except Exception as exc:
        logger.error(f"BTC F&G CMC fetch failed: {exc}")
        return None, None


def _fetch_btc_fng_altme() -> tuple[float, str] | tuple[None, None]:
    """Fetch BTC Fear & Greed from Alternative.me (free, no key required)."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(_ALTME_FNG_URL)
            r.raise_for_status()
            data = r.json()

        entry = data["data"][0]
        value = round(float(entry["value"]), 2)
        label = entry.get("value_classification", "")
        return value, label

    except Exception as exc:
        logger.error(f"BTC F&G Alternative.me fetch failed: {exc}")
        return None, None



def get_btc_fng(db: Session) -> dict:
    """
    Return today's BTC Fear & Greed from DB if available; otherwise fetch and store.
    CMC and Alternative.me use separate cache keys so switching sources works immediately.
    Response: { "value": float|None, "sentiment": str|None,
                "source": "db"|"coinmarketcap"|"alternative.me"|"error", "date": str }
    """
    today = _today_ist()
    cmc_key = _get_cmc_api_key(db)

    if cmc_key:
        # CMC path: check btc_fng_cmc cache
        cached = _get_cached(db, _FNG_CMC_SERIES, today)
        if cached is not None:
            return {"value": cached.value, "sentiment": cached.label or None,
                    "source": "coinmarketcap", "date": today}
        value, label = _fetch_btc_fng_cmc(cmc_key)
        if value is None:
            logger.warning("CMC fetch failed — falling back to Alternative.me")
            # fall through to Alternative.me below
        else:
            try:
                _upsert(db, _FNG_CMC_SERIES, today, value, label)
            except Exception as exc:
                logger.error(f"BTC F&G CMC DB write failed: {exc}")
            return {"value": value, "sentiment": label, "source": "coinmarketcap", "date": today}

    # Alternative.me path: check btc_fng cache
    cached = _get_cached(db, _FNG_SERIES, today)
    if cached is not None:
        return {"value": cached.value, "sentiment": cached.label or None,
                "source": "alternative.me", "date": today}
    value, label = _fetch_btc_fng_altme()
    if value is None:
        return {"value": None, "sentiment": None, "source": "error", "date": today}
    try:
        _upsert(db, _FNG_SERIES, today, value, label)
    except Exception as exc:
        logger.error(f"BTC F&G DB write failed: {exc}")
    return {"value": value, "sentiment": label, "source": "alternative.me", "date": today}


# ── US Fear & Greed Index (CNN) ───────────────────────────────────────────────

def _fetch_us_fng_cnn() -> tuple[float, str] | tuple[None, None]:
    """Fetch US Fear & Greed from CNN's public data API (no key required)."""
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0) as client:
            r = client.get(_CNN_FNG_URL, headers=_BROWSER_HEADERS)
            r.raise_for_status()
            data = r.json()

        fg = data["fear_and_greed"]
        value = round(float(fg["score"]), 2)
        label = fg.get("rating", "")
        return value, label

    except Exception as exc:
        logger.error(f"US F&G CNN fetch failed: {exc}")
        return None, None


def get_us_fng(db: Session) -> dict:
    """
    Return today's US Fear & Greed from DB if available; otherwise fetch from CNN and store.
    Response: { "value": float|None, "sentiment": str|None,
                "source": "db"|"cnn"|"error", "date": str }
    """
    today = _today_ist()
    cached = _get_cached(db, _US_FNG_SERIES, today)
    if cached is not None:
        return {"value": cached.value, "sentiment": cached.label or None,
                "source": "cnn", "date": today}

    value, label = _fetch_us_fng_cnn()
    if value is None:
        return {"value": None, "sentiment": None, "source": "error", "date": today}

    try:
        _upsert(db, _US_FNG_SERIES, today, value, label)
    except Exception as exc:
        logger.error(f"US F&G DB write failed: {exc}")

    return {"value": value, "sentiment": label, "source": "cnn", "date": today}


def refresh_us_fng(db: Session) -> None:
    """Always fetch and upsert — called by daily scheduler."""
    today = _today_ist()
    value, label = _fetch_us_fng_cnn()
    if value is None:
        logger.warning("US F&G daily refresh: fetch returned no data")
        return
    try:
        _upsert(db, _US_FNG_SERIES, today, value, label)
        logger.info(f"US F&G (CNN) refreshed: {value} ({label}) for {today}")
    except Exception as exc:
        logger.error(f"US F&G daily refresh DB write failed: {exc}")


def refresh_btc_fng(db: Session) -> None:
    """Always fetch and upsert — called by daily scheduler."""
    today = _today_ist()
    cmc_key = _get_cmc_api_key(db)
    if cmc_key:
        value, label = _fetch_btc_fng_cmc(cmc_key)
        if value is not None:
            try:
                _upsert(db, _FNG_CMC_SERIES, today, value, label)
                logger.info(f"BTC F&G (CMC) refreshed: {value} ({label}) for {today}")
            except Exception as exc:
                logger.error(f"BTC F&G CMC daily refresh DB write failed: {exc}")
            return
        logger.warning("BTC F&G CMC daily refresh failed — falling back to Alternative.me")
    value, label = _fetch_btc_fng_altme()
    if value is None:
        logger.warning("BTC F&G daily refresh: fetch returned no data")
        return
    try:
        _upsert(db, _FNG_SERIES, today, value, label)
        logger.info(f"BTC F&G (Alternative.me) refreshed: {value} ({label}) for {today}")
    except Exception as exc:
        logger.error(f"BTC F&G daily refresh DB write failed: {exc}")
