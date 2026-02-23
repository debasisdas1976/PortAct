"""Fixed Deposit API Endpoints"""
import calendar
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, get_db, get_default_portfolio_id
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.schemas.fixed_deposit import (
    FDAccountCreate,
    FDAccountUpdate,
    FDAccountResponse,
    FDAccountWithTransactions,
    FDTransactionCreate,
    FDTransactionUpdate,
    FDTransactionResponse,
    FDSummary,
    FDGenerateInterestResponse,
)

router = APIRouter()

FREQ_MONTHS = {"monthly": 1, "quarterly": 3, "half_yearly": 6, "annually": 12}
PERIODS_PER_YEAR = {"monthly": 12, "quarterly": 4, "half_yearly": 2, "annually": 1}


def _add_months(dt: date, months: int) -> date:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _asset_to_fd(asset: Asset) -> FDAccountResponse:
    d = asset.details or {}
    principal = d.get("principal_amount", asset.total_invested)
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
    return FDAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        bank_name=d.get("bank_name", ""),
        nickname=asset.name,
        account_number=asset.account_id,
        principal_amount=principal,
        interest_rate=d.get("interest_rate", 0.0),
        interest_type=d.get("interest_type", "simple"),
        compounding_frequency=d.get("compounding_frequency", "annually"),
        start_date=start_date,
        maturity_date=maturity_date,
        auto_update=d.get("auto_update", False),
        notes=asset.notes,
        current_value=asset.current_value,
        total_interest_earned=max(0.0, asset.current_value - principal),
        created_at=asset.created_at,
        updated_at=asset.last_updated,
    )


def _tx_to_fd(tx: Transaction) -> FDTransactionResponse:
    return FDTransactionResponse(
        id=tx.id,
        asset_id=tx.asset_id,
        transaction_date=tx.transaction_date.date() if tx.transaction_date else date.today(),
        amount=tx.total_amount,
        description=tx.description,
        is_auto_generated=(tx.reference_number == "AUTO_GENERATED"),
        created_at=tx.created_at,
    )


def _recalc_fd_value(asset: Asset, db: Session):
    """Recalculate current_value = principal + sum(interest transactions)."""
    d = asset.details or {}
    principal = d.get("principal_amount", asset.total_invested)
    interest_txs = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
        )
        .all()
    )
    total_interest = sum(t.total_amount for t in interest_txs)
    asset.current_value = principal + total_interest
    asset.profit_loss = total_interest
    asset.last_updated = datetime.utcnow()


@router.get("/", response_model=List[FDAccountResponse])
async def list_fds(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all fixed deposits for the current user."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.FIXED_DEPOSIT,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.order_by(Asset.created_at.desc()).all()
    return [_asset_to_fd(a) for a in assets]


@router.get("/summary", response_model=FDSummary)
async def fd_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Summary statistics for all fixed deposits."""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.FIXED_DEPOSIT,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()
    total_principal = sum(
        (a.details or {}).get("principal_amount", a.total_invested) for a in assets
    )
    total_value = sum(a.current_value for a in assets)
    return FDSummary(
        total_accounts=len(assets),
        total_principal=total_principal,
        total_current_value=total_value,
        total_interest_earned=max(0.0, total_value - total_principal),
    )


@router.post("/", response_model=FDAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_fd(
    data: FDAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new fixed deposit."""
    resolved_portfolio_id = portfolio_id or data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    asset = Asset(
        user_id=current_user.id,
        portfolio_id=resolved_portfolio_id,
        asset_type=AssetType.FIXED_DEPOSIT,
        name=data.nickname or data.bank_name,
        account_id=data.account_number,
        quantity=1,
        purchase_price=data.principal_amount,
        current_price=data.principal_amount,
        total_invested=data.principal_amount,
        current_value=data.principal_amount,
        profit_loss=0.0,
        purchase_date=datetime.combine(data.start_date, datetime.min.time()),
        notes=data.notes,
        details={
            "bank_name": data.bank_name,
            "principal_amount": data.principal_amount,
            "interest_rate": data.interest_rate,
            "interest_type": data.interest_type,
            "compounding_frequency": data.compounding_frequency,
            "start_date": data.start_date.strftime("%Y-%m-%d"),
            "maturity_date": data.maturity_date.strftime("%Y-%m-%d") if data.maturity_date else None,
            "auto_update": data.auto_update,
        },
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _asset_to_fd(asset)


@router.get("/{fd_id}", response_model=FDAccountWithTransactions)
async def get_fd(
    fd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a fixed deposit with all its interest transactions."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
        )
        .order_by(Transaction.transaction_date.desc())
        .all()
    )
    fd_data = _asset_to_fd(asset)
    return FDAccountWithTransactions(
        **fd_data.dict(),
        transactions=[_tx_to_fd(t) for t in txs],
        transaction_count=len(txs),
    )


@router.put("/{fd_id}", response_model=FDAccountResponse)
async def update_fd(
    fd_id: int,
    data: FDAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a fixed deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    upd = data.dict(exclude_unset=True)
    d = dict(asset.details or {})

    if "bank_name" in upd:
        d["bank_name"] = upd["bank_name"]
    if "nickname" in upd:
        asset.name = upd["nickname"] or d.get("bank_name", asset.name)
    if "account_number" in upd:
        asset.account_id = upd["account_number"]
    if "principal_amount" in upd:
        d["principal_amount"] = upd["principal_amount"]
        asset.total_invested = upd["principal_amount"]
    if "interest_rate" in upd:
        d["interest_rate"] = upd["interest_rate"]
    if "interest_type" in upd:
        d["interest_type"] = upd["interest_type"]
    if "compounding_frequency" in upd:
        d["compounding_frequency"] = upd["compounding_frequency"]
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
    _recalc_fd_value(asset, db)
    db.commit()
    db.refresh(asset)
    return _asset_to_fd(asset)


@router.delete("/{fd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fd(
    fd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a fixed deposit and all its transactions."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    # Clear FK references that lack ON DELETE CASCADE/SET NULL in the DB
    db.query(Alert).filter(Alert.asset_id == asset.id).update(
        {Alert.asset_id: None}, synchronize_session=False
    )
    db.query(AssetSnapshot).filter(AssetSnapshot.asset_id == asset.id).update(
        {AssetSnapshot.asset_id: None}, synchronize_session=False
    )
    db.query(MutualFundHolding).filter(MutualFundHolding.asset_id == asset.id).delete(
        synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.asset_id == asset.id).delete(
        synchronize_session=False
    )

    db.delete(asset)
    db.commit()


@router.post("/{fd_id}/generate-interest", response_model=FDGenerateInterestResponse)
async def generate_fd_interest(
    fd_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate outstanding interest transactions for a fixed deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    d = asset.details or {}
    principal = d.get("principal_amount", asset.total_invested)
    rate = d.get("interest_rate", 0.0)
    interest_type = d.get("interest_type", "simple")
    freq = d.get("compounding_frequency", "annually")
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
    freq_months = FREQ_MONTHS.get(freq, 12)
    periods_per_year = PERIODS_PER_YEAR.get(freq, 1)

    # Find the last auto-generated interest transaction
    last_auto = (
        db.query(Transaction)
        .filter(
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
            Transaction.reference_number == "AUTO_GENERATED",
        )
        .order_by(Transaction.transaction_date.desc())
        .first()
    )

    next_date = (
        _add_months(last_auto.transaction_date.date(), freq_months)
        if last_auto
        else _add_months(start_date, freq_months)
    )

    if next_date > end_date:
        _recalc_fd_value(asset, db)
        db.commit()
        return FDGenerateInterestResponse(
            transactions_created=0,
            new_current_value=asset.current_value,
            total_interest_earned=max(0.0, asset.current_value - principal),
        )

    # Determine starting balance for compound interest
    if interest_type == "compound":
        existing_interest = (
            db.query(Transaction)
            .filter(
                Transaction.asset_id == asset.id,
                Transaction.transaction_type == TransactionType.INTEREST,
            )
            .all()
        )
        balance = principal + sum(t.total_amount for t in existing_interest)
    else:
        balance = principal

    created = 0
    current_date = next_date
    while current_date <= end_date:
        interest_amount = round(balance * (rate / periods_per_year / 100), 2)
        if interest_amount <= 0:
            break

        tx = Transaction(
            asset_id=asset.id,
            transaction_type=TransactionType.INTEREST,
            transaction_date=datetime.combine(current_date, datetime.min.time()),
            quantity=1,
            price_per_unit=interest_amount,
            total_amount=interest_amount,
            fees=0.0,
            taxes=0.0,
            description=f"Interest ({freq.replace('_', ' ')})",
            reference_number="AUTO_GENERATED",
        )
        db.add(tx)

        if interest_type == "compound":
            balance += interest_amount

        current_date = _add_months(current_date, freq_months)
        created += 1

    db.flush()
    _recalc_fd_value(asset, db)
    db.commit()
    return FDGenerateInterestResponse(
        transactions_created=created,
        new_current_value=asset.current_value,
        total_interest_earned=max(0.0, asset.current_value - principal),
    )


@router.post(
    "/{fd_id}/transactions",
    response_model=FDTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_fd_transaction(
    fd_id: int,
    data: FDTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a manual interest transaction to a fixed deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    tx = Transaction(
        asset_id=asset.id,
        transaction_type=TransactionType.INTEREST,
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
    _recalc_fd_value(asset, db)
    db.commit()
    db.refresh(tx)
    return _tx_to_fd(tx)


@router.put("/{fd_id}/transactions/{tx_id}", response_model=FDTransactionResponse)
async def update_fd_transaction(
    fd_id: int,
    tx_id: int,
    data: FDTransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an interest transaction on a fixed deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == tx_id,
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
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

    _recalc_fd_value(asset, db)
    db.commit()
    db.refresh(tx)
    return _tx_to_fd(tx)


@router.delete("/{fd_id}/transactions/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fd_transaction(
    fd_id: int,
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an interest transaction from a fixed deposit."""
    asset = (
        db.query(Asset)
        .filter(
            Asset.id == fd_id,
            Asset.user_id == current_user.id,
            Asset.asset_type == AssetType.FIXED_DEPOSIT,
        )
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed deposit not found")

    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == tx_id,
            Transaction.asset_id == asset.id,
            Transaction.transaction_type == TransactionType.INTEREST,
        )
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(tx)
    _recalc_fd_value(asset, db)
    db.commit()

# Made with Bob
