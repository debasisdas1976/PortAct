"""
NSE Holidays Service
====================
Maintains a DB-backed table of NSE trading holidays.

DATA SOURCE
-----------
_NSE_HOLIDAY_DATA below is the authoritative list, updated each December when
NSE publishes its annual trading holiday circular for the coming year.
The scheduler syncs this into the `nse_holidays` table so that the API always
reads from the DB — not from this list directly.

SCHEDULING POLICY
-----------------
- On every system startup : ensure current year's data is in the DB.
- If startup month >= 11  : also ensure next year's data is in the DB.
- Annual cron (Dec 1)     : populate the coming year's data proactively.

Islamic holiday dates (Eid ul-Adha, Muharram) shift ~11 days earlier each
year and depend on moon sighting; they are marked "(tentative)".

UPDATE POLICY
-------------
Each October/November, update _NSE_HOLIDAY_DATA with the new NSE circular for
the coming year (published at nseindia.com/resources/exchange-communication-holidays).
Do NOT add a year's data until the official circular is released — estimated
dates cause incorrect calendar display.
"""

from datetime import date
from typing import List, Dict
from loguru import logger
from sqlalchemy.orm import Session

from app.models.nse_holiday import NseHoliday


# ── Source-of-truth holiday list ──────────────────────────────────────────────
# Keep weekends in here — they are filtered out before writing to DB.
# Update every December with the new NSE circular for the upcoming year.

_NSE_HOLIDAY_DATA: List[Dict[str, str]] = [
    # ── 2026 — source: NSE India official holiday circular ────────────────────
    # https://www.nseindia.com/resources/exchange-communication-holidays
    {"date": "2026-01-26", "name": "Republic Day"},
    {"date": "2026-03-03", "name": "Holi"},
    {"date": "2026-03-26", "name": "Ram Navami"},
    {"date": "2026-03-31", "name": "Mahavir Jayanti"},
    {"date": "2026-04-03", "name": "Good Friday"},
    {"date": "2026-04-14", "name": "Dr. Baba Saheb Ambedkar Jayanti"},
    {"date": "2026-05-01", "name": "Maharashtra Day"},
    {"date": "2026-05-28", "name": "Bakri Id / Eid ul-Adha (tentative)"},
    {"date": "2026-06-26", "name": "Muharram (tentative)"},
    {"date": "2026-08-15", "name": "Independence Day"},       # Saturday — filtered out
    {"date": "2026-09-14", "name": "Ganesh Chaturthi"},
    {"date": "2026-10-02", "name": "Mahatma Gandhi Jayanti"},
    {"date": "2026-10-20", "name": "Dasara"},
    {"date": "2026-11-08", "name": "Diwali-Laxmi Pujan"},    # Sunday — filtered out
    {"date": "2026-11-10", "name": "Diwali-Balipratipada"},
    {"date": "2026-11-24", "name": "Guru Nanak Jayanti"},
    {"date": "2026-12-25", "name": "Christmas"},
    # ── 2027 — add after NSE publishes the official circular (Oct/Nov 2026) ──
]


# ── DB operations ─────────────────────────────────────────────────────────────

def _source_holidays_for_year(year: int) -> List[Dict[str, str]]:
    """Return weekday entries from the source list for the given year."""
    return [
        h for h in _NSE_HOLIDAY_DATA
        if date.fromisoformat(h["date"]).year == year
        and date.fromisoformat(h["date"]).weekday() < 5  # Mon–Fri only
    ]


def populate_year(db: Session, year: int) -> int:
    """
    Insert NSE holidays for `year` into the DB if not already present.
    Idempotent — skips silently if data already exists for that year.
    Returns the number of rows inserted (0 if already populated).
    """
    existing = db.query(NseHoliday).filter(NseHoliday.year == year).count()
    if existing > 0:
        logger.debug(f"NSE holidays for {year} already in DB ({existing} rows) — skipping.")
        return 0

    holidays = _source_holidays_for_year(year)
    if not holidays:
        logger.warning(f"No NSE holiday data found in source list for {year}.")
        return 0

    for h in holidays:
        db.add(NseHoliday(
            date=date.fromisoformat(h["date"]),
            name=h["name"],
            year=year,
        ))
    db.commit()
    logger.info(f"Populated {len(holidays)} NSE holidays for {year}.")
    return len(holidays)


def ensure_holidays(db: Session) -> None:
    """
    Called on startup and by the annual Dec-1 scheduler job.

    Always ensures current year's data is in the DB.
    Also populates next year if the current month is November (11) or later —
    because December 1st NSE circular typically arrives in November.
    """
    today = date.today()
    years_to_ensure = [today.year]
    if today.month >= 11:
        years_to_ensure.append(today.year + 1)

    for year in years_to_ensure:
        try:
            populate_year(db, year)
        except Exception as exc:
            logger.error(f"Failed to populate NSE holidays for {year}: {exc}")
            db.rollback()


def get_nse_holidays(db: Session, years: List[int]) -> List[Dict[str, str]]:
    """
    Read NSE holidays for the requested years from DB, sorted by date.
    Returns list of {date: YYYY-MM-DD, name: str}.
    """
    rows = (
        db.query(NseHoliday)
        .filter(NseHoliday.year.in_(years))
        .order_by(NseHoliday.date)
        .all()
    )
    return [{"date": row.date.isoformat(), "name": row.name} for row in rows]
