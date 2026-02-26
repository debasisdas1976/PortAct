"""
NPS (National Pension System) Account API Endpoints
"""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.dependencies import get_current_active_user, get_db, get_default_portfolio_id
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.schemas.nps import (
    NPSAccountCreate,
    NPSAccountUpdate,
    NPSAccountResponse,
    NPSAccountWithTransactions,
    NPSTransaction,
    NPSTransactionCreate,
    NPSStatementUpload,
    NPSSummary,
)
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.services.nps_parser import NPSStatementParser

router = APIRouter()


@router.get("/", response_model=List[NPSAccountResponse])
async def get_all_nps_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all NPS accounts for the current user
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    nps_accounts = []
    for asset in assets:
        nps_account = NPSAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"NPS - {asset.account_id}",
            pran_number=asset.account_id or asset.details.get('pran_number', ''),
            account_holder_name=asset.account_holder_name or '',
            sector_type=asset.details.get('sector_type', 'all_citizen'),
            tier_type=asset.details.get('tier_type', 'tier_1'),
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            date_of_birth=datetime.strptime(asset.details.get('date_of_birth'), '%Y-%m-%d').date() if asset.details.get('date_of_birth') else date.today(),
            retirement_age=asset.details.get('retirement_age', 60),
            current_balance=asset.current_value,
            total_contributions=asset.total_invested,
            employer_contributions=asset.details.get('employer_contributions', 0),
            total_returns=asset.profit_loss,
            scheme_preference=asset.details.get('scheme_preference'),
            fund_manager=asset.broker_name,
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        nps_accounts.append(nps_account)
    
    return nps_accounts


@router.get("/summary", response_model=NPSSummary)
async def get_nps_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all NPS accounts
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    total_accounts = len(assets)
    total_balance = sum(asset.current_value for asset in assets)
    total_contributions = sum(asset.total_invested for asset in assets)
    employer_contributions = sum(asset.details.get('employer_contributions', 0) for asset in assets)
    total_returns = sum(asset.profit_loss for asset in assets)
    
    # Calculate tier balances
    tier_1_balance = sum(asset.current_value for asset in assets if asset.details.get('tier_type') == 'tier_1')
    tier_2_balance = sum(asset.current_value for asset in assets if asset.details.get('tier_type') == 'tier_2')
    
    return NPSSummary(
        total_accounts=total_accounts,
        total_balance=total_balance,
        total_contributions=total_contributions,
        employer_contributions=employer_contributions,
        total_returns=total_returns,
        tier_1_balance=tier_1_balance,
        tier_2_balance=tier_2_balance
    )


@router.get("/{account_id}", response_model=NPSAccountWithTransactions)
async def get_nps_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific NPS account with its transactions
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="NPS account not found")
    
    # Get transactions
    transactions = db.query(Transaction).filter(
        Transaction.asset_id == asset.id
    ).order_by(Transaction.transaction_date.desc()).all()
    
    nps_transactions = []
    for trans in transactions:
        # Map generic TransactionType enum to NPS-specific display types
        if trans.transaction_type in (TransactionType.BUY, TransactionType.DEPOSIT):
            nps_type = 'contribution'
        elif trans.transaction_type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
            nps_type = 'returns'
        elif trans.transaction_type in (TransactionType.SELL, TransactionType.WITHDRAWAL):
            nps_type = 'withdrawal'
        else:
            nps_type = 'contribution'
        
        nps_trans = NPSTransaction(
            id=trans.id,
            asset_id=trans.asset_id,
            transaction_date=trans.transaction_date.date() if trans.transaction_date else date.today(),
            transaction_type=nps_type,
            amount=abs(trans.total_amount),
            nav=trans.price_per_unit if trans.price_per_unit else None,
            units=trans.quantity if trans.quantity else None,
            scheme=trans.details.get('scheme') if trans.details else None,
            description=trans.description or '',
            financial_year=trans.reference_number,
            created_at=trans.created_at
        )
        nps_transactions.append(nps_trans)
    
    nps_account = NPSAccountWithTransactions(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"NPS - {asset.account_id}",
        pran_number=asset.account_id or "",
        account_holder_name=asset.account_holder_name or "",
        sector_type=asset.details.get('sector_type', 'all_citizen'),
        tier_type=asset.details.get('tier_type', 'tier_1'),
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        date_of_birth=datetime.strptime(asset.details.get('date_of_birth'), '%Y-%m-%d').date() if asset.details.get('date_of_birth') else date.today(),
        retirement_age=asset.details.get('retirement_age', 60),
        current_balance=asset.current_value,
        total_contributions=asset.total_invested,
        employer_contributions=asset.details.get('employer_contributions', 0),
        total_returns=asset.profit_loss,
        scheme_preference=asset.details.get('scheme_preference'),
        fund_manager=asset.broker_name,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
        transactions=nps_transactions,
        transaction_count=len(nps_transactions)
    )
    
    return nps_account


@router.post("/", response_model=NPSAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_nps_account(
    nps_data: NPSAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new NPS account manually
    """
    # Resolve portfolio: parameter > schema > user default
    resolved_portfolio_id = portfolio_id or nps_data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    # Create asset
    asset = Asset(
        user_id=current_user.id,
        asset_type=AssetType.NPS,
        name=nps_data.nickname,
        broker_name=nps_data.fund_manager,
        account_id=nps_data.pran_number,
        account_holder_name=nps_data.account_holder_name,
        purchase_date=datetime.combine(nps_data.opening_date, datetime.min.time()),
        quantity=1,
        purchase_price=nps_data.current_balance,
        current_price=nps_data.current_balance,
        current_value=nps_data.current_balance,
        total_invested=nps_data.total_contributions,
        profit_loss=nps_data.total_returns,
        notes=nps_data.notes,
        portfolio_id=resolved_portfolio_id,
        details={
            'date_of_birth': nps_data.date_of_birth.strftime('%Y-%m-%d'),
            'sector_type': nps_data.sector_type,
            'tier_type': nps_data.tier_type,
            'retirement_age': nps_data.retirement_age,
            'employer_contributions': nps_data.employer_contributions,
            'scheme_preference': nps_data.scheme_preference,
        }
    )
    
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return NPSAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        pran_number=asset.account_id or "",
        account_holder_name=asset.account_holder_name or "",
        sector_type=nps_data.sector_type,
        tier_type=nps_data.tier_type,
        opening_date=nps_data.opening_date,
        date_of_birth=nps_data.date_of_birth,
        retirement_age=nps_data.retirement_age,
        current_balance=asset.current_value,
        total_contributions=asset.total_invested,
        employer_contributions=nps_data.employer_contributions,
        total_returns=asset.profit_loss,
        scheme_preference=nps_data.scheme_preference,
        fund_manager=asset.broker_name,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.put("/{account_id}", response_model=NPSAccountResponse)
async def update_nps_account(
    account_id: int,
    nps_data: NPSAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing NPS account
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="NPS account not found")
    
    # Update fields
    update_data = nps_data.dict(exclude_unset=True)
    
    if 'nickname' in update_data:
        asset.name = update_data['nickname']
    if 'fund_manager' in update_data:
        asset.broker_name = update_data['fund_manager']
    if 'sector_type' in update_data:
        asset.details['sector_type'] = update_data['sector_type']
    if 'tier_type' in update_data:
        asset.details['tier_type'] = update_data['tier_type']
    if 'retirement_age' in update_data:
        asset.details['retirement_age'] = update_data['retirement_age']
    if 'current_balance' in update_data:
        asset.current_value = update_data['current_balance']
        asset.current_price = update_data['current_balance']
    if 'total_contributions' in update_data:
        asset.total_invested = update_data['total_contributions']
    if 'employer_contributions' in update_data:
        asset.details['employer_contributions'] = update_data['employer_contributions']
    if 'total_returns' in update_data:
        asset.profit_loss = update_data['total_returns']
    if 'scheme_preference' in update_data:
        asset.details['scheme_preference'] = update_data['scheme_preference']
    if 'notes' in update_data:
        asset.notes = update_data['notes']
    
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(asset)
    
    return NPSAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"NPS - {asset.account_id}",
        pran_number=asset.account_id or "",
        account_holder_name=asset.account_holder_name or "",
        sector_type=asset.details.get('sector_type', 'all_citizen'),
        tier_type=asset.details.get('tier_type', 'tier_1'),
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        date_of_birth=datetime.strptime(asset.details.get('date_of_birth'), '%Y-%m-%d').date() if asset.details.get('date_of_birth') else date.today(),
        retirement_age=asset.details.get('retirement_age', 60),
        current_balance=asset.current_value,
        total_contributions=asset.total_invested,
        employer_contributions=asset.details.get('employer_contributions', 0),
        total_returns=asset.profit_loss,
        scheme_preference=asset.details.get('scheme_preference'),
        fund_manager=asset.broker_name,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nps_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an NPS account and all its transactions
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="NPS account not found")

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

    return None


@router.post("/{account_id}/transactions", response_model=NPSTransaction, status_code=status.HTTP_201_CREATED)
async def add_nps_transaction(
    account_id: int,
    transaction_data: NPSTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a transaction to an NPS account
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="NPS account not found")
    
    # Map NPS transaction type to Transaction type
    trans_type_map = {
        'contribution': TransactionType.BUY,
        'employer_contribution': TransactionType.BUY,
        'returns': TransactionType.DIVIDEND,
        'withdrawal': TransactionType.SELL,
        'switch': TransactionType.BUY
    }
    
    trans_type = trans_type_map.get(transaction_data.transaction_type, TransactionType.BUY)
    
    # Check for duplicate
    existing = db.query(Transaction).filter(
        Transaction.asset_id == asset.id,
        Transaction.transaction_date == datetime.combine(transaction_data.transaction_date, datetime.min.time()),
        Transaction.transaction_type == trans_type,
        Transaction.total_amount == transaction_data.amount
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate transaction detected")
    
    # Create transaction
    transaction = Transaction(
        asset_id=asset.id,
        transaction_type=trans_type,
        transaction_date=datetime.combine(transaction_data.transaction_date, datetime.min.time()),
        quantity=transaction_data.units if transaction_data.units else 1,
        price_per_unit=transaction_data.nav if transaction_data.nav else transaction_data.amount,
        total_amount=transaction_data.amount,
        fees=0,
        taxes=0,
        description=transaction_data.description,
        reference_number=transaction_data.financial_year,
        details={'scheme': transaction_data.scheme} if transaction_data.scheme else {}
    )
    
    db.add(transaction)
    
    # Update asset balances
    if transaction_data.transaction_type in ['contribution', 'employer_contribution']:
        asset.total_invested += transaction_data.amount
        if transaction_data.transaction_type == 'employer_contribution':
            current_employer = asset.details.get('employer_contributions', 0)
            asset.details['employer_contributions'] = current_employer + transaction_data.amount
    elif transaction_data.transaction_type == 'returns':
        asset.profit_loss += transaction_data.amount
    
    asset.current_value += transaction_data.amount
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(transaction)
    
    return NPSTransaction(
        id=transaction.id,
        asset_id=transaction.asset_id,
        transaction_date=transaction.transaction_date.date(),
        transaction_type=transaction_data.transaction_type,
        amount=transaction_data.amount,
        nav=transaction_data.nav,
        units=transaction_data.units,
        scheme=transaction_data.scheme,
        description=transaction_data.description,
        financial_year=transaction_data.financial_year,
        created_at=transaction.created_at
    )


@router.post("/upload", response_model=NPSAccountResponse, status_code=status.HTTP_201_CREATED)
async def upload_nps_statement_auto(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    portfolio_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse an NPS statement PDF, auto-creating an account if needed
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        content = await file.read()
        parser = NPSStatementParser(content, password)
        account_data, transactions = parser.parse()

        # Resolve portfolio
        resolved_portfolio_id = portfolio_id or get_default_portfolio_id(current_user.id, db)

        # Check if account already exists by PRAN number
        existing_asset = None
        pran = (account_data.get('pran_number') or account_data.get('account_number') or '').strip()
        if pran:
            existing_asset = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.NPS,
                Asset.account_id == pran
            ).first()

        if existing_asset:
            asset = existing_asset
            # Update with parsed data
            if account_data.get('current_balance'):
                asset.current_value = account_data['current_balance']
                asset.current_price = account_data['current_balance']
            if account_data.get('total_contributions'):
                asset.total_invested = account_data['total_contributions']
            if account_data.get('total_returns'):
                asset.profit_loss = account_data['total_returns']
            if account_data.get('employer_contributions'):
                asset.details['employer_contributions'] = account_data['employer_contributions']
            asset.last_updated = datetime.utcnow()
        else:
            # Create new NPS asset
            holder_name = (account_data.get('account_holder_name') or
                          account_data.get('account_holder', 'Unknown'))
            fund_manager = account_data.get('fund_manager', '')
            opening_date_str = account_data.get('opening_date', date.today().strftime('%Y-%m-%d'))
            if isinstance(opening_date_str, str):
                opening_date = datetime.strptime(opening_date_str, '%Y-%m-%d')
            else:
                opening_date = opening_date_str if isinstance(opening_date_str, datetime) else datetime.combine(opening_date_str, datetime.min.time())

            dob_str = account_data.get('date_of_birth', date.today().strftime('%Y-%m-%d'))

            asset = Asset(
                user_id=current_user.id,
                asset_type=AssetType.NPS,
                portfolio_id=resolved_portfolio_id,
                name=f"NPS - {holder_name}",
                broker_name=fund_manager,
                account_id=pran,
                account_holder_name=holder_name,
                purchase_date=opening_date,
                quantity=1,
                purchase_price=account_data.get('current_balance', 0),
                current_price=account_data.get('current_balance', 0),
                current_value=account_data.get('current_balance', 0),
                total_invested=account_data.get('total_contributions', 0),
                profit_loss=account_data.get('total_returns', 0),
                details={
                    'pran_number': pran,
                    'date_of_birth': dob_str if isinstance(dob_str, str) else dob_str.strftime('%Y-%m-%d'),
                    'sector_type': account_data.get('sector_type', 'all_citizen'),
                    'tier_type': account_data.get('tier_type', 'tier_1'),
                    'retirement_age': account_data.get('retirement_age', 60),
                    'employer_contributions': account_data.get('employer_contributions', 0),
                    'scheme_preference': account_data.get('scheme_preference'),
                }
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

        # Add transactions with duplicate detection
        for trans_data in transactions:
            trans_type_map = {
                'contribution': TransactionType.BUY,
                'employer_contribution': TransactionType.BUY,
                'returns': TransactionType.DIVIDEND,
                'withdrawal': TransactionType.SELL,
                'switch': TransactionType.BUY
            }

            trans_type = trans_type_map.get(trans_data.get('transaction_type', 'contribution'), TransactionType.BUY)
            trans_date = datetime.strptime(trans_data['transaction_date'], '%Y-%m-%d')

            existing = db.query(Transaction).filter(
                Transaction.asset_id == asset.id,
                Transaction.transaction_date == trans_date,
                Transaction.transaction_type == trans_type,
                Transaction.total_amount == trans_data['amount']
            ).first()

            if not existing:
                transaction = Transaction(
                    asset_id=asset.id,
                    transaction_type=trans_type,
                    transaction_date=trans_date,
                    quantity=trans_data.get('units', 1),
                    price_per_unit=trans_data.get('nav', trans_data['amount']),
                    total_amount=trans_data['amount'],
                    fees=0,
                    taxes=0,
                    description=trans_data.get('description'),
                    reference_number=trans_data.get('financial_year'),
                    details={'scheme': trans_data.get('scheme')} if trans_data.get('scheme') else {}
                )
                db.add(transaction)

        db.commit()
        db.refresh(asset)

        return NPSAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"NPS - {asset.account_id}",
            pran_number=asset.account_id or asset.details.get('pran_number', ''),
            account_holder_name=asset.account_holder_name or '',
            sector_type=asset.details.get('sector_type', 'all_citizen'),
            tier_type=asset.details.get('tier_type', 'tier_1'),
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            date_of_birth=datetime.strptime(asset.details.get('date_of_birth'), '%Y-%m-%d').date() if asset.details.get('date_of_birth') else date.today(),
            retirement_age=asset.details.get('retirement_age', 60),
            current_balance=asset.current_value,
            total_contributions=asset.total_invested,
            employer_contributions=asset.details.get('employer_contributions', 0),
            total_returns=asset.profit_loss,
            scheme_preference=asset.details.get('scheme_preference'),
            fund_manager=asset.broker_name,
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not process the NPS statement. Please check the file format.")


@router.post("/{account_id}/upload", response_model=NPSAccountResponse, status_code=status.HTTP_201_CREATED)
async def upload_nps_statement(
    account_id: int,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse an NPS statement PDF for a specific account
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.NPS
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="NPS account not found")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse statement
        parser = NPSStatementParser(content, password)
        account_data, transactions = parser.parse()

        # Validate that the statement matches the selected NPS account
        extracted_holder = (account_data.get('account_holder_name') or
                            account_data.get('account_holder', '')).strip()
        existing_holder = (asset.account_holder_name or '').strip()
        if extracted_holder and existing_holder:
            if extracted_holder.lower() != existing_holder.lower():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Statement mismatch: this statement belongs to '{extracted_holder}', "
                        f"but the selected NPS account is held by '{existing_holder}'. "
                        f"Please use 'Add New Account' if this is a different account."
                    )
                )

        extracted_pran = (account_data.get('pran_number') or
                          account_data.get('account_number') or '').strip()
        existing_acct_id = (asset.account_id or '').strip()
        if extracted_pran and existing_acct_id:
            if extracted_pran != existing_acct_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Statement mismatch: this statement is for PRAN {extracted_pran}, "
                        f"but you selected account {existing_acct_id}. "
                        f"Please use 'Add New Account' if this is a different account."
                    )
                )

        # Update asset with parsed data
        if account_data.get('current_balance'):
            asset.current_value = account_data['current_balance']
            asset.current_price = account_data['current_balance']
        if account_data.get('total_contributions'):
            asset.total_invested = account_data['total_contributions']
        if account_data.get('total_returns'):
            asset.profit_loss = account_data['total_returns']
        if account_data.get('employer_contributions'):
            asset.details['employer_contributions'] = account_data['employer_contributions']
        
        asset.last_updated = datetime.utcnow()
        
        # Add transactions
        for trans_data in transactions:
            trans_type_map = {
                'contribution': TransactionType.BUY,
                'employer_contribution': TransactionType.BUY,
                'returns': TransactionType.DIVIDEND,
                'withdrawal': TransactionType.SELL,
                'switch': TransactionType.BUY
            }
            
            trans_type = trans_type_map.get(trans_data['transaction_type'], TransactionType.BUY)
            trans_date = datetime.strptime(trans_data['transaction_date'], '%Y-%m-%d')
            
            # Check for duplicate
            existing = db.query(Transaction).filter(
                Transaction.asset_id == asset.id,
                Transaction.transaction_date == trans_date,
                Transaction.transaction_type == trans_type,
                Transaction.total_amount == trans_data['amount']
            ).first()
            
            if not existing:
                transaction = Transaction(
                    asset_id=asset.id,
                    transaction_type=trans_type,
                    transaction_date=trans_date,
                    quantity=trans_data.get('units', 1),
                    price_per_unit=trans_data.get('nav', trans_data['amount']),
                    total_amount=trans_data['amount'],
                    fees=0,
                    taxes=0,
                    description=trans_data.get('description'),
                    reference_number=trans_data.get('financial_year'),
                    details={'scheme': trans_data.get('scheme')} if trans_data.get('scheme') else {}
                )
                db.add(transaction)
        
        db.commit()
        db.refresh(asset)
        
        return NPSAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"NPS - {asset.account_id}",
            pran_number=asset.account_id or asset.details.get('pran_number', ''),
            account_holder_name=asset.account_holder_name or '',
            sector_type=asset.details.get('sector_type', 'all_citizen'),
            tier_type=asset.details.get('tier_type', 'tier_1'),
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            date_of_birth=datetime.strptime(asset.details.get('date_of_birth'), '%Y-%m-%d').date() if asset.details.get('date_of_birth') else date.today(),
            retirement_age=asset.details.get('retirement_age', 60),
            current_balance=asset.current_value,
            total_contributions=asset.total_invested,
            employer_contributions=asset.details.get('employer_contributions', 0),
            total_returns=asset.profit_loss,
            scheme_preference=asset.details.get('scheme_preference'),
            fund_manager=asset.broker_name,
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not process the NPS statement. Please check the file format.")

# Made with Bob