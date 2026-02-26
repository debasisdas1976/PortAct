"""Automatic master-data seed file synchronisation.

Whenever a master table row (bank, broker, crypto exchange, institution,
asset type, or system expense category) is created, updated, or deleted
via the ORM, the ``seed_data.json`` file is re-exported so that fresh
database installs always contain the latest data.

Usage – called once at import time from ``database.py``::

    from app.services.seed_sync import register_seed_sync_events
    register_seed_sync_events(SessionLocal)
"""

import json
import os
from pathlib import Path

from loguru import logger
from sqlalchemy import event

# ---------------------------------------------------------------------------
# Seed file path — lives next to the app package so it's committed to git.
# ---------------------------------------------------------------------------
SEED_FILE_PATH = Path(__file__).resolve().parent.parent / "seed_data.json"

# ---------------------------------------------------------------------------
# Column specs: which columns to export for each master table.
# ---------------------------------------------------------------------------
_BANK_COLS = ["name", "display_label", "bank_type", "website", "has_parser", "supported_formats", "sort_order"]
_BROKER_COLS = ["name", "display_label", "broker_type", "supported_markets", "website", "has_parser", "supported_formats", "sort_order"]
_EXCHANGE_COLS = ["name", "display_label", "exchange_type", "website", "sort_order"]
_INSTITUTION_COLS = ["name", "display_label", "category", "website", "sort_order"]
_ASSET_TYPE_COLS = ["name", "display_label", "category", "sort_order", "allowed_conversions"]
_EXPENSE_CAT_COLS = ["name", "description", "icon", "color", "is_income", "keywords"]


def _rows_to_dicts(rows, columns):
    """Convert a list of ORM rows to a list of plain dicts."""
    return [
        {col: getattr(r, col) for col in columns}
        for r in sorted(rows, key=lambda r: getattr(r, "sort_order", 0))
    ]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_seed_data() -> dict:
    """Read seed_data.json and return its contents as a dict."""
    if not SEED_FILE_PATH.exists():
        logger.warning(f"Seed file not found at {SEED_FILE_PATH}, returning empty seed data.")
        return {}
    with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def export_seed_data(session_factory):
    """Query all master tables and write the current state to seed_data.json.

    Uses a *new* short-lived session from ``session_factory`` so that it can
    be called safely from an ``after_commit`` event listener (the original
    session may already be expunged).
    """
    # Late imports to avoid circular dependencies at module load time.
    from app.models.bank import BankMaster
    from app.models.broker import BrokerMaster
    from app.models.crypto_exchange import CryptoExchangeMaster
    from app.models.institution import InstitutionMaster
    from app.models.asset_type_master import AssetTypeMaster
    from app.models.expense_category import ExpenseCategory

    db = session_factory()
    try:
        seed = {
            "banks": _rows_to_dicts(db.query(BankMaster).all(), _BANK_COLS),
            "brokers": _rows_to_dicts(db.query(BrokerMaster).all(), _BROKER_COLS),
            "crypto_exchanges": _rows_to_dicts(db.query(CryptoExchangeMaster).all(), _EXCHANGE_COLS),
            "institutions": _rows_to_dicts(db.query(InstitutionMaster).all(), _INSTITUTION_COLS),
            "asset_types": _rows_to_dicts(db.query(AssetTypeMaster).all(), _ASSET_TYPE_COLS),
            "expense_categories": _rows_to_dicts(
                db.query(ExpenseCategory).filter(ExpenseCategory.is_system == True).all(),
                _EXPENSE_CAT_COLS,
            ),
        }
    finally:
        db.close()

    # Atomic write: write to a temp file then rename, to avoid partial writes.
    tmp_path = str(SEED_FILE_PATH) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(seed, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, SEED_FILE_PATH)
    logger.info("seed_data.json updated after master data change.")


# ---------------------------------------------------------------------------
# SQLAlchemy event listeners
# ---------------------------------------------------------------------------

# Table names we consider "master data".
_MASTER_TABLE_NAMES: set = set()  # populated lazily on first flush


def _get_master_table_names() -> set:
    """Return the set of master table names (populated once on first call)."""
    global _MASTER_TABLE_NAMES
    if not _MASTER_TABLE_NAMES:
        from app.models.bank import BankMaster
        from app.models.broker import BrokerMaster
        from app.models.crypto_exchange import CryptoExchangeMaster
        from app.models.institution import InstitutionMaster
        from app.models.asset_type_master import AssetTypeMaster
        from app.models.expense_category import ExpenseCategory
        _MASTER_TABLE_NAMES = {
            BankMaster.__tablename__,
            BrokerMaster.__tablename__,
            CryptoExchangeMaster.__tablename__,
            InstitutionMaster.__tablename__,
            AssetTypeMaster.__tablename__,
            ExpenseCategory.__tablename__,
        }
    return _MASTER_TABLE_NAMES


def register_seed_sync_events(session_factory):
    """Hook into SQLAlchemy session events so that any commit that touches a
    master table automatically re-exports ``seed_data.json``.

    Call this once after creating the ``SessionLocal`` factory.
    """

    @event.listens_for(session_factory, "after_flush")
    def _flag_master_change(session, flush_context):
        """After a flush, check if any master table row was affected."""
        master_tables = _get_master_table_names()
        for obj in session.new | session.dirty | session.deleted:
            tname = getattr(obj, "__tablename__", None)
            if tname and tname in master_tables:
                session.info["_master_data_changed"] = True
                return  # one flag is enough

    @event.listens_for(session_factory, "after_commit")
    def _export_on_commit(session):
        """After commit, if the flag is set, re-export the seed file."""
        if session.info.pop("_master_data_changed", False):
            try:
                export_seed_data(session_factory)
            except Exception as exc:
                # Never let a seed-sync failure break the request.
                logger.error(f"Failed to export seed_data.json: {exc}")

    logger.debug("Seed-sync event listeners registered.")
