"""Recurring Deposit API Endpoints"""
import calendar
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_db, get_default_portfolio_id
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.schemas.recurring_deposit import (
    RDAccountCreate,
    RDAccountUpdate,
    RDAccountResponse,
    RDAccountWithTransactions,
    RDTransactionCreate,
    RDTransactionUpdate,
    RDTransactionResponse,
    RDSummary,
    RDGenerateResponse,
)

router = APIRouter()


def _add_months(dt: date, months: int) -> date:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _asset_to_rd(asset: Asset) -> RDAccountResponse:
    d = asset.details or {}
    start_date = (
        datetime.strptime(d["start_date"], "%Y-%m-%d").date()
        if d.get("start_date")
        else (asset.purchase_date.date() if asset.purchase_date else date.today())
    )
    maturity_date = (
        datetime.strptime(d["maturity_date"], "%Y-%m-%d").date()
        if d.get("maturity_date")
        else None
    )
    return RDAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        bank_name=d.get("bank_name", ""),
        nickname=asset.name,
        account_number=asset.account_id,
        monthly_installment=d.get("monthly_installment", 0.0),
        interest_rate=d.get("interest_rate", 0.0),
        start_date=start_date,
        maturity_date=maturity_date,
        auto_update=d.get("auto_update", False),
        notes=asset.notes,
        total_deposited=asset.total_invested,
        current_value=asset.current_value,
        total_interest_earned=max(0.0, asset.profit_loss),
        created_at=asset.created_at,
        updated_at=asset.last_updated,
    )


def _tx_to_rd(tx: Transaction) -> RDTransactionResponse:
    tx_type = "interest" if tx.transaction_type == TransactionType.INTEREST else "installment"
    return RDTransactionResponse(
        id=tx.id,
        asset_id=tx.asset_id,
        transaction_date=tx.transaction_date.date() if tx.transaction_date else date.today(),
        amount=tx.total_amount,
        transaction_type=tx_type,
        description=tx.description,
        is_auto_generated=(tx.reference_number == "AUTO_GENERATED"),
        created_at=tx.created_at,
    )


def _recalc_rd_value(asset: Asset, db: Session):
    """Recalculate current_value = total_deposited + total_interest."""
    deposits = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.DEPOSIT,
        )
        .all()
    )
    interest_txs = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
        )
        .all()
    )
    total_deposited = sum(t.total_amount for t in deposits)
    total_interest = sum(t.total_amount for t in interest_txs)
    asset.total_invested = total_deposited
    asset.current_value = total_deposited + total_interest
    asset.profit_loss = total_interest
    asset.last_updated = datetime.utcnow()


@router.get("/", response_model=List[RDAccountResponse])
async def list_rds(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all recurring deposits for the current user."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.RECURRING_DEPOSIT,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.order_by(Asset.created_at.desc()).all()
    return [_asset_to_rd(a) for a in assets]


@router.get("/summary", response_model=RDSummary)
async def rd_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Summary statistics for all recurring deposits."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.RECURRING_DEPOSIT,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    return RDSummary(
        total_accounts=len(assets),
        total_deposited=sum(a.total_invested for a in assets),
        total_current_value=sum(a.current_value for a in assets),
        total_interest_earned=sum(max(0.0, a.profit_loss) for a in assets),
    )


@router.post("/", response_model=RDAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_rd(
    data: RDAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new recurring deposit."""
    resolved_portfolio_id = portfolio_id or data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    asset = Asset(
        user_id=current_user.id,
        portfolio_id=resolved_portfolio_id,
        asset_type=AssetType.RECURRING_DEPOSIT,
        name=data.nickname or data.bank_name,
        account_id=data.account_number,
        quantity=1,
        purchase_price=data.monthly_installment,
        current_price=data.monthly_installment,
        total_invested=0.0,
        current_value=0.0,
        profit_loss=0.0,
        purchase_date=datetime.combine(data.start_date, datetime.min.time()),
        notes=data.notes,
        details={
            "bank_name": data.bank_name,
            "monthly_installment": data.monthly_installment,
            "interest_rate": data.interest_rate,
            "start_date": data.start_date.strftime("%Y-%m-%d"),
            "maturity_date": data.maturity_date.strftime("%Y-%m-%d") if data.maturity_date else None,
            "auto_update": data.auto_update,
        },
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset_to_rd(asset)


@router.get("/{rd_id}", response_model=RDAccountWithTransactions)
async def get_rd(
    rd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a recurring deposit with all its transactions."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type.in_(
                [TransactionType.DEPOSIT, TransactionType.INTEREST]
            ),
        )
        .order_by(Transaction.transaction_date.desc())
        .all()
    )
    rd_data = _asset_to_rd(asset)
    return RDAccountWithTransactions(
        **rd_data.dict(),
        transactions=[_tx_to_rd(t) for t in txs],
        transaction_count=len(txs),
    )


@router.put("/{rd_id}", response_model=RDAccountResponse)
async def update_rd(
    rd_id: int,
    data: RDAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a recurring deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    upd = data.dict(exclude_unset=True)
    d = dict(asset.details or {})

    if "bank_name" in upd:
        d["bank_name"] = upd["bank_name"]
    if "nickname" in upd and upd["nickname"]:
        asset.name = upd["nickname"]
    if "account_number" in upd:
        asset.account_id = upd["account_number"]
    if "monthly_installment" in upd:
        d["monthly_installment"] = upd["monthly_installment"]
        asset.purchase_price = upd["monthly_installment"]
    if "interest_rate" in upd:
        d["interest_rate"] = upd["interest_rate"]
    if "start_date" in upd:
        d["start_date"] = upd["start_date"].strftime("%Y-%m-%d")
        asset.purchase_date = datetime.combine(upd["start_date"], datetime.min.time())
    if "maturity_date" in upd:
        d["maturity_date"] = (
            upd["maturity_date"].strftime("%Y-%m-%d") if upd["maturity_date"] else None
        )
    if "auto_update" in upd:
        d["auto_update"] = upd["auto_update"]
    if "notes" in upd:
        asset.notes = upd["notes"]

    asset.details = d
    _recalc_rd_value(asset, db)
    db.commit()
    db.refresh(asset)
    return _asset_to_rd(asset)


@router.delete("/{rd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rd(
    rd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a recurring deposit and all its transactions."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")
    db.query(Transaction).filter(Transaction.asset_id == asset.id).delete()
    db.delete(asset)
    db.commit()


@router.post("/{rd_id}/generate", response_model=RDGenerateResponse)
async def generate_rd_transactions(
    rd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate outstanding installment and interest transactions for a recurring deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    d = asset.details or {}
    monthly_installment = d.get("monthly_installment", 0.0)
    rate = d.get("interest_rate", 0.0)
    start_date = (
        datetime.strptime(d["start_date"], "%Y-%m-%d").date()
        if d.get("start_date")
        else (asset.purchase_date.date() if asset.purchase_date else date.today())
    )
    maturity_date = (
        datetime.strptime(d["maturity_date"], "%Y-%m-%d").date()
        if d.get("maturity_date")
        else None
    )

    today = date.today()
    end_date = min(today, maturity_date) if maturity_date else today

    # Find last auto-generated deposit to know where to resume
    last_auto_deposit = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.DEPOSIT,
            Transaction.reference_number == "AUTO_GENERATED",
        )
        .order_by(Transaction.transaction_date.desc())
        .first()
    )

    next_month = (
        _add_months(last_auto_deposit.transaction_date.date(), 1)
        if last_auto_deposit
        else start_date
    )

    if next_month > end_date:
        _recalc_rd_value(asset, db)
        db.commit()
        return RDGenerateResponse(
            installments_created=0,
            interest_transactions_created=0,
            new_current_value=asset.current_value,
            total_interest_earned=max(0.0, asset.profit_loss),
        )

    # Start accumulated balance from existing deposits + interest
    existing_deposits = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.DEPOSIT,
        )
        .all()
    )
    existing_interest = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
        )
        .all()
    )
    accumulated = sum(t.total_amount for t in existing_deposits) + sum(
        t.total_amount for t in existing_interest
    )

    installments_created = 0
    interest_created = 0
    current_date = next_month

    while current_date <= end_date:
        # Add monthly installment
        dep_tx = Transaction(
            asset_id=asset.id,
            transaction_type=TransactionType.DEPOSIT,
            transaction_date=datetime.combine(current_date, datetime.min.time()),
            quantity=1,
            price_per_unit=monthly_installment,
            total_amount=monthly_installment,
            fees=0.0,
            taxes=0.0,
            description="Monthly installment",
            reference_number="AUTO_GENERATED",
        )
        db.add(dep_tx)
        accumulated += monthly_installment
        installments_created += 1

        # Add monthly interest on accumulated balance (monthly compounding)
        interest_amount = round(accumulated * (rate / 12 / 100), 2)
        if interest_amount > 0:
            int_tx = Transaction(
                asset_id=asset.id,
                transaction_type=TransactionType.INTEREST,
                transaction_date=datetime.combine(current_date, datetime.min.time()),
                quantity=1,
                price_per_unit=interest_amount,
                total_amount=interest_amount,
                fees=0.0,
                taxes=0.0,
                description="Monthly interest",
                reference_number="AUTO_GENERATED",
            )
            db.add(int_tx)
            accumulated += interest_amount
            interest_created += 1

        current_date = _add_months(current_date, 1)

    db.flush()
    _recalc_rd_value(asset, db)
    db.commit()
    return RDGenerateResponse(
        installments_created=installments_created,
        interest_transactions_created=interest_created,
        new_current_value=asset.current_value,
        total_interest_earned=max(0.0, asset.profit_loss),
    )


@router.post(
    "/{rd_id}/transactions",
    response_model=RDTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_rd_transaction(
    rd_id: int,
    data: RDTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a manual transaction (installment or interest) to a recurring deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    trans_type = (
        TransactionType.INTEREST if data.transaction_type == "interest" else TransactionType.DEPOSIT
    )
    tx = Transaction(
        asset_id=asset.id,
        transaction_type=trans_type,
        transaction_date=datetime.combine(data.transaction_date, datetime.min.time()),
        quantity=1,
        price_per_unit=data.amount,
        total_amount=data.amount,
        fees=0.0,
        taxes=0.0,
        description=data.description,
        reference_number=None,  # manual — not AUTO_GENERATED
    )
    db.add(tx)
    db.flush()
    _recalc_rd_value(asset, db)
    db.commit()
    db.refresh(tx)
    return _tx_to_rd(tx)


@router.put("/{rd_id}/transactions/{tx_id}", response_model=RDTransactionResponse)
async def update_rd_transaction(
    rd_id: int,
    tx_id: int,
    data: RDTransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a transaction on a recurring deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == tx_id,
            Transaction.asset_id == asset.id,
            Transaction.transaction_type.in_(
                [TransactionType.DEPOSIT, TransactionType.INTEREST]
            ),
        )
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    upd = data.dict(exclude_unset=True)
    if "transaction_date" in upd:
        tx.transaction_date = datetime.combine(upd["transaction_date"], datetime.min.time())
    if "amount" in upd:
        tx.total_amount = upd["amount"]
        tx.price_per_unit = upd["amount"]
    if "description" in upd:
        tx.description = upd["description"]

    _recalc_rd_value(asset, db)
    db.commit()
    db.refresh(tx)
    return _tx_to_rd(tx)


@router.delete("/{rd_id}/transactions/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rd_transaction(
    rd_id: int,
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction from a recurring deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == rd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.RECURRING_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Recurring deposit not found")

    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == tx_id,
            Transaction.asset_id == asset.id,
            Transaction.transaction_type.in_(
                [TransactionType.DEPOSIT, TransactionType.INTEREST]
            ),
        )
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(tx)
    _recalc_rd_value(asset, db)
    db.commit()

# Made with Bob
