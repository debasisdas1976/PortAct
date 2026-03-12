"""
Macro-economic data service — database-backed with delta fetching.

Historical data is seeded by the Alembic migration.
The daily scheduler job calls refresh_macro_data(db) to fetch only new data
and write it to the macro_data_points table.

Data sources:
  - US CPI (CPIAUCSL)    : BLS public API — no key needed
  - US Unemployment      : BLS public API — no key needed
  - India CPI YoY %      : World Bank API — no key needed
  - RBI Repo Rate        : BankBazaar scrape — no key; keeps DB data on failure
  - US Fed Funds Rate    : FRED CSV (FEDFUNDS) — no key needed
  - US 10Y Treasury Yield: FRED CSV (GS10) — no key needed
  - Nifty 50 P/E         : NSE archives CSV — no key needed
  - India VIX            : Yahoo Finance historical API — no key needed
  - FII/DII equity flows : NSE fiidiiTradeReact API — session-based, no key needed
  - India SIP inflows    : AMFI monthly XLS report — no auth needed
"""

import csv
import io
import logging
import time
from datetime import date, timedelta
from typing import Optional

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.macro_data import MacroDataPoint

logger = logging.getLogger(__name__)

_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_REQUEST_TIMEOUT = 15


def _period_label(period: str) -> str:
    """Convert 'YYYY-MM' to "Mon'YY" label, e.g. '2025-01' → \"Jan'25\"."""
    y, m = period.split("-")
    return f"{_MONTH_ABBR[int(m) - 1]}'{y[2:]}"


def _latest_period(db: Session, series: str) -> Optional[str]:
    """Return the most recent 'YYYY-MM' period stored for a series, or None."""
    row = (
        db.query(MacroDataPoint)
        .filter(MacroDataPoint.series == series)
        .order_by(MacroDataPoint.period.desc())
        .first()
    )
    return row.period if row else None


def _upsert_rows(db: Session, rows: list) -> int:
    """Insert new rows into macro_data_points, ignoring duplicates.
    Returns the number of rows actually inserted."""
    if not rows:
        return 0
    stmt = text(
        """
        INSERT INTO macro_data_points (series, period, label, value)
        VALUES (:series, :period, :label, :value)
        ON CONFLICT (series, period) DO NOTHING
        """
    )
    inserted = 0
    for row in rows:
        result = db.execute(stmt, row)
        inserted += result.rowcount
    db.commit()
    return inserted


# ── BLS ────────────────────────────────────────────────────────────────────────

_BLS_BASE = "https://api.bls.gov/publicAPI/v1/timeseries/data"


def _fetch_bls_raw(bls_series_id: str) -> list:
    """Fetch all available monthly data from BLS public API (no key required)."""
    url = f"{_BLS_BASE}/{bls_series_id}"
    try:
        r = requests.get(url, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(f"BLS status: {data.get('message')}")
        return data["Results"]["series"][0]["data"]
    except Exception as exc:
        logger.warning("BLS fetch failed for %s: %s", bls_series_id, exc)
        return []


def _refresh_bls_cpi(db: Session) -> None:
    """Fetch US CPI index (CPIAUCSL) from BLS, compute YoY%, upsert new periods.
    Always fetches full dataset to ensure year-ago values are available for YoY computation."""
    raw = _fetch_bls_raw("CPIAUCSL")
    if not raw:
        return

    # Build index lookup: (year, month) -> index value
    lookup: dict = {}
    for item in raw:
        try:
            period_str = item["period"]
            if not period_str.startswith("M") or period_str == "M13":
                continue
            y = int(item["year"])
            m = int(period_str[1:])
            lookup[(y, m)] = float(item["value"])
        except (KeyError, ValueError):
            continue

    latest = _latest_period(db, "us_cpi")
    rows = []
    for (y, m), v in sorted(lookup.items()):
        period = f"{y}-{m:02d}"
        if latest and period <= latest:
            continue
        prev = lookup.get((y - 1, m))
        if prev and prev > 0:
            yoy = round((v / prev - 1) * 100, 2)
            rows.append({
                "series": "us_cpi",
                "period": period,
                "label": _period_label(period),
                "value": yoy,
            })

    inserted = _upsert_rows(db, rows)
    logger.info("US CPI: inserted %d new rows", inserted)


def _refresh_bls_unemployment(db: Session) -> None:
    """Fetch US unemployment rate from BLS and upsert new periods."""
    raw = _fetch_bls_raw("LNS14000000")
    if not raw:
        return

    latest = _latest_period(db, "us_unemployment")
    rows = []
    for item in raw:
        try:
            period_str = item["period"]
            if not period_str.startswith("M") or period_str == "M13":
                continue
            year = item["year"]
            month = int(period_str[1:])
            period = f"{year}-{month:02d}"
            if latest and period <= latest:
                continue
            rows.append({
                "series": "us_unemployment",
                "period": period,
                "label": _period_label(period),
                "value": round(float(item["value"]), 2),
            })
        except (KeyError, ValueError):
            continue

    inserted = _upsert_rows(db, rows)
    logger.info("US Unemployment: inserted %d new rows", inserted)


# ── World Bank ─────────────────────────────────────────────────────────────────

def _refresh_india_cpi(db: Session) -> None:
    """Fetch India CPI YoY% from World Bank API and upsert new periods.
    Indicator FP.CPI.TOTL.ZG with frequency=M gives monthly YoY% directly."""
    url = (
        "https://api.worldbank.org/v2/country/IN/indicator/FP.CPI.TOTL.ZG"
        "?format=json&frequency=M&mrv=60&per_page=200"
    )
    try:
        r = requests.get(url, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError("Unexpected World Bank response structure")
        records = payload[1] or []
    except Exception as exc:
        logger.warning("World Bank India CPI fetch failed: %s", exc)
        return

    latest = _latest_period(db, "india_cpi")
    rows = []
    for rec in records:
        try:
            if rec.get("value") is None:
                continue
            # date field format: "2025M01"
            date_str = rec["date"]
            if "M" not in date_str:
                continue
            year_str, month_str = date_str.split("M")
            period = f"{year_str}-{month_str.zfill(2)}"
            if latest and period <= latest:
                continue
            rows.append({
                "series": "india_cpi",
                "period": period,
                "label": _period_label(period),
                "value": round(float(rec["value"]), 2),
            })
        except (KeyError, ValueError, TypeError):
            continue

    inserted = _upsert_rows(db, rows)
    logger.info("India CPI: inserted %d new rows", inserted)


# ── BankBazaar scraper / RBI Repo Rate ────────────────────────────────────────

_BB_REPO_URL = "https://www.bankbazaar.com/home-loan/repo-rate.html"
_BB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _parse_rbi_rate_page(html: str) -> list:
    """
    Parse the BankBazaar repo rate page.
    Returns list of (period 'YYYY-MM', label "Mon'YY", value float) tuples
    from the rate-history table, newest first.
    """
    from bs4 import BeautifulSoup
    from datetime import datetime

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    # Find table whose first row contains "date" and "repo" columns (bankbazaar uses td, not th)
    history_table = None
    for t in tables:
        first_row = t.find("tr")
        if first_row:
            cells = [c.get_text(strip=True).lower() for c in first_row.find_all(["th", "td"])]
            if any("date" in c for c in cells) and any("repo" in c for c in cells):
                history_table = t
                break
    if not history_table:
        raise ValueError("Rate history table not found on bankbazaar page")

    results = []
    for row in history_table.find_all("tr")[1:]:  # skip header row
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue
        try:
            dt = datetime.strptime(cells[0], "%d %B %Y")
            period = dt.strftime("%Y-%m")
            label = _period_label(period)
            rate = float(cells[1].replace("%", "").strip())
            results.append((period, label, rate))
        except (ValueError, IndexError):
            continue
    return results


def _refresh_rbi_rate(db: Session) -> None:
    """Scrape BankBazaar for the latest RBI repo rate changes and upsert new periods.
    On any failure, existing DB data is preserved unchanged."""
    try:
        r = requests.get(_BB_REPO_URL, headers=_BB_HEADERS, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        entries = _parse_rbi_rate_page(r.text)
    except Exception as exc:
        logger.warning("RBI rate scrape failed (keeping DB data): %s", exc)
        return

    if not entries:
        logger.warning("RBI rate: no entries parsed from bankbazaar, keeping DB data")
        return

    latest = _latest_period(db, "rbi_repo_rate")
    rows = []
    for period, label, value in entries:
        if latest and period <= latest:
            continue
        rows.append({
            "series": "rbi_repo_rate",
            "period": period,
            "label": label,
            "value": value,
        })

    inserted = _upsert_rows(db, rows)
    logger.info("RBI repo rate: inserted %d new rows from bankbazaar", inserted)


# ── FRED ───────────────────────────────────────────────────────────────────────

_FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_FRED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _refresh_fred_series(db: Session, fred_id: str, series_name: str) -> None:
    """Fetch a monthly FRED CSV series and upsert new periods into macro_data_points.
    The CSV has two columns: DATE (YYYY-MM-DD) and the series value.
    We store one row per YYYY-MM period using the first-of-month date as the key."""
    url = f"{_FRED_BASE}?id={fred_id}"
    try:
        r = requests.get(url, headers=_FRED_HEADERS, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        next(reader)  # skip header row
        raw = list(reader)
    except Exception as exc:
        logger.warning("FRED fetch failed for %s: %s", fred_id, exc)
        return

    latest = _latest_period(db, series_name)
    rows = []
    for line in raw:
        try:
            date_str, value_str = line[0], line[1]
            if not date_str or not value_str or value_str == ".":
                continue
            period = date_str[:7]  # "YYYY-MM" from "YYYY-MM-DD"
            if latest and period <= latest:
                continue
            rows.append({
                "series": series_name,
                "period": period,
                "label": _period_label(period),
                "value": round(float(value_str), 2),
            })
        except (ValueError, IndexError):
            continue

    inserted = _upsert_rows(db, rows)
    logger.info("%s (%s): inserted %d new rows", series_name, fred_id, inserted)


# ── Yahoo Finance Historical — India VIX ──────────────────────────────────────

_YF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def _refresh_india_vix(db: Session) -> None:
    """Fetch monthly India VIX closing values from Yahoo Finance historical API
    and upsert new periods. Uses the last 3 years of monthly data.
    Uses DO UPDATE so the current month's value stays current."""
    from datetime import datetime as _dt, timezone as _tz
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/%5EINDIAVIX"
        "?interval=1mo&range=3y"
    )
    try:
        r = requests.get(url, headers=_YF_HEADERS, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
    except Exception as exc:
        logger.warning("India VIX historical fetch failed: %s", exc)
        return

    rows_upserted = 0
    for ts, close_val in zip(timestamps, closes):
        if close_val is None:
            continue
        try:
            d = _dt.fromtimestamp(ts, tz=_tz.utc)
            period = d.strftime("%Y-%m")
            label = _period_label(period)
            value = round(float(close_val), 2)
            db.execute(
                text(
                    "INSERT INTO macro_data_points (series, period, label, value) "
                    "VALUES (:series, :period, :label, :value) "
                    "ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value"
                ),
                {"series": "india_vix", "period": period, "label": label, "value": value},
            )
            rows_upserted += 1
        except (ValueError, OSError):
            continue

    db.commit()
    logger.info("India VIX: upserted %d monthly rows", rows_upserted)


# ── NSE Archives — Nifty 50 P/E ───────────────────────────────────────────────

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _refresh_nifty_pe(db: Session) -> None:
    """Fetch the latest Nifty 50 P/E from NSE archives and upsert for the current month.
    Tries the last 7 days to handle weekends and market holidays.
    Uses DO UPDATE so the current month's value is refreshed daily."""
    today = date.today()
    pe_value: Optional[float] = None
    fetched_date: Optional[date] = None

    for delta in range(7):
        d = today - timedelta(days=delta)
        date_str = d.strftime("%d%m%Y")
        url = f"https://archives.nseindia.com/content/indices/ind_close_all_{date_str}.csv"
        try:
            r = requests.get(url, headers=_NSE_HEADERS, timeout=_REQUEST_TIMEOUT)
            r.raise_for_status()
            reader = csv.DictReader(io.StringIO(r.text))
            for row in reader:
                index_name = row.get("Index Name", "").strip()
                if index_name.lower() == "nifty 50":
                    pe_str = row.get("P/E", "").strip()
                    if pe_str:
                        pe_value = round(float(pe_str), 2)
                        fetched_date = d
                        break
            if pe_value is not None:
                break
        except Exception as exc:
            logger.debug("NSE P/E fetch failed for %s: %s", date_str, exc)
            continue

    if pe_value is None:
        logger.warning("Nifty P/E: could not fetch from NSE archives for last 7 days")
        return

    period = fetched_date.strftime("%Y-%m")
    label = _period_label(period)
    # Use DO UPDATE so the current month's P/E gets refreshed on each run
    db.execute(
        text(
            "INSERT INTO macro_data_points (series, period, label, value) "
            "VALUES (:series, :period, :label, :value) "
            "ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"series": "nifty_pe", "period": period, "label": label, "value": pe_value},
    )
    db.commit()
    logger.info("Nifty P/E: upserted %s = %.2f (from %s)", period, pe_value, fetched_date)


# ── NSE FII / DII Equity Flows ────────────────────────────────────────────────
#
# The NSE fiidiiTradeReact API always returns the most recent single trading
# day's data regardless of any date parameters — there is no way to query
# historical monthly totals from this API.
#
# Strategy: run daily, add today's single-day figure to the current month's
# running total.  A metadata record tracks the last date we accumulated so the
# same trading day is never counted twice even if the scheduler fires more than
# once in a day.  Historical months (up to the latest seed in the migration) are
# seeded once and never touched again by this function.  From the next month
# after the seed, each new month starts at zero and grows automatically.

_NSE_FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
_NSE_FII_DII_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/reports/fii-dii",
}
_NSE_FII_DII_META = "_fii_dii_last_date"  # series name used only for date-tracking


def _nse_session() -> requests.Session:
    """Establish a valid NSE session by visiting the homepage first (sets cookies)."""
    session = requests.Session()
    session.get(
        "https://www.nseindia.com",
        headers={**_NSE_FII_DII_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"},
        timeout=_REQUEST_TIMEOUT,
    )
    time.sleep(0.5)
    return session


def _refresh_nse_fii_dii(db: Session) -> None:
    """Fetch today's FII/DII net equity flow from NSE and accumulate into the
    current month's running total.  Skips if today was already processed."""
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    current_period = today.strftime("%Y-%m")

    # Skip if today was already accumulated
    meta = (
        db.query(MacroDataPoint)
        .filter(MacroDataPoint.series == _NSE_FII_DII_META, MacroDataPoint.period == "meta")
        .first()
    )
    if meta and meta.label == today_str:
        logger.info("NSE FII/DII: already processed today (%s), skipping", today_str)
        return

    try:
        session = _nse_session()
        r = session.get(_NSE_FII_DII_URL, headers=_NSE_FII_DII_HEADERS, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        records = r.json()
        if not isinstance(records, list) or not records:
            logger.warning("NSE FII/DII: empty response, skipping")
            return
    except Exception as exc:
        logger.warning("NSE FII/DII fetch failed: %s", exc)
        return

    fii_today = dii_today = 0.0
    for entry in records:
        try:
            cat = str(entry.get("category", "")).upper()
            net = float(entry.get("netValue", 0) or 0)
            if "FII" in cat or "FPI" in cat:
                fii_today += net
            elif "DII" in cat:
                dii_today += net
        except (ValueError, TypeError):
            continue

    label = _period_label(current_period)

    # Read existing month totals; start at zero if this is a brand-new month
    fii_row = (
        db.query(MacroDataPoint)
        .filter(MacroDataPoint.series == "fii_equity_flow", MacroDataPoint.period == current_period)
        .first()
    )
    dii_row = (
        db.query(MacroDataPoint)
        .filter(MacroDataPoint.series == "dii_equity_flow", MacroDataPoint.period == current_period)
        .first()
    )
    new_fii = round((fii_row.value if fii_row else 0.0) + fii_today, 0)
    new_dii = round((dii_row.value if dii_row else 0.0) + dii_today, 0)

    upsert = text(
        "INSERT INTO macro_data_points (series, period, label, value) "
        "VALUES (:series, :period, :label, :value) "
        "ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value"
    )
    db.execute(upsert, {"series": "fii_equity_flow", "period": current_period, "label": label, "value": new_fii})
    db.execute(upsert, {"series": "dii_equity_flow", "period": current_period, "label": label, "value": new_dii})

    # Record today so we don't double-count if the scheduler runs again today
    db.execute(
        text(
            "INSERT INTO macro_data_points (series, period, label, value) "
            "VALUES (:series, :period, :label, :value) "
            "ON CONFLICT (series, period) DO UPDATE SET label = EXCLUDED.label"
        ),
        {"series": _NSE_FII_DII_META, "period": "meta", "label": today_str, "value": 0.0},
    )
    db.commit()
    logger.info(
        "NSE FII/DII: +%.0f / +%.0f → %s totals FII=%.0f DII=%.0f",
        fii_today, dii_today, current_period, new_fii, new_dii,
    )


# ── World Bank — India Annual GDP Growth ──────────────────────────────────────

def _refresh_india_gdp(db: Session) -> None:
    """
    Fetch India annual real GDP growth % from World Bank API and upsert.

    Indicator: NY.GDP.MKTP.KD.ZG (annual GDP growth %)
    World Bank calendar year X → India FY(X+1) (Apr X – Mar X+1).
    Stored as period 'YYYY-03' (fiscal year-end March) with label 'FYXX'.
    Current fiscal year uses DO UPDATE so preliminary estimates stay fresh.
    """
    url = (
        "https://api.worldbank.org/v2/country/IN/indicator/NY.GDP.MKTP.KD.ZG"
        "?format=json&mrv=15&per_page=30"
    )
    try:
        r = requests.get(url, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError("Unexpected World Bank GDP response structure")
        records = payload[1] or []
    except Exception as exc:
        logger.warning("World Bank India GDP fetch failed: %s", exc)
        return

    today = date.today()
    # Current FY ends in March; if we're past March the current FY end year = this year + 1
    current_fy_end_year = today.year + 1 if today.month >= 4 else today.year
    current_period = f"{current_fy_end_year}-03"

    rows = []
    for rec in records:
        try:
            if rec.get("value") is None:
                continue
            cal_year = int(rec["date"])
            fy_end_year = cal_year + 1  # India FY ends March of next calendar year
            period = f"{fy_end_year}-03"
            label = f"FY{str(fy_end_year)[2:]}"
            value = round(float(rec["value"]), 1)
            rows.append({"series": "india_gdp_growth", "period": period, "label": label, "value": value})
        except (KeyError, ValueError, TypeError):
            continue

    rows.sort(key=lambda x: x["period"])

    upserted = 0
    for row in rows:
        conflict_clause = (
            "ON CONFLICT (series, period) DO UPDATE SET value = EXCLUDED.value"
            if row["period"] == current_period else
            "ON CONFLICT (series, period) DO NOTHING"
        )
        db.execute(
            text(
                f"INSERT INTO macro_data_points (series, period, label, value) "
                f"VALUES (:series, :period, :label, :value) {conflict_clause}"
            ),
            row,
        )
        upserted += 1

    db.commit()
    logger.info("India GDP: upserted %d annual rows", upserted)


# ── India SIP Monthly Inflows (AI-assisted) ───────────────────────────────────
#
# AMFI does not expose SIP aggregate data in its monthly XLS reports.
# Instead, we use the user-configured AI provider (OpenAI / Gemini / etc.) to
# look up the AMFI-published SIP inflow figure for the most recent completed
# month that is not yet in the DB.  The AI is prompted to return ONLY a number;
# if it replies null the record is skipped and retried on the next daily run.

_AI_SIP_PROVIDERS = {
    "openai":    {"key": "ai_openai_api_key",    "endpoint": "ai_openai_endpoint",    "model": "ai_openai_model",    "format": "openai"},
    "grok":      {"key": "ai_grok_api_key",      "endpoint": "ai_grok_endpoint",      "model": "ai_grok_model",      "format": "openai"},
    "gemini":    {"key": "ai_gemini_api_key",     "endpoint": "ai_gemini_endpoint",    "model": "ai_gemini_model",    "format": "openai"},
    "deepseek":  {"key": "ai_deepseek_api_key",   "endpoint": "ai_deepseek_endpoint",  "model": "ai_deepseek_model",  "format": "openai"},
    "mistral":   {"key": "ai_mistral_api_key",    "endpoint": "ai_mistral_endpoint",   "model": "ai_mistral_model",   "format": "openai"},
    "anthropic": {"key": "ai_anthropic_api_key",  "endpoint": "ai_anthropic_endpoint", "model": "ai_anthropic_model", "format": "anthropic"},
}


def _ai_sip_config(db: Session) -> Optional[dict]:
    """
    Resolve the active AI provider config from DB (AppSettings).
    Returns a dict with keys: api_key, endpoint, model, format, display_name.
    Returns None if no provider is configured or no API key is set.
    """
    from app.models.app_settings import AppSettings
    from app.core.config import settings as env_settings

    rows = db.query(AppSettings).filter(AppSettings.category == "ai").all()
    db_cfg = {r.key: r.value for r in rows}

    provider = (db_cfg.get("ai_news_provider") or getattr(env_settings, "AI_NEWS_PROVIDER", "openai")).lower()
    if provider not in _AI_SIP_PROVIDERS:
        provider = "openai"

    prov = _AI_SIP_PROVIDERS[provider]
    api_key  = db_cfg.get(prov["key"])  or getattr(env_settings, prov["key"].replace("ai_", "").upper().replace("_API_KEY", "_API_KEY"), None)
    endpoint = db_cfg.get(prov["endpoint"]) or getattr(env_settings, prov["endpoint"].replace("ai_", "").upper().replace("_ENDPOINT", "_API_ENDPOINT"), "")
    model    = db_cfg.get(prov["model"])    or getattr(env_settings, prov["model"].replace("ai_", "").upper().replace("_MODEL", "_MODEL"), "")

    if not api_key:
        logger.warning("SIP AI refresh: no API key found for provider '%s'", provider)
        return None

    return {"api_key": api_key, "endpoint": endpoint, "model": model,
            "format": prov["format"], "display_name": provider}


def _query_ai_for_sip(period: str, cfg: dict) -> Optional[float]:
    """
    Ask the configured AI provider for AMFI's published total SIP inflow
    (₹ crore) for *period* (format 'YYYY-MM').
    Returns the rounded crore value or None if the AI couldn't provide it.
    """
    import json as _json

    y, m = period.split("-")
    month_name = f"{_MONTH_ABBR[int(m) - 1]} {y}"

    prompt = (
        f"What was India's total SIP (Systematic Investment Plan) inflow for "
        f"{month_name} as officially published by AMFI (Association of Mutual Funds in India)? "
        f"Reply with ONLY valid JSON, no markdown: "
        f'{{ "sip_inflow_crore": <number in INR crore, rounded to nearest crore> }} '
        f'or {{ "sip_inflow_crore": null }} if you do not have this specific figure.'
    )

    try:
        if cfg["format"] == "anthropic":
            headers = {
                "x-api-key": cfg["api_key"],
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": cfg["model"],
                "max_tokens": 100,
                "messages": [{"role": "user", "content": prompt}],
            }
            r = requests.post(cfg["endpoint"], headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            raw = r.json()["content"][0]["text"].strip()
        else:
            headers = {
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": "You are a financial data assistant. Reply with valid JSON only, no markdown."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 100,
                "temperature": 0.0,
            }
            r = requests.post(cfg["endpoint"], headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = _json.loads(raw)
        val = data.get("sip_inflow_crore")
        if val is None:
            logger.info("SIP AI: model returned null for %s", period)
            return None
        val = float(val)
        # Sanity check: SIP inflows are typically ₹10k–₹50k crore
        if not (5_000 < val < 1_00_000):
            logger.warning("SIP AI: implausible value %.0f for %s — discarding", val, period)
            return None
        return round(val, 0)

    except Exception as exc:
        logger.warning("SIP AI query failed for %s: %s", period, exc)
        return None


def _refresh_sip_via_ai(db: Session) -> None:
    """
    Use the configured AI provider to fetch and store AMFI SIP inflow data
    for any recently completed months not yet in the DB.

    Logic:
    - Determines the last fully-completed month (month before today).
    - If the DB already has data for that month, nothing to do.
    - Otherwise queries the AI for each missing month up to last complete month.
    - Skips months the AI cannot provide (null response).
    """
    today = date.today()
    # Last fully-completed month
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1
    last_complete = f"{prev_year}-{prev_month:02d}"

    latest = _latest_period(db, "india_sip_inflow")
    if latest and latest >= last_complete:
        logger.info("SIP AI: data already current through %s, skipping", latest)
        return

    cfg = _ai_sip_config(db)
    if cfg is None:
        return  # No AI provider configured; logged inside _ai_sip_config

    # Build list of missing periods from (latest+1) through last_complete
    if latest:
        y, m = int(latest[:4]), int(latest[5:])
        m += 1
        if m > 12:
            m, y = 1, y + 1
    else:
        y, m = prev_year, prev_month  # just fetch last complete month if nothing stored

    missing = []
    while f"{y}-{m:02d}" <= last_complete:
        missing.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1

    if not missing:
        return

    logger.info("SIP AI: fetching %d missing month(s) via %s", len(missing), cfg["display_name"])

    for period in missing:
        val = _query_ai_for_sip(period, cfg)
        if val is None:
            logger.info("SIP AI: skipping %s (no data from AI)", period)
            continue
        label = _period_label(period)
        db.execute(
            text(
                "INSERT INTO macro_data_points (series, period, label, value) "
                "VALUES (:series, :period, :label, :value) "
                "ON CONFLICT (series, period) DO NOTHING"
            ),
            {"series": "india_sip_inflow", "period": period, "label": label, "value": val},
        )
        db.commit()
        logger.info("SIP AI: stored %s india_sip_inflow = %.0f cr (via %s)", period, val, cfg["display_name"])


# ── Public API ─────────────────────────────────────────────────────────────────

def get_macro_indicators(db: Session) -> dict:
    """Read all macro indicator series from DB and return structured dict."""

    def _read_series(series: str):
        return (
            db.query(MacroDataPoint)
            .filter(MacroDataPoint.series == series)
            .order_by(MacroDataPoint.period.asc())
            .all()
        )

    rbi_rows = _read_series("rbi_repo_rate")
    india_cpi_rows = _read_series("india_cpi")
    us_cpi_rows = _read_series("us_cpi")
    unemp_rows = _read_series("us_unemployment")
    fed_rows = _read_series("us_fed_rate")
    treasury_rows = _read_series("us_10y_yield")
    nifty_pe_rows = _read_series("nifty_pe")
    india_vix_rows = _read_series("india_vix")
    fii_rows = _read_series("fii_equity_flow")
    dii_rows = _read_series("dii_equity_flow")
    sip_rows = _read_series("india_sip_inflow")
    gdp_rows = _read_series("india_gdp_growth")

    return {
        "rbi_repo_rate": [{"date": r.label, "rate": r.value} for r in rbi_rows],
        "india_cpi": [{"month": r.label, "value": r.value} for r in india_cpi_rows],
        "us_cpi": [{"month": r.label, "value": r.value} for r in us_cpi_rows] or None,
        "us_unemployment": [{"month": r.label, "value": r.value} for r in unemp_rows] or None,
        "us_fed_rate": [{"month": r.label, "value": r.value} for r in fed_rows] or None,
        "us_10y_yield": [{"month": r.label, "value": r.value} for r in treasury_rows] or None,
        "nifty_pe": [{"month": r.label, "value": r.value} for r in nifty_pe_rows] or None,
        "india_vix": [{"month": r.label, "value": r.value} for r in india_vix_rows] or None,
        "fii_equity_flow": [{"month": r.label, "value": r.value} for r in fii_rows] or None,
        "dii_equity_flow": [{"month": r.label, "value": r.value} for r in dii_rows] or None,
        "india_sip_inflow": [{"month": r.label, "value": r.value} for r in sip_rows] or None,
        "india_gdp_growth": [{"month": r.label, "value": r.value} for r in gdp_rows] or None,
    }


def refresh_macro_data(db: Session) -> None:
    """Fetch delta updates for all macro series.
    Called by the daily scheduler job. Does NOT include RBI rate (see refresh_rbi_rate_only)."""
    logger.info("Starting daily macro data refresh...")
    _refresh_bls_cpi(db)
    _refresh_bls_unemployment(db)
    _refresh_india_cpi(db)
    _refresh_fred_series(db, "FEDFUNDS", "us_fed_rate")
    _refresh_fred_series(db, "GS10", "us_10y_yield")
    _refresh_nifty_pe(db)
    _refresh_india_vix(db)
    _refresh_nse_fii_dii(db)
    _refresh_india_gdp(db)
    _refresh_sip_via_ai(db)
    logger.info("Daily macro data refresh complete.")


def refresh_rbi_rate_only(db: Session) -> None:
    """Scrape BankBazaar for latest RBI repo rate changes and write to DB.
    Called by the bimonthly scheduler job (10th of Feb/Apr/Jun/Aug/Oct/Dec)."""
    logger.info("Starting bimonthly RBI repo rate refresh...")
    _refresh_rbi_rate(db)
    logger.info("RBI repo rate refresh complete.")
