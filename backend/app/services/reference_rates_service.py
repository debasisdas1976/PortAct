"""
Reference rates service — bank FD rates and government savings scheme rates.

Both data sets are stored in the `reference_rates` table (one row per institution,
always reflecting the current rate). They are refreshed by scheduled jobs:
  - Bank FD rates  : monthly (1st of each month, 07:00 UTC)
  - Govt schemes   : quarterly (1st of Jan/Apr/Jul/Oct, 07:00 UTC)

Scrape sources (no year or date in any URL — always current):
  - Bank FD        : https://www.bankbazaar.com/fixed-deposit-rate.html
  - Govt schemes   : https://www.bankbazaar.com/saving-schemes.html
"""

import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.reference_rate import ReferenceRate

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
_TIMEOUT = 15

# ── Bank FD ────────────────────────────────────────────────────────────────────

_FD_URL = "https://www.bankbazaar.com/fixed-deposit-rate.html"

# Maps lowercase scraped bank name → internal key used by the frontend config
_BANK_NAME_MAP = {
    "state bank of india": "sbi",
    "hdfc bank":           "hdfc",
    "icici bank":          "icici",
    "axis bank":           "axis",
    "kotak mahindra bank": "kotak",
    "bank of baroda":      "bob",
    "indusind bank":       "indusind",
    "yes bank":            "yesbank",
}


def _scrape_bank_fd_rates() -> dict[str, float]:
    """
    Scrape the highest FD rate (general public) for each tracked bank.
    Returns {bank_key: rate_float} or {} on any failure.

    Targets the "highest rate" table on bankbazaar which has columns:
      Bank | Interest Rates for General Public | Interest Rates for Senior Citizens
    """
    r = requests.get(_FD_URL, headers=_HEADERS, timeout=_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Find the table whose first row has "Bank" and "General Public"
    target_table = None
    for t in soup.find_all("table"):
        first_row = t.find("tr")
        if not first_row:
            continue
        cells = [c.get_text(strip=True).lower() for c in first_row.find_all(["th", "td"])]
        if any("bank" in c for c in cells) and any("general public" in c for c in cells):
            # Pick the table where rates are single values (not ranges like "3.00% - 6.45%")
            data_rows = t.find_all("tr")[1:]
            if data_rows:
                sample = data_rows[0].find_all("td")
                if sample and "-" not in sample[1].get_text(strip=True):
                    target_table = t
                    break

    if not target_table:
        raise ValueError("Bank FD rate table not found on bankbazaar page")

    rates: dict[str, float] = {}
    for row in target_table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue
        bank_key = _BANK_NAME_MAP.get(cells[0].lower())
        if not bank_key:
            continue
        try:
            rate_str = cells[1].replace("%", "").strip()
            rates[bank_key] = round(float(rate_str), 2)
        except ValueError:
            continue

    return rates


def refresh_bank_fd_rates(db: Session) -> None:
    """Scrape bankbazaar and upsert current bank FD rates into the DB."""
    try:
        rates = _scrape_bank_fd_rates()
    except Exception as exc:
        logger.warning("Bank FD rates scrape failed (keeping DB data): %s", exc)
        return

    if not rates:
        logger.warning("Bank FD rates: no data parsed, keeping DB data")
        return

    stmt = text(
        """
        INSERT INTO reference_rates (category, name, rate, sub_info)
        VALUES (:cat, :name, :rate, :sub)
        ON CONFLICT (category, name)
        DO UPDATE SET rate = EXCLUDED.rate, sub_info = EXCLUDED.sub_info,
                      updated_at = now()
        """
    )
    sub_info = "Best rate p.a."
    for bank_key, rate in rates.items():
        db.execute(stmt, {"cat": "bank_fd", "name": bank_key, "rate": rate, "sub": sub_info})
    db.commit()
    logger.info("Bank FD rates: updated %d banks", len(rates))


# ── Government Savings Schemes ─────────────────────────────────────────────────

_SCHEME_URL = "https://www.bankbazaar.com/saving-schemes.html"

# Maps lowercase scraped scheme name (partial match) → internal key
_SCHEME_NAME_MAP = {
    "public provident fund":             "ppf",
    "sukanya samriddhi yojana":          "ssy",
    "national savings certificate":      "nsc",
    "kisan vikas patra":                 "kvp",
    "senior citizens' saving scheme":    "scss",
    "senior citizen saving scheme":      "scss",
    "post office monthly income scheme": "mis",
}


def _current_quarter_label() -> str:
    """Return a human-readable current quarter label, e.g. 'Jan–Mar 2026'."""
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    now = datetime.now()
    q = (now.month - 1) // 3
    start_month = q * 3      # 0-indexed
    end_month = start_month + 2
    year = now.year
    return f"{month_names[start_month]}–{month_names[end_month]} {year}"


def _scrape_govt_scheme_rates() -> dict[str, float]:
    """
    Scrape government small savings scheme rates from bankbazaar.
    Returns {scheme_key: rate_float} or {} on failure.
    RBI Floating Rate Bond rate is computed as NSC rate + 0.35% (official formula).
    """
    r = requests.get(_SCHEME_URL, headers=_HEADERS, timeout=_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Find the table with columns: Savings Scheme | Interest Rate | ...
    target_table = None
    for t in soup.find_all("table"):
        first_row = t.find("tr")
        if not first_row:
            continue
        cells = [c.get_text(strip=True).lower() for c in first_row.find_all(["th", "td"])]
        if any("savings scheme" in c or "scheme" in c for c in cells) and any("interest" in c for c in cells):
            target_table = t
            break

    if not target_table:
        raise ValueError("Govt savings scheme table not found on bankbazaar page")

    rates: dict[str, float] = {}
    for row in target_table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 2:
            continue
        scheme_key = None
        name_lower = cells[0].lower()
        # Match by longest prefix (avoids "National Savings Certificate" matching twice)
        for pattern, key in _SCHEME_NAME_MAP.items():
            if pattern in name_lower:
                scheme_key = key
                break
        if not scheme_key:
            continue
        try:
            rate_str = cells[1].replace("%", "").strip()
            if not rate_str or rate_str == "-":
                continue
            rates[scheme_key] = round(float(rate_str), 2)
        except ValueError:
            continue

    # RBI Floating Rate Bond = NSC rate + 0.35% (official government formula)
    if "nsc" in rates:
        rates["rbi_bond"] = round(rates["nsc"] + 0.35, 2)

    return rates


def refresh_govt_scheme_rates(db: Session) -> None:
    """Scrape bankbazaar and upsert current govt savings scheme rates into the DB."""
    try:
        rates = _scrape_govt_scheme_rates()
    except Exception as exc:
        logger.warning("Govt scheme rates scrape failed (keeping DB data): %s", exc)
        return

    if not rates:
        logger.warning("Govt scheme rates: no data parsed, keeping DB data")
        return

    quarter_label = _current_quarter_label()
    stmt = text(
        """
        INSERT INTO reference_rates (category, name, rate, sub_info)
        VALUES (:cat, :name, :rate, :sub)
        ON CONFLICT (category, name)
        DO UPDATE SET rate = EXCLUDED.rate, sub_info = EXCLUDED.sub_info,
                      updated_at = now()
        """
    )
    for scheme_key, rate in rates.items():
        db.execute(stmt, {"cat": "govt_scheme", "name": scheme_key, "rate": rate, "sub": quarter_label})
    db.commit()
    logger.info("Govt scheme rates: updated %d schemes (quarter: %s)", len(rates), quarter_label)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_reference_rates(db: Session) -> dict:
    """
    Read all reference rates from the DB and return a structured dict.
    Returns:
        bank_fd      : list of {name, rate, sub_info} for each tracked bank
        govt_schemes : list of {name, rate, sub_info} for each govt scheme
    """
    def _read(category: str) -> list:
        rows = (
            db.query(ReferenceRate)
            .filter(ReferenceRate.category == category)
            .order_by(ReferenceRate.name)
            .all()
        )
        return [{"name": r.name, "rate": r.rate, "sub_info": r.sub_info} for r in rows]

    return {
        "bank_fd":      _read("bank_fd"),
        "govt_schemes": _read("govt_scheme"),
    }
