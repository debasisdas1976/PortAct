"""
Portfolio administration endpoints:
  GET  /portfolio/export          – download entire portfolio as JSON
  POST /portfolio/restore         – restore portfolio from JSON backup
  GET  /portfolio/statement/pdf   – generate a PDF portfolio statement
"""
from __future__ import annotations

import io
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.crypto_exchange import CryptoExchangeMaster
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.models.transaction import Transaction
from app.models.alert import Alert
from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
from app.models.mutual_fund_holding import MutualFundHolding

router = APIRouter()

EXPORT_VERSION = "5.0"
SUPPORTED_VERSIONS = {"1.0", "2.0", "3.0", "4.0", "5.0"}


# ─── helpers ────────────────────────────────────────────────────────────────

def _to_dict(obj) -> Dict[str, Any]:
    """Convert a SQLAlchemy model row to a JSON-serialisable dict."""
    result: Dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, (datetime, date)):
            result[col.name] = val.isoformat()
        elif hasattr(val, "value"):          # Enum
            result[col.name] = val.value
        else:
            result[col.name] = val
    return result


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ─── export ─────────────────────────────────────────────────────────────────

@router.get("/export")
async def export_portfolio(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Download the entire portfolio as a JSON file."""
    uid = current_user.id

    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == uid).all()
    demat_accounts = db.query(DematAccount).filter(DematAccount.user_id == uid).all()
    crypto_accounts = db.query(CryptoAccount).filter(CryptoAccount.user_id == uid).all()
    assets = db.query(Asset).filter(Asset.user_id == uid).all()
    # Include both user-defined AND system categories so expense category_id
    # references remain valid on restore.
    from sqlalchemy import or_
    categories = db.query(ExpenseCategory).filter(
        or_(ExpenseCategory.user_id == uid, ExpenseCategory.user_id.is_(None))
    ).all()
    expenses = db.query(Expense).filter(Expense.user_id == uid).all()
    alerts = db.query(Alert).filter(Alert.user_id == uid).all()

    portfolios = db.query(Portfolio).filter(Portfolio.user_id == uid).all()

    asset_ids = [a.id for a in assets]
    transactions = (
        db.query(Transaction).filter(Transaction.asset_id.in_(asset_ids)).all()
        if asset_ids
        else []
    )

    # Mutual fund holdings (stock-level breakdown of MF assets)
    mutual_fund_holdings = (
        db.query(MutualFundHolding).filter(MutualFundHolding.user_id == uid).all()
    )

    # Portfolio snapshots with their nested asset snapshots
    portfolio_snapshots = (
        db.query(PortfolioSnapshot).filter(PortfolioSnapshot.user_id == uid).all()
    )
    snapshots_data = []
    for ps in portfolio_snapshots:
        ps_dict = _to_dict(ps)
        ps_dict["asset_snapshots"] = [_to_dict(a_snap) for a_snap in ps.asset_snapshots]
        snapshots_data.append(ps_dict)

    payload = {
        "export_version": EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "exported_by": current_user.email,
        "portfolios": [_to_dict(r) for r in portfolios],
        "bank_accounts": [_to_dict(r) for r in bank_accounts],
        "demat_accounts": [_to_dict(r) for r in demat_accounts],
        "crypto_accounts": [_to_dict(r) for r in crypto_accounts],
        "assets": [_to_dict(r) for r in assets],
        "expense_categories": [_to_dict(r) for r in categories],
        "expenses": [_to_dict(r) for r in expenses],
        "transactions": [_to_dict(r) for r in transactions],
        "mutual_fund_holdings": [_to_dict(r) for r in mutual_fund_holdings],
        "alerts": [_to_dict(r) for r in alerts],
        "portfolio_snapshots": snapshots_data,
    }

    json_bytes = json.dumps(payload, default=str, indent=2).encode("utf-8")
    filename = f"portfolio_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── restore ────────────────────────────────────────────────────────────────

@router.post("/restore")
async def restore_portfolio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Restore portfolio from a previously exported JSON backup.

    Records that already exist (matched by natural keys) are skipped.
    New records are inserted and old-ID → new-ID mappings are built so that
    dependent records (assets, expenses, transactions) are linked correctly.
    """
    raw = await file.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON file")

    file_version = data.get("export_version")
    if file_version not in SUPPORTED_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export version '{file_version}'. Supported: {', '.join(sorted(SUPPORTED_VERSIONS))}.",
        )

    uid = current_user.id

    stats: Dict[str, Dict[str, int]] = {
        k: {"imported": 0, "skipped": 0}
        for k in ("portfolios", "bank_accounts", "demat_accounts", "crypto_accounts",
                  "assets", "expense_categories", "expenses", "transactions",
                  "mutual_fund_holdings", "alerts", "portfolio_snapshots", "asset_snapshots")
    }

    # old_id → new_id maps
    portfolio_map: Dict[int, int] = {}
    ba_map: Dict[int, int] = {}
    da_map: Dict[int, int] = {}
    ca_map: Dict[int, int] = {}
    cat_map: Dict[int, int] = {}
    asset_map: Dict[int, int] = {}

    # ── 0. Portfolios ────────────────────────────────────────────────────────
    # Ensure the user has a default portfolio (needed for v1/v2 backups or
    # as a fallback when restoring assets without portfolio data).
    default_portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == uid, Portfolio.is_default == True)
        .first()
    )
    if not default_portfolio:
        default_portfolio = Portfolio(user_id=uid, name="Default", is_default=True)
        db.add(default_portfolio)
        db.flush()

    for r in data.get("portfolios", []):
        old_id = r.get("id")
        existing = (
            db.query(Portfolio)
            .filter(
                Portfolio.user_id == uid,
                Portfolio.name == r.get("name"),
            )
            .first()
        )
        if existing:
            portfolio_map[old_id] = existing.id
            stats["portfolios"]["skipped"] += 1
        else:
            obj = Portfolio(
                user_id=uid,
                name=r.get("name"),
                description=r.get("description"),
                is_default=False,  # only the pre-existing default is default
                is_active=r.get("is_active", True),
            )
            db.add(obj)
            db.flush()
            portfolio_map[old_id] = obj.id
            stats["portfolios"]["imported"] += 1

    # ── 1. Bank accounts ─────────────────────────────────────────────────────
    for r in data.get("bank_accounts", []):
        old_id = r.get("id")
        existing = (
            db.query(BankAccount)
            .filter(
                BankAccount.user_id == uid,
                BankAccount.bank_name == r.get("bank_name"),
                BankAccount.account_type == r.get("account_type"),
                BankAccount.account_number == r.get("account_number"),
            )
            .first()
        )
        if existing:
            ba_map[old_id] = existing.id
            stats["bank_accounts"]["skipped"] += 1
        else:
            obj = BankAccount(
                user_id=uid,
                portfolio_id=portfolio_map.get(r.get("portfolio_id")) or default_portfolio.id,
                bank_name=r.get("bank_name"),
                account_type=r.get("account_type"),
                account_number=r.get("account_number"),
                account_holder_name=r.get("account_holder_name"),
                ifsc_code=r.get("ifsc_code"),
                branch_name=r.get("branch_name"),
                current_balance=r.get("current_balance", 0),
                available_balance=r.get("available_balance"),
                credit_limit=r.get("credit_limit"),
                is_active=r.get("is_active", True),
                is_primary=r.get("is_primary", False),
                nickname=r.get("nickname"),
                notes=r.get("notes"),
                last_statement_date=_parse_dt(r.get("last_statement_date")),
            )
            db.add(obj)
            db.flush()
            ba_map[old_id] = obj.id
            stats["bank_accounts"]["imported"] += 1

    # ── 2. Demat accounts ────────────────────────────────────────────────────
    for r in data.get("demat_accounts", []):
        old_id = r.get("id")
        existing = (
            db.query(DematAccount)
            .filter(
                DematAccount.user_id == uid,
                DematAccount.broker_name == r.get("broker_name"),
                DematAccount.account_id == r.get("account_id"),
            )
            .first()
        )
        if existing:
            da_map[old_id] = existing.id
            stats["demat_accounts"]["skipped"] += 1
        else:
            obj = DematAccount(
                user_id=uid,
                portfolio_id=portfolio_map.get(r.get("portfolio_id")) or default_portfolio.id,
                broker_name=r.get("broker_name"),
                account_id=r.get("account_id"),
                account_holder_name=r.get("account_holder_name"),
                demat_account_number=r.get("demat_account_number"),
                account_market=r.get("account_market"),
                cash_balance=r.get("cash_balance", 0),
                cash_balance_usd=r.get("cash_balance_usd"),
                currency=r.get("currency", "INR"),
                is_active=r.get("is_active", True),
                is_primary=r.get("is_primary", False),
                nickname=r.get("nickname"),
                notes=r.get("notes"),
                last_statement_date=_parse_dt(r.get("last_statement_date")),
            )
            db.add(obj)
            db.flush()
            da_map[old_id] = obj.id
            stats["demat_accounts"]["imported"] += 1

    # ── 3. Crypto accounts ───────────────────────────────────────────────────
    # Auto-create missing crypto exchanges so restore doesn't fail
    exchange_names_in_backup = {
        r.get("exchange_name", "").lower()
        for r in data.get("crypto_accounts", [])
        if r.get("exchange_name")
    }
    if exchange_names_in_backup:
        existing_exchanges = {
            row.name for row in db.query(CryptoExchangeMaster.name).all()
        }
        for ename in exchange_names_in_backup - existing_exchanges:
            db.add(CryptoExchangeMaster(
                name=ename,
                display_label=ename.replace("_", " ").title(),
                exchange_type="exchange",
                sort_order=50,
            ))
        db.flush()

    for r in data.get("crypto_accounts", []):
        old_id = r.get("id")
        existing = (
            db.query(CryptoAccount)
            .filter(
                CryptoAccount.user_id == uid,
                CryptoAccount.exchange_name == r.get("exchange_name"),
                CryptoAccount.account_id == r.get("account_id"),
            )
            .first()
        )
        if existing:
            ca_map[old_id] = existing.id
            stats["crypto_accounts"]["skipped"] += 1
        else:
            obj = CryptoAccount(
                user_id=uid,
                portfolio_id=portfolio_map.get(r.get("portfolio_id")) or default_portfolio.id,
                exchange_name=r.get("exchange_name"),
                account_id=r.get("account_id"),
                account_holder_name=r.get("account_holder_name"),
                wallet_address=r.get("wallet_address"),
                cash_balance_usd=r.get("cash_balance_usd"),
                total_value_usd=r.get("total_value_usd"),
                is_active=r.get("is_active", True),
                is_primary=r.get("is_primary", False),
                nickname=r.get("nickname"),
                notes=r.get("notes"),
                last_sync_date=_parse_dt(r.get("last_sync_date")),
            )
            db.add(obj)
            db.flush()
            ca_map[old_id] = obj.id
            stats["crypto_accounts"]["imported"] += 1

    # ── 4. Expense categories ───────────────────────────────────────────────
    # System categories (is_system=True, user_id=NULL) are matched by name to
    # existing system categories.  User-defined categories are matched by
    # user_id + name.  Only user-defined categories are created if missing.
    # First pass: create all categories without parent_id
    for r in data.get("expense_categories", []):
        old_id = r.get("id")
        is_system = r.get("is_system", False)

        if is_system:
            # System category: match existing by name only (never create)
            existing = (
                db.query(ExpenseCategory)
                .filter(
                    ExpenseCategory.is_system == True,
                    ExpenseCategory.name == r.get("name"),
                )
                .first()
            )
        else:
            # User-defined category: match by user_id + name
            existing = (
                db.query(ExpenseCategory)
                .filter(
                    ExpenseCategory.user_id == uid,
                    ExpenseCategory.name == r.get("name"),
                )
                .first()
            )

        if existing:
            cat_map[old_id] = existing.id
            stats["expense_categories"]["skipped"] += 1
        elif is_system:
            # System category not found — skip (don't create system categories)
            stats["expense_categories"]["skipped"] += 1
        else:
            obj = ExpenseCategory(
                user_id=uid,
                name=r.get("name"),
                description=r.get("description"),
                icon=r.get("icon"),
                color=r.get("color"),
                is_system=False,
                is_income=r.get("is_income", False),
                is_active=r.get("is_active", True),
                keywords=r.get("keywords"),
            )
            db.add(obj)
            db.flush()
            cat_map[old_id] = obj.id
            stats["expense_categories"]["imported"] += 1

    # Second pass: wire up parent_id using the id map
    for r in data.get("expense_categories", []):
        old_parent = r.get("parent_id")
        if old_parent and old_parent in cat_map:
            new_id = cat_map.get(r.get("id"))
            if new_id:
                cat_obj = db.query(ExpenseCategory).get(new_id)
                if cat_obj:
                    cat_obj.parent_id = cat_map[old_parent]
    db.flush()

    # ── 5. Assets ────────────────────────────────────────────────────────────
    # Track already-matched asset IDs so duplicate-name lots (e.g. multiple
    # SIP lots of the same fund) aren't collapsed into one.
    matched_asset_ids: set = set()

    for r in data.get("assets", []):
        old_id = r.get("id")

        # Remap account IDs
        new_demat_id = da_map.get(r.get("demat_account_id"))
        new_crypto_id = ca_map.get(r.get("crypto_account_id"))
        new_portfolio_id = portfolio_map.get(r.get("portfolio_id")) or default_portfolio.id

        # Find candidates matching (user, type, name) that haven't been
        # consumed by a previous import row already.
        candidates = (
            db.query(Asset)
            .filter(
                Asset.user_id == uid,
                Asset.asset_type == r.get("asset_type"),
                Asset.name == r.get("name"),
                ~Asset.id.in_(matched_asset_ids) if matched_asset_ids else True,
            )
            .all()
        )
        # Among candidates, prefer one with matching total_invested (exact lot)
        existing = None
        for c in candidates:
            if abs((c.total_invested or 0) - (r.get("total_invested") or 0)) < 1:
                existing = c
                break
        if existing is None and candidates:
            existing = candidates[0]

        if existing:
            asset_map[old_id] = existing.id
            matched_asset_ids.add(existing.id)
            stats["assets"]["skipped"] += 1
        else:
            obj = Asset(
                user_id=uid,
                portfolio_id=new_portfolio_id,
                demat_account_id=new_demat_id,
                crypto_account_id=new_crypto_id,
                asset_type=r.get("asset_type"),
                name=r.get("name"),
                symbol=r.get("symbol"),
                api_symbol=r.get("api_symbol"),
                isin=r.get("isin"),
                account_id=r.get("account_id"),
                broker_name=r.get("broker_name"),
                account_holder_name=r.get("account_holder_name"),
                quantity=r.get("quantity", 0),
                purchase_price=r.get("purchase_price", 0),
                current_price=r.get("current_price", 0),
                total_invested=r.get("total_invested", 0),
                current_value=r.get("current_value", 0),
                profit_loss=r.get("profit_loss", 0),
                profit_loss_percentage=r.get("profit_loss_percentage", 0),
                details=r.get("details"),
                is_active=r.get("is_active", True),
                notes=r.get("notes"),
                purchase_date=_parse_dt(r.get("purchase_date")),
            )
            db.add(obj)
            db.flush()
            asset_map[old_id] = obj.id
            matched_asset_ids.add(obj.id)
            stats["assets"]["imported"] += 1

    # ── 6. Transactions ──────────────────────────────────────────────────────
    for r in data.get("transactions", []):
        new_asset_id = asset_map.get(r.get("asset_id"))
        if not new_asset_id:
            continue  # orphaned; skip

        txn_date = _parse_dt(r.get("transaction_date"))
        existing = (
            db.query(Transaction)
            .filter(
                Transaction.asset_id == new_asset_id,
                Transaction.transaction_date == txn_date,
                Transaction.total_amount == r.get("total_amount"),
                Transaction.transaction_type == r.get("transaction_type"),
            )
            .first()
        )
        if existing:
            stats["transactions"]["skipped"] += 1
        else:
            obj = Transaction(
                asset_id=new_asset_id,
                transaction_type=r.get("transaction_type"),
                transaction_date=txn_date,
                quantity=r.get("quantity"),
                price_per_unit=r.get("price_per_unit"),
                total_amount=r.get("total_amount"),
                fees=r.get("fees"),
                taxes=r.get("taxes"),
                description=r.get("description"),
                reference_number=r.get("reference_number"),
                notes=r.get("notes"),
            )
            db.add(obj)
            stats["transactions"]["imported"] += 1

    # ── 6b. Mutual fund holdings ──────────────────────────────────────────────
    for r in data.get("mutual_fund_holdings", []):
        new_asset_id = asset_map.get(r.get("asset_id"))
        if not new_asset_id:
            continue  # orphaned; skip

        # Match by (asset_id, stock_symbol, isin) to detect duplicates
        existing = (
            db.query(MutualFundHolding)
            .filter(
                MutualFundHolding.asset_id == new_asset_id,
                MutualFundHolding.stock_name == r.get("stock_name"),
                MutualFundHolding.stock_symbol == r.get("stock_symbol"),
            )
            .first()
        )
        if existing:
            stats["mutual_fund_holdings"]["skipped"] += 1
        else:
            obj = MutualFundHolding(
                asset_id=new_asset_id,
                user_id=uid,
                stock_name=r.get("stock_name"),
                stock_symbol=r.get("stock_symbol"),
                isin=r.get("isin"),
                holding_percentage=r.get("holding_percentage", 0),
                holding_value=r.get("holding_value", 0),
                quantity_held=r.get("quantity_held", 0),
                sector=r.get("sector"),
                industry=r.get("industry"),
                market_cap=r.get("market_cap"),
                stock_current_price=r.get("stock_current_price", 0),
                data_source=r.get("data_source"),
            )
            db.add(obj)
            stats["mutual_fund_holdings"]["imported"] += 1

    # ── 7. Expenses ──────────────────────────────────────────────────────────
    for r in data.get("expenses", []):
        new_ba_id = ba_map.get(r.get("bank_account_id"))
        new_cat_id = cat_map.get(r.get("category_id"))
        txn_date = _parse_dt(r.get("transaction_date"))

        # bank_account_id is NOT NULL — skip if we can't remap
        if not new_ba_id:
            stats["expenses"]["skipped"] += 1
            continue

        existing = (
            db.query(Expense)
            .filter(
                Expense.user_id == uid,
                Expense.bank_account_id == new_ba_id,
                Expense.transaction_date == txn_date,
                Expense.amount == r.get("amount"),
                Expense.description == r.get("description"),
            )
            .first()
        )
        if existing:
            stats["expenses"]["skipped"] += 1
        else:
            obj = Expense(
                user_id=uid,
                portfolio_id=portfolio_map.get(r.get("portfolio_id")) or default_portfolio.id,
                bank_account_id=new_ba_id,
                category_id=new_cat_id,
                transaction_date=txn_date,
                transaction_type=r.get("transaction_type"),
                amount=r.get("amount"),
                balance_after=r.get("balance_after"),
                description=r.get("description"),
                merchant_name=r.get("merchant_name"),
                reference_number=r.get("reference_number"),
                payment_method=r.get("payment_method"),
                is_categorized=r.get("is_categorized", False),
                is_recurring=r.get("is_recurring", False),
                is_split=r.get("is_split", False),
                is_reconciled=r.get("is_reconciled", False),
                location=r.get("location"),
                notes=r.get("notes"),
                tags=r.get("tags"),
            )
            db.add(obj)
            stats["expenses"]["imported"] += 1

    # ── 8. Alerts ────────────────────────────────────────────────────────────
    for r in data.get("alerts", []):
        new_asset_id = asset_map.get(r.get("asset_id"))
        alert_date = _parse_dt(r.get("alert_date"))

        existing = (
            db.query(Alert)
            .filter(
                Alert.user_id == uid,
                Alert.alert_type == r.get("alert_type"),
                Alert.title == r.get("title"),
                Alert.alert_date == alert_date,
            )
            .first()
        )
        if existing:
            stats["alerts"]["skipped"] += 1
        else:
            obj = Alert(
                user_id=uid,
                asset_id=new_asset_id,
                alert_type=r.get("alert_type"),
                severity=r.get("severity"),
                title=r.get("title"),
                message=r.get("message"),
                suggested_action=r.get("suggested_action"),
                action_url=r.get("action_url"),
                is_read=r.get("is_read", False),
                is_dismissed=r.get("is_dismissed", False),
                is_actionable=r.get("is_actionable", True),
                alert_date=alert_date,
                read_at=_parse_dt(r.get("read_at")),
                dismissed_at=_parse_dt(r.get("dismissed_at")),
            )
            db.add(obj)
            stats["alerts"]["imported"] += 1
    db.flush()

    # ── 9. Portfolio snapshots ────────────────────────────────────────────────
    for r in data.get("portfolio_snapshots", []):
        snap_date_str = r.get("snapshot_date")
        try:
            snap_date = date.fromisoformat(snap_date_str) if snap_date_str else None
        except (ValueError, TypeError):
            snap_date = None
        if not snap_date:
            continue

        existing = (
            db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.user_id == uid,
                PortfolioSnapshot.snapshot_date == snap_date,
            )
            .first()
        )
        if existing:
            stats["portfolio_snapshots"]["skipped"] += 1
            # Still need to count child asset_snapshots as skipped
            stats["asset_snapshots"]["skipped"] += len(r.get("asset_snapshots", []))
        else:
            ps = PortfolioSnapshot(
                user_id=uid,
                snapshot_date=snap_date,
                total_invested=r.get("total_invested", 0),
                total_current_value=r.get("total_current_value", 0),
                total_profit_loss=r.get("total_profit_loss", 0),
                total_profit_loss_percentage=r.get("total_profit_loss_percentage", 0),
                total_assets_count=r.get("total_assets_count", 0),
            )
            db.add(ps)
            db.flush()
            stats["portfolio_snapshots"]["imported"] += 1

            for a_snap in r.get("asset_snapshots", []):
                a_snap_date_str = a_snap.get("snapshot_date")
                try:
                    a_snap_date = date.fromisoformat(a_snap_date_str) if a_snap_date_str else snap_date
                except (ValueError, TypeError):
                    a_snap_date = snap_date

                new_asset_id = asset_map.get(a_snap.get("asset_id"))

                # v5.0+: snapshot_source and account FK columns
                # v1.0-4.0 backward compat: infer from old asset_type string
                snapshot_source = a_snap.get("snapshot_source")
                asset_type_val = a_snap.get("asset_type")
                if not snapshot_source:
                    if asset_type_val in ("bank_account", "bank_balance"):
                        snapshot_source = "bank_account"
                        asset_type_val = None
                    elif asset_type_val == "demat_cash":
                        snapshot_source = "demat_cash"
                        asset_type_val = None
                    elif asset_type_val == "crypto_cash":
                        snapshot_source = "crypto_cash"
                        asset_type_val = None
                    else:
                        snapshot_source = "asset"

                obj = AssetSnapshot(
                    portfolio_snapshot_id=ps.id,
                    snapshot_date=a_snap_date,
                    snapshot_source=snapshot_source,
                    asset_id=new_asset_id,
                    bank_account_id=ba_map.get(a_snap.get("bank_account_id")),
                    demat_account_id=da_map.get(a_snap.get("demat_account_id")),
                    crypto_account_id=ca_map.get(a_snap.get("crypto_account_id")),
                    asset_type=asset_type_val,
                    asset_name=a_snap.get("asset_name"),
                    asset_symbol=a_snap.get("asset_symbol"),
                    quantity=a_snap.get("quantity", 0),
                    purchase_price=a_snap.get("purchase_price", 0),
                    current_price=a_snap.get("current_price", 0),
                    total_invested=a_snap.get("total_invested", 0),
                    current_value=a_snap.get("current_value", 0),
                    profit_loss=a_snap.get("profit_loss", 0),
                    profit_loss_percentage=a_snap.get("profit_loss_percentage", 0),
                )
                db.add(obj)
                stats["asset_snapshots"]["imported"] += 1

    db.commit()

    total_imported = sum(v["imported"] for v in stats.values())
    total_skipped = sum(v["skipped"] for v in stats.values())

    return {
        "success": True,
        "message": f"Restore complete. {total_imported} records imported, {total_skipped} skipped (already exist).",
        "stats": stats,
    }


# ─── PDF statement ──────────────────────────────────────────────────────────

@router.get("/statement/pdf")
async def generate_pdf_statement(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate a PDF portfolio statement for the current user."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    uid = current_user.id
    assets = db.query(Asset).filter(Asset.user_id == uid, Asset.is_active == True).all()
    bank_accounts = db.query(BankAccount).filter(BankAccount.user_id == uid, BankAccount.is_active == True).all()
    demat_accounts = db.query(DematAccount).filter(DematAccount.user_id == uid, DematAccount.is_active == True).all()
    crypto_accounts = db.query(CryptoAccount).filter(CryptoAccount.user_id == uid, CryptoAccount.is_active == True).all()

    # ── Recalculate metrics in-memory (same as Dashboard) ────────────────────
    # The dashboard calls calculate_metrics() + commit before summing; we do
    # the same recalculation in-memory (no commit) so the PDF matches exactly.
    for a in assets:
        a.calculate_metrics()

    # ── Aggregates ────────────────────────────────────────────────────────────
    asset_invested = sum(a.total_invested or 0 for a in assets)
    asset_value = sum(a.current_value or 0 for a in assets)
    asset_pl = asset_value - asset_invested
    asset_pl_pct = (asset_pl / asset_invested * 100) if asset_invested else 0
    bank_total = sum(b.current_balance or 0 for b in bank_accounts)
    demat_cash_total = sum(d.cash_balance or 0 for d in demat_accounts)
    crypto_cash_total = sum(c.cash_balance_usd or 0 for c in crypto_accounts)

    # Dashboard-matching totals: include bank + demat + crypto cash in invested & value
    total_invested = asset_invested + bank_total + demat_cash_total + crypto_cash_total
    total_value = asset_value + bank_total + demat_cash_total + crypto_cash_total
    # P&L is only from assets (bank, demat & crypto cash have zero gain)
    total_pl = asset_pl
    total_pl_pct = (total_pl / total_invested * 100) if total_invested else 0

    from collections import defaultdict
    by_type: Dict[str, List[Asset]] = defaultdict(list)
    for a in assets:
        by_type[a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type)].append(a)

    # ── Formatting helpers ────────────────────────────────────────────────────
    # Use "Rs." — the rupee Unicode char (U+20B9) is NOT in built-in PDF fonts
    # and renders as a black rectangle.  "Rs." is universally supported.
    def inr(val: float) -> str:
        return f"Rs.{val:,.0f}"

    def pct(val: float) -> str:
        sign = "+" if val >= 0 else ""
        return f"{sign}{val:.2f}%"

    def fmt_qty(q) -> str:
        """Format quantity without scientific notation."""
        if q is None:
            return "—"
        if q == int(q):
            return f"{int(q):,}"
        # Up to 4 significant decimal places, strip trailing zeros
        return f"{q:,.4f}".rstrip("0").rstrip(".")

    # ── PDF document setup ───────────────────────────────────────────────────
    # A4 printable width = 21 cm - 2*2 cm margins = 17 cm
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    BLUE = colors.HexColor("#1976d2")
    LIGHT_BLUE = colors.HexColor("#e3f2fd")
    GREY_LINE = colors.HexColor("#e0e0e0")

    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"], fontSize=20, spaceAfter=4, textColor=BLUE,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=11, spaceBefore=12,
        spaceAfter=4, textColor=BLUE,
    )
    normal = styles["Normal"]

    # ── Base table style (NO Paragraph objects in cells, NO ROWBACKGROUNDS) ──
    # Plain strings only → row heights are predictable and text never overlaps.
    BASE = [
        ("BACKGROUND",   (0, 0), (-1,  0), BLUE),
        ("TEXTCOLOR",    (0, 0), (-1,  0), colors.white),
        ("FONTNAME",     (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR",    (0, 1), (-1, -1), colors.black),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("ALIGN",        (1, 1), (-1, -1), "RIGHT"),
        ("LINEBELOW",    (0, 0), (-1,  0), 0.5, BLUE),
        ("LINEBELOW",    (0, 1), (-1, -2), 0.25, GREY_LINE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]

    TOTALS_ROW = [
        ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_BLUE),
        ("TEXTCOLOR",  (0, -1), (-1, -1), colors.black),
        ("LINEABOVE",  (0, -1), (-1, -1), 0.5, BLUE),
    ]

    ASSET_TYPE_LABELS = {
        "stock": "Stocks", "us_stock": "US Stocks",
        "equity_mutual_fund": "Equity Mutual Funds",
        "hybrid_mutual_fund": "Hybrid Mutual Funds",
        "debt_mutual_fund": "Debt Mutual Funds",
        "commodity": "Commodities", "crypto": "Crypto",
        "ppf": "PPF", "pf": "PF / EPF", "nps": "NPS", "ssy": "SSY",
        "gratuity": "Gratuity", "insurance_policy": "Insurance",
        "fixed_deposit": "Fixed Deposits",
        "recurring_deposit": "Recurring Deposits",
        "savings_account": "Savings Accounts",
        "real_estate": "Real Estate", "cash": "Cash",
        "nsc": "NSC", "kvp": "KVP", "scss": "SCSS", "mis": "MIS",
        "corporate_bond": "Corporate Bonds", "rbi_bond": "RBI Bonds",
        "tax_saving_bond": "Tax Saving Bonds",
        "reit": "REITs", "invit": "InvITs",
        "sovereign_gold_bond": "Sovereign Gold Bonds",
        "esop": "ESOPs", "rsu": "RSUs",
    }

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Portfolio Statement", title_style))
    story.append(Paragraph(
        f"<font size='9' color='grey'>Generated {datetime.now().strftime('%d %b %Y, %H:%M')}"
        f"  |  {current_user.email}</font>",
        normal,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=8))

    # ── Summary table (4 cols × 4.25 cm = 17 cm) ─────────────────────────────
    pl_color = "#2e7d32" if total_pl >= 0 else "#c62828"
    summary_data = [
        ["Total Invested", "Current Value", "Profit / Loss", "Return"],
        [
            inr(total_invested),
            inr(total_value),
            ("+" if total_pl >= 0 else "") + inr(total_pl),
            pct(total_pl_pct),
        ],
    ]
    summary_tbl = Table(summary_data, colWidths=[4.25 * cm] * 4)
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1,  0), BLUE),
        ("TEXTCOLOR",    (0, 0), (-1,  0), colors.white),
        ("FONTNAME",     (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR",    (0, 1), (-1, -1), colors.black),
        ("FONTNAME",     (0, 1), (-1,  1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 1), (-1,  1), 11),
        ("TEXTCOLOR",    (2, 1), (3,  1),  colors.HexColor(pl_color)),
        ("BOX",          (0, 0), (-1, -1), 0.5, BLUE),
        ("LINEBELOW",    (0, 0), (-1,  0), 0.5, BLUE),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 0.3 * cm))

    # ── Allocation summary (6 cols, total 17 cm) ──────────────────────────────
    # [4.5, 1.2, 2.9, 2.9, 2.9, 2.6] = 17.0
    story.append(Paragraph("Asset Allocation Summary", section_style))
    alloc_rows = [["Asset Type", "Count", "Invested", "Value", "P&L", "Return"]]
    for atype, group in sorted(by_type.items()):
        inv = sum(a.total_invested or 0 for a in group)
        val = sum(a.current_value or 0 for a in group)
        pl  = val - inv
        pl_p = (pl / inv * 100) if inv else 0
        alloc_rows.append([
            ASSET_TYPE_LABELS.get(atype, atype.replace("_", " ").title()),
            str(len(group)),
            inr(inv), inr(val),
            ("+" if pl >= 0 else "") + inr(pl),
            pct(pl_p),
        ])
    # Bank Accounts row (invested = value = balance, P&L = 0)
    if bank_accounts:
        alloc_rows.append([
            "Bank Accounts", str(len(bank_accounts)),
            inr(bank_total), inr(bank_total),
            "+Rs.0", "+0.00%",
        ])
    # Demat Cash row (invested = value = cash balance, P&L = 0)
    demat_with_cash = [d for d in demat_accounts if (d.cash_balance or 0) > 0]
    if demat_with_cash:
        alloc_rows.append([
            "Demat Cash", str(len(demat_with_cash)),
            inr(demat_cash_total), inr(demat_cash_total),
            "+Rs.0", "+0.00%",
        ])
    # Crypto Cash row (invested = value = cash balance in USD, P&L = 0)
    crypto_with_cash = [c for c in crypto_accounts if (c.cash_balance_usd or 0) > 0]
    if crypto_with_cash:
        alloc_rows.append([
            "Crypto Cash", str(len(crypto_with_cash)),
            inr(crypto_cash_total), inr(crypto_cash_total),
            "+Rs.0", "+0.00%",
        ])
    alloc_rows.append([
        "TOTAL", str(len(assets) + len(bank_accounts) + len(demat_with_cash) + len(crypto_with_cash)),
        inr(total_invested), inr(total_value),
        ("+" if total_pl >= 0 else "") + inr(total_pl),
        pct(total_pl_pct),
    ])
    alloc_tbl = Table(alloc_rows, colWidths=[4.5*cm, 1.2*cm, 2.9*cm, 2.9*cm, 2.9*cm, 2.6*cm])
    alloc_tbl.setStyle(TableStyle(BASE + TOTALS_ROW))
    story.append(alloc_tbl)

    # ── Individual asset tables ───────────────────────────────────────────────
    # 7 cols, total 17 cm: [6.0, 1.3, 1.4, 2.3, 2.3, 2.3, 1.4]
    # Name column uses Paragraph for multi-line wrapping.
    # All other columns are plain strings (keeps row height predictable).

    MAX_SYM_LEN = 14  # fits comfortably in the 1.3 cm column

    def short_symbol(a) -> str:
        """Return a short ticker for the PDF Symbol column.

        Many mutual funds store the full fund name as both `symbol` and
        `api_symbol`.  Showing that next to the Name column is useless
        and causes garbled overlapping text.  Only display genuinely
        short ticker-style symbols; otherwise show '—'.
        """
        sym = a.symbol or ""
        name = a.name or ""
        # If symbol is short and different from the name, use it as-is
        if sym and sym != name and len(sym) <= MAX_SYM_LEN:
            return sym
        # Try api_symbol as fallback, but only if it's short
        api_sym = a.api_symbol or ""
        if api_sym and len(api_sym) <= MAX_SYM_LEN:
            return api_sym
        return "—"

    # Maximum characters for the Name column as a plain string.
    # At 8pt Helvetica, ~38 chars fit in 6 cm without wrapping.
    MAX_NAME_LEN = 38

    def short_name(a) -> str:
        name = a.name or "—"
        if len(name) <= MAX_NAME_LEN:
            return name
        return name[: MAX_NAME_LEN - 1] + "…"

    for atype, group in sorted(by_type.items()):
        label = ASSET_TYPE_LABELS.get(atype, atype.replace("_", " ").title())
        story.append(Paragraph(label, section_style))
        rows = [["Name", "Symbol", "Qty", "Invested", "Value", "P&L", "Return"]]
        for a in sorted(group, key=lambda x: -(x.current_value or 0)):
            pl   = (a.current_value or 0) - (a.total_invested or 0)
            pl_p = (pl / a.total_invested * 100) if a.total_invested else 0
            rows.append([
                short_name(a),
                short_symbol(a),
                fmt_qty(a.quantity),
                inr(a.total_invested or 0),
                inr(a.current_value or 0),
                ("+" if pl >= 0 else "") + inr(pl),
                pct(pl_p),
            ])
        tbl = Table(rows, colWidths=[6.0*cm, 1.3*cm, 1.4*cm, 2.3*cm, 2.3*cm, 2.3*cm, 1.4*cm])
        tbl.setStyle(TableStyle(BASE))
        story.append(tbl)

    # ── Bank accounts (5 cols, 17 cm: [3.5, 3.0, 2.5, 5.0, 3.0]) ────────────
    if bank_accounts:
        story.append(Paragraph("Bank Accounts", section_style))
        ba_rows = [["Bank", "Type", "Account No.", "Nickname", "Balance"]]
        for b in bank_accounts:
            bname = str(b.bank_name)
            btype = b.account_type.value if hasattr(b.account_type, "value") else str(b.account_type)
            masked = f"xxxx{b.account_number[-4:]}" if b.account_number else "—"
            ba_rows.append([
                bname.replace("_", " ").title(),
                btype.replace("_", " ").title(),
                masked,
                b.nickname or "—",
                inr(b.current_balance or 0),
            ])
        ba_rows.append(["", "", "", "Total", inr(bank_total)])
        ba_tbl = Table(ba_rows, colWidths=[3.5*cm, 3.0*cm, 2.5*cm, 5.0*cm, 3.0*cm])
        ba_tbl.setStyle(TableStyle(BASE + TOTALS_ROW))
        story.append(ba_tbl)

    # ── Demat accounts (5 cols, 17 cm: [3.5, 3.0, 3.0, 4.5, 3.0]) ────────────
    if demat_accounts:
        story.append(Paragraph("Demat / Trading Accounts", section_style))
        da_rows = [["Broker", "Account ID", "Currency", "Nickname", "Cash Balance"]]
        for d in demat_accounts:
            broker = str(d.broker_name)
            da_rows.append([
                broker.replace("_", " ").title(),
                d.account_id or "—",
                d.currency or "INR",
                d.nickname or "—",
                inr(d.cash_balance or 0),
            ])
        da_rows.append(["", "", "", "Total", inr(demat_cash_total)])
        da_tbl = Table(da_rows, colWidths=[3.5*cm, 3.0*cm, 3.0*cm, 4.5*cm, 3.0*cm])
        da_tbl.setStyle(TableStyle(BASE + TOTALS_ROW))
        story.append(da_tbl)

    # ── Crypto accounts (5 cols, 17 cm: [3.5, 3.0, 3.5, 4.0, 3.0]) ────────
    if crypto_accounts:
        story.append(Paragraph("Crypto Accounts", section_style))
        ca_rows = [["Exchange", "Account", "Currency", "Nickname", "Cash (USD)"]]
        for c in crypto_accounts:
            exchange = str(c.exchange_name)
            ca_rows.append([
                exchange.replace("_", " ").title(),
                c.account_id or "—",
                "USD",
                c.account_name or "—",
                inr(c.cash_balance_usd or 0),
            ])
        ca_rows.append(["", "", "", "Total", inr(crypto_cash_total)])
        ca_tbl = Table(ca_rows, colWidths=[3.5*cm, 3.0*cm, 3.5*cm, 4.0*cm, 3.0*cm])
        ca_tbl.setStyle(TableStyle(BASE + TOTALS_ROW))
        story.append(ca_tbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "<font size='7' color='grey'>This statement is for informational purposes only. "
        "Values shown are as of the last update and may not reflect real-time market prices.</font>",
        normal,
    ))

    doc.build(story)
    buf.seek(0)

    filename = f"portfolio_statement_{datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# Made with Bob
