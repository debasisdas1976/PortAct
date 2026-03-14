#!/usr/bin/env python3
"""
One-time backfill of historical macro-economic data into PortAct.

Run from the backend directory:
    cd backend && python seed_historical_macro_data.py

All inserts use ON CONFLICT DO NOTHING — safe to re-run at any time.

Sources (all free, no API key required):
  FRED public CSV endpoint:
    us_fed_rate     ← FEDFUNDS          (Jul 1954 – present)
    us_10y_yield    ← GS10              (Apr 1953 – present)
    us_cpi          ← CPIAUCSL (pc1)    (Jan 1949 – present, YoY %)
    us_unemployment ← UNRATE            (Jan 1948 – present)
    rbi_repo_rate   ← IRSTCB01INM156N   (India central bank overnight rate,
                                          Jan 1968 – Dec 2023, OECD proxy)

  Yahoo Finance (no key):
    india_vix       ← ^INDIAVIX         (Mar 2008 – present)

Notes:
  - RBI repo rate (as a formal instrument) was introduced in 2000.
    Pre-2000 FRED proxy represents India's prevailing overnight bank rate.
  - Existing DB rows are never overwritten (DO NOTHING), so BankBazaar-
    scraped repo rate values and recent NSE P/E values are preserved.
"""

import csv
import io
import sys
import os
from datetime import date

import requests

# ── path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

# ── constants ────────────────────────────────────────────────────────────────
_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_REQUEST_TIMEOUT = 20


# ── helpers ──────────────────────────────────────────────────────────────────

def _period_label(period: str) -> str:
    """'2025-01' → \"Jan'25\""""
    y, m = period.split("-")
    return f"{_MONTH_ABBR[int(m) - 1]}'{y[2:]}"


def _upsert_rows(db: Session, rows: list) -> int:
    """Insert rows using ON CONFLICT DO NOTHING. Returns count inserted."""
    if not rows:
        return 0
    stmt = text("""
        INSERT INTO macro_data_points (series, period, label, value)
        VALUES (:series, :period, :label, :value)
        ON CONFLICT (series, period) DO NOTHING
    """)
    inserted = 0
    for row in rows:
        result = db.execute(stmt, row)
        inserted += result.rowcount
    db.commit()
    return inserted


def _build_rows(series: str, data: dict) -> list:
    """Convert {period: value} dict to list of insert-ready dicts."""
    return [
        {"series": series, "period": p, "label": _period_label(p), "value": v}
        for p, v in sorted(data.items())
        if v is not None
    ]


# ── FRED ─────────────────────────────────────────────────────────────────────

def fetch_fred(series_id: str, units: str = "lin") -> dict:
    """
    Fetch monthly data from FRED public CSV endpoint (no API key needed).
    Returns {YYYY-MM: float}.

    units: 'lin' = raw value, 'pc1' = percent change from year ago
    NOTE: the public fredgraph.csv endpoint ignores 'units' and always returns
    raw values. When units='pc1', we compute YoY% manually here.
    """
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&frequency=m&units=lin"
    )
    print(f"  Fetching FRED {series_id} (units={units})...", end=" ", flush=True)
    try:
        r = requests.get(url, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        reader = csv.reader(io.StringIO(r.text))
        next(reader)  # skip header row
        raw = {}
        for row in reader:
            if len(row) < 2:
                continue
            date_str, val_str = row[0].strip(), row[1].strip()
            if not date_str or not val_str or val_str == ".":
                continue
            period = date_str[:7]  # YYYY-MM
            try:
                raw[period] = round(float(val_str), 4)
            except ValueError:
                pass

        if units == "pc1":
            # Compute YoY% manually: (current - year_ago) / year_ago * 100
            result = {}
            for period, val in raw.items():
                y, m = period.split("-")
                prior = f"{int(y) - 1}-{m}"
                if prior not in raw or raw[prior] == 0:
                    continue
                result[period] = round((val - raw[prior]) / raw[prior] * 100, 4)
            print(f"{len(result)} monthly records (YoY%)")
            return result

        print(f"{len(raw)} monthly records")
        return raw
    except Exception as exc:
        print(f"ERROR: {exc}")
        return {}


# ── Yahoo Finance ─────────────────────────────────────────────────────────────

def fetch_yahoo_vix() -> dict:
    """
    Fetch India VIX full history from Yahoo Finance (no API key needed).
    Returns {YYYY-MM: float} using month-end close values.
    """
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/"
        "%5EINDIAVIX?interval=1mo&range=max"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    print("  Fetching Yahoo Finance ^INDIAVIX (range=max)...", end=" ", flush=True)
    try:
        r = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        chart_result = data["chart"]["result"][0]
        timestamps = chart_result["timestamp"]
        closes = chart_result["indicators"]["quote"][0]["close"]
        result = {}
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            d = date.fromtimestamp(ts)
            period = d.strftime("%Y-%m")
            result[period] = round(close, 2)
        print(f"{len(result)} monthly records")
        return result
    except Exception as exc:
        print(f"ERROR: {exc}")
        return {}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    db: Session = SessionLocal()
    try:
        print("=" * 60)
        print("PortAct — Historical Macro Data Backfill")
        print("=" * 60)

        # ── [1] US Fed Funds Rate ──────────────────────────────────────────
        print("\n[1/6] US Fed Funds Rate → us_fed_rate")
        print("      Source: FRED FEDFUNDS (Jul 1954 – present)")
        data = fetch_fred("FEDFUNDS", "lin")
        if data:
            rows = _build_rows("us_fed_rate", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        # ── [2] US 10Y Treasury Yield ──────────────────────────────────────
        print("\n[2/6] US 10Y Treasury Yield → us_10y_yield")
        print("      Source: FRED GS10 (Apr 1953 – present)")
        data = fetch_fred("GS10", "lin")
        if data:
            rows = _build_rows("us_10y_yield", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        # ── [3] US CPI YoY % ──────────────────────────────────────────────
        print("\n[3/6] US CPI Inflation (YoY %) → us_cpi")
        print("      Source: FRED CPIAUCSL with pc1 transform (Jan 1949 – present)")
        data = fetch_fred("CPIAUCSL", "pc1")
        if data:
            rows = _build_rows("us_cpi", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        # ── [4] US Unemployment Rate ───────────────────────────────────────
        print("\n[4/6] US Unemployment Rate → us_unemployment")
        print("      Source: FRED UNRATE (Jan 1948 – present)")
        data = fetch_fred("UNRATE", "lin")
        if data:
            rows = _build_rows("us_unemployment", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        # ── [5] RBI Repo Rate (FRED proxy for historical) ─────────────────
        print("\n[5/6] RBI Repo Rate (historical proxy) → rbi_repo_rate")
        print("      Source: FRED IRSTCB01INM156N (India overnight CB rate, OECD)")
        print("      Covers Jan 1968 – Dec 2023. Pre-2019 data will be inserted;")
        print("      existing rows (from BankBazaar scraper) are NOT overwritten.")
        data = fetch_fred("IRSTCB01INM156N", "lin")
        if data:
            rows = _build_rows("rbi_repo_rate", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        # ── [6] India VIX ─────────────────────────────────────────────────
        print("\n[6/6] India VIX → india_vix")
        print("      Source: Yahoo Finance ^INDIAVIX (Mar 2008 – present)")
        data = fetch_yahoo_vix()
        if data:
            rows = _build_rows("india_vix", data)
            n = _upsert_rows(db, rows)
            print(f"  ✓  Inserted {n} new rows ({len(rows) - n} already existed)")

        print("\n" + "=" * 60)
        print("✅  Backfill complete.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⏹  Interrupted by user. Partial data committed so far is safe.")
    except Exception as exc:
        print(f"\n❌  Fatal error: {exc}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
