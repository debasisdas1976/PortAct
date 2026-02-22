"""
SSY (Sukanya Samriddhi Yojana) Account API Endpoints
"""
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.schemas.ssy import (
    SSYAccountCreate,
    SSYAccountUpdate,
    SSYAccountResponse,
    SSYAccountWithTransactions,
    SSYTransaction,
    SSYTransactionCreate,
    SSYStatementUpload,
    SSYSummary,
)
from app.services.ssy_parser import SSYStatementParser

router = APIRouter()


@router.get("/", response_model=List[SSYAccountResponse])
async def get_all_ssy_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all SSY accounts for the current user
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    ssy_accounts = []
    for asset in assets:
        ssy_account = SSYAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"SSY - {asset.broker_name}",
            account_number=asset.account_id or asset.details.get('account_number', ''),
            bank_name=asset.broker_name or asset.details.get('post_office', ''),
            post_office_name=asset.details.get('post_office_name') or asset.details.get('post_office'),
            girl_name=asset.account_holder_name or asset.details.get('beneficiary_name', ''),
            girl_dob=datetime.strptime(asset.details.get('girl_dob') or asset.details.get('beneficiary_dob', ''), '%Y-%m-%d').date() if (asset.details.get('girl_dob') or asset.details.get('beneficiary_dob')) else date.today(),
            guardian_name=asset.details.get('guardian_name', ''),
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            maturity_date=asset.details.get('maturity_date'),
            interest_rate=asset.details.get('interest_rate', 8.2),
            current_balance=asset.current_value,
            total_deposits=asset.total_invested,
            total_interest_earned=asset.profit_loss,
            financial_year=asset.details.get('financial_year'),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        ssy_accounts.append(ssy_account)
    
    return ssy_accounts


@router.get("/summary", response_model=SSYSummary)
async def get_ssy_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for all SSY accounts
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    total_accounts = len(assets)
    total_balance = sum(asset.current_value for asset in assets)
    total_deposits = sum(asset.total_invested for asset in assets)
    total_interest = sum(asset.profit_loss for asset in assets)
    
    # Calculate average interest rate
    interest_rates = [asset.details.get('interest_rate', 8.2) for asset in assets if asset.details.get('interest_rate')]
    avg_interest_rate = sum(interest_rates) / len(interest_rates) if interest_rates else 8.2
    
    return SSYSummary(
        total_accounts=total_accounts,
        total_balance=total_balance,
        total_deposits=total_deposits,
        total_interest_earned=total_interest,
        average_interest_rate=avg_interest_rate
    )


@router.get("/{account_id}", response_model=SSYAccountWithTransactions)
async def get_ssy_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific SSY account with its transactions
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="SSY account not found")
    
    # Get transactions
    transactions = db.query(Transaction).filter(
        Transaction.asset_id == asset.id
    ).order_by(Transaction.transaction_date.desc()).all()
    
    ssy_transactions = []
    for trans in transactions:
        # Map transaction types
        trans_type_value = trans.transaction_type.value if hasattr(trans.transaction_type, 'value') else str(trans.transaction_type)
        if trans_type_value in ['buy', 'deposit']:
            ssy_type = 'deposit'
        elif trans_type_value in ['dividend', 'interest']:
            ssy_type = 'interest'
        elif trans_type_value in ['sell', 'withdrawal']:
            ssy_type = 'withdrawal'
        elif trans_type_value == 'maturity':
            ssy_type = 'maturity'
        else:
            ssy_type = 'deposit'
        
        ssy_trans = SSYTransaction(
            id=trans.id,
            asset_id=trans.asset_id,
            transaction_date=trans.transaction_date.date() if trans.transaction_date else date.today(),
            transaction_type=ssy_type,
            amount=abs(trans.total_amount),
            balance_after_transaction=0.0,
            description=trans.description or '',
            financial_year=trans.reference_number,
            created_at=trans.created_at
        )
        ssy_transactions.append(ssy_trans)
    
    ssy_account = SSYAccountWithTransactions(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"SSY - {asset.broker_name}",
        account_number=asset.account_id or "",
        bank_name=asset.broker_name or "",
        post_office_name=asset.details.get('post_office_name'),
        girl_name=asset.account_holder_name or "",
        girl_dob=datetime.strptime(asset.details.get('girl_dob'), '%Y-%m-%d').date() if asset.details.get('girl_dob') else date.today(),
        guardian_name=asset.details.get('guardian_name', ''),
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        maturity_date=asset.details.get('maturity_date'),
        interest_rate=asset.details.get('interest_rate', 8.2),
        current_balance=asset.current_value,
        total_deposits=asset.total_invested,
        total_interest_earned=asset.profit_loss,
        financial_year=asset.details.get('financial_year'),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
        transactions=ssy_transactions,
        transaction_count=len(ssy_transactions)
    )
    
    return ssy_account


@router.post("/", response_model=SSYAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_ssy_account(
    ssy_data: SSYAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new SSY account manually
    """
    # Calculate maturity date (21 years from opening or marriage after 18)
    maturity_date = ssy_data.maturity_date
    if not maturity_date and ssy_data.opening_date:
        from dateutil.relativedelta import relativedelta
        maturity_date = ssy_data.opening_date + relativedelta(years=21)
    
    # Resolve portfolio: parameter > schema > user default
    from app.api.dependencies import get_default_portfolio_id
    resolved_portfolio_id = portfolio_id or ssy_data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    # Create asset
    asset = Asset(
        user_id=current_user.id,
        asset_type=AssetType.SSY,
        name=ssy_data.nickname,
        broker_name=ssy_data.bank_name,
        account_id=ssy_data.account_number,
        account_holder_name=ssy_data.girl_name,
        purchase_date=datetime.combine(ssy_data.opening_date, datetime.min.time()),
        quantity=1,
        purchase_price=ssy_data.current_balance,
        current_price=ssy_data.current_balance,
        current_value=ssy_data.current_balance,
        total_invested=ssy_data.total_deposits,
        profit_loss=ssy_data.total_interest_earned,
        notes=ssy_data.notes,
        portfolio_id=resolved_portfolio_id,
        details={
            'girl_dob': ssy_data.girl_dob.strftime('%Y-%m-%d'),
            'guardian_name': ssy_data.guardian_name,
            'post_office_name': ssy_data.post_office_name,
            'maturity_date': maturity_date.strftime('%Y-%m-%d') if maturity_date else None,
            'interest_rate': ssy_data.interest_rate,
            'financial_year': ssy_data.financial_year,
        }
    )
    
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return SSYAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        account_number=asset.account_id or "",
        bank_name=asset.broker_name or "",
        post_office_name=ssy_data.post_office_name,
        girl_name=asset.account_holder_name or "",
        girl_dob=ssy_data.girl_dob,
        guardian_name=ssy_data.guardian_name,
        opening_date=ssy_data.opening_date,
        maturity_date=maturity_date,
        interest_rate=ssy_data.interest_rate,
        current_balance=asset.current_value,
        total_deposits=asset.total_invested,
        total_interest_earned=asset.profit_loss,
        financial_year=ssy_data.financial_year,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.put("/{account_id}", response_model=SSYAccountResponse)
async def update_ssy_account(
    account_id: int,
    ssy_data: SSYAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing SSY account
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="SSY account not found")
    
    # Update fields
    update_data = ssy_data.dict(exclude_unset=True)
    
    if 'nickname' in update_data:
        asset.name = update_data['nickname']
    if 'bank_name' in update_data:
        asset.broker_name = update_data['bank_name']
    if 'guardian_name' in update_data:
        asset.details['guardian_name'] = update_data['guardian_name']
    if 'post_office_name' in update_data:
        asset.details['post_office_name'] = update_data['post_office_name']
    if 'interest_rate' in update_data:
        asset.details['interest_rate'] = update_data['interest_rate']
    if 'current_balance' in update_data:
        asset.current_value = update_data['current_balance']
        asset.current_price = update_data['current_balance']
    if 'total_deposits' in update_data:
        asset.total_invested = update_data['total_deposits']
    if 'total_interest_earned' in update_data:
        asset.profit_loss = update_data['total_interest_earned']
    if 'financial_year' in update_data:
        asset.details['financial_year'] = update_data['financial_year']
    if 'notes' in update_data:
        asset.notes = update_data['notes']
    
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(asset)
    
    return SSYAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"SSY - {asset.broker_name}",
        account_number=asset.account_id or "",
        bank_name=asset.broker_name or "",
        post_office_name=asset.details.get('post_office_name'),
        girl_name=asset.account_holder_name or "",
        girl_dob=datetime.strptime(asset.details.get('girl_dob'), '%Y-%m-%d').date() if asset.details.get('girl_dob') else date.today(),
        guardian_name=asset.details.get('guardian_name', ''),
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        maturity_date=asset.details.get('maturity_date'),
        interest_rate=asset.details.get('interest_rate', 8.2),
        current_balance=asset.current_value,
        total_deposits=asset.total_invested,
        total_interest_earned=asset.profit_loss,
        financial_year=asset.details.get('financial_year'),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ssy_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an SSY account and all its transactions
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="SSY account not found")
    
    # Delete associated transactions
    db.query(Transaction).filter(Transaction.asset_id == asset.id).delete()
    
    # Delete asset
    db.delete(asset)
    db.commit()
    
    return None


@router.post("/{account_id}/transactions", response_model=SSYTransaction, status_code=status.HTTP_201_CREATED)
async def add_ssy_transaction(
    account_id: int,
    transaction_data: SSYTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a transaction to an SSY account
    """
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.SSY
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="SSY account not found")
    
    # Map SSY transaction type to Transaction type
    trans_type_map = {
        'deposit': TransactionType.BUY,
        'interest': TransactionType.DIVIDEND,
        'withdrawal': TransactionType.SELL,
        'maturity': TransactionType.SELL
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
        quantity=1,
        price_per_unit=transaction_data.amount,
        total_amount=transaction_data.amount,
        fees=0,
        taxes=0,
        description=transaction_data.description,
        reference_number=transaction_data.financial_year
    )
    
    db.add(transaction)
    
    # Update asset balances
    if transaction_data.transaction_type == 'deposit':
        asset.total_invested += transaction_data.amount
    elif transaction_data.transaction_type == 'interest':
        asset.profit_loss += transaction_data.amount
    
    asset.current_value = transaction_data.balance_after_transaction
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(transaction)
    
    return SSYTransaction(
        id=transaction.id,
        asset_id=transaction.asset_id,
        transaction_date=transaction.transaction_date.date(),
        transaction_type=transaction_data.transaction_type,
        amount=transaction_data.amount,
        balance_after_transaction=transaction_data.balance_after_transaction,
        description=transaction_data.description,
        financial_year=transaction_data.financial_year,
        created_at=transaction.created_at
    )


@router.post("/upload", response_model=SSYAccountResponse, status_code=status.HTTP_201_CREATED)
async def upload_ssy_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse an SSY statement PDF
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Parse statement
        parser = SSYStatementParser(content, password)
        account_data, transactions = parser.parse()
        
        # Check if account already exists
        existing_asset = None
        if account_data.get('account_number'):
            existing_asset = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.SSY,
                Asset.account_id == account_data['account_number']
            ).first()
        
        if existing_asset:
            asset = existing_asset
        else:
            # Create new asset
            opening_date = datetime.strptime(account_data.get('opening_date', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d')
            girl_dob = datetime.strptime(account_data.get('girl_dob', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d')
            
            asset = Asset(
                user_id=current_user.id,
                asset_type=AssetType.SSY,
                name=f"SSY - {account_data.get('girl_name', 'Account')}",
                broker_name=account_data.get('bank_name', ''),
                account_id=account_data.get('account_number', ''),
                account_holder_name=account_data.get('girl_name', ''),
                purchase_date=opening_date,
                quantity=1,
                purchase_price=account_data.get('current_balance', 0),
                current_price=account_data.get('current_balance', 0),
                current_value=account_data.get('current_balance', 0),
                total_invested=account_data.get('total_deposits', 0),
                profit_loss=account_data.get('total_interest_earned', 0),
                details={
                    'girl_dob': girl_dob.strftime('%Y-%m-%d'),
                    'guardian_name': account_data.get('guardian_name', ''),
                    'post_office_name': account_data.get('post_office_name'),
                    'maturity_date': account_data.get('maturity_date'),
                    'interest_rate': account_data.get('interest_rate', 8.2),
                    'financial_year': account_data.get('financial_year'),
                }
            )
            
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        # Add transactions
        for trans_data in transactions:
            trans_type_map = {
                'deposit': TransactionType.BUY,
                'interest': TransactionType.DIVIDEND,
                'withdrawal': TransactionType.SELL,
                'maturity': TransactionType.SELL
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
                    quantity=1,
                    price_per_unit=trans_data['amount'],
                    total_amount=trans_data['amount'],
                    fees=0,
                    taxes=0,
                    description=trans_data.get('description'),
                    reference_number=trans_data.get('financial_year')
                )
                db.add(transaction)
        
        db.commit()
        db.refresh(asset)
        
        return SSYAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"SSY - {asset.broker_name}",
            account_number=asset.account_id or asset.details.get('account_number', ''),
            bank_name=asset.broker_name or asset.details.get('post_office', ''),
            post_office_name=asset.details.get('post_office_name') or asset.details.get('post_office'),
            girl_name=asset.account_holder_name or asset.details.get('beneficiary_name', ''),
            girl_dob=datetime.strptime(asset.details.get('girl_dob') or asset.details.get('beneficiary_dob', ''), '%Y-%m-%d').date() if (asset.details.get('girl_dob') or asset.details.get('beneficiary_dob')) else date.today(),
            guardian_name=asset.details.get('guardian_name', ''),
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            maturity_date=asset.details.get('maturity_date'),
            interest_rate=asset.details.get('interest_rate', 8.2),
            current_balance=asset.current_value,
            total_deposits=asset.total_invested,
            total_interest_earned=asset.profit_loss,
            financial_year=asset.details.get('financial_year'),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not process the SSY statement. Please check the file format.")

# Made with Bob
