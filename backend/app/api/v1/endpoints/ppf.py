from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import os
import shutil
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_default_portfolio_id
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.statement import Statement, StatementType, StatementStatus
from app.schemas.ppf import (
    PPFAccountCreate,
    PPFAccountUpdate,
    PPFAccountResponse,
    PPFAccountWithTransactions,
    PPFSummary,
    PPFTransactionCreate,
    PPFTransaction
)
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.services.ppf_parser import PPFStatementParser
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[PPFAccountResponse])
async def get_ppf_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all PPF accounts for the current user
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    # Calculate current metrics
    for asset in assets:
        asset.calculate_metrics()
    db.commit()

    # Convert to PPF account response format
    ppf_accounts = []
    for asset in assets:
        details = asset.details or {}
        ppf_account = PPFAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"PPF - {asset.broker_name}",
            account_number=asset.account_id or details.get('account_number', ''),
            bank_name=asset.broker_name or details.get('bank', ''),
            account_holder_name=asset.account_holder_name or '',
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            maturity_date=details.get('maturity_date'),
            interest_rate=details.get('interest_rate', 7.1),
            current_balance=asset.current_value,
            total_deposits=asset.total_invested,
            total_interest_earned=details.get('total_interest_earned', 0.0),
            financial_year=details.get('financial_year'),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        ppf_accounts.append(ppf_account)

    return ppf_accounts


@router.get("/summary", response_model=PPFSummary)
async def get_ppf_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get PPF portfolio summary
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF,
        Asset.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    # Calculate metrics
    for asset in assets:
        asset.calculate_metrics()
    db.commit()
    
    total_balance = sum(asset.current_value for asset in assets)
    total_deposits = sum(asset.total_invested for asset in assets)
    total_interest = sum((asset.details or {}).get('total_interest_earned', 0.0) for asset in assets)

    # Calculate average interest rate
    interest_rates = [asset.details.get('interest_rate', 0) for asset in assets if asset.details.get('interest_rate')]
    avg_interest_rate = sum(interest_rates) / len(interest_rates) if interest_rates else 7.1

    # Convert to PPF account responses
    ppf_accounts = []
    for asset in assets:
        details = asset.details or {}
        ppf_account = PPFAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"PPF - {asset.broker_name}",
            account_number=asset.account_id or details.get('account_number', ''),
            bank_name=asset.broker_name or details.get('bank', ''),
            account_holder_name=asset.account_holder_name or '',
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            maturity_date=details.get('maturity_date'),
            interest_rate=details.get('interest_rate', 7.1),
            current_balance=asset.current_value,
            total_deposits=asset.total_invested,
            total_interest_earned=details.get('total_interest_earned', 0.0),
            financial_year=details.get('financial_year'),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        ppf_accounts.append(ppf_account)
    
    return PPFSummary(
        total_accounts=len(assets),
        total_balance=total_balance,
        total_deposits=total_deposits,
        total_interest_earned=total_interest,
        average_interest_rate=avg_interest_rate,
        accounts=ppf_accounts
    )


@router.get("/{ppf_id}", response_model=PPFAccountWithTransactions)
async def get_ppf_account(
    ppf_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific PPF account with transactions
    """
    asset = db.query(Asset).filter(
        Asset.id == ppf_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPF account not found"
        )
    
    asset.calculate_metrics()
    db.commit()
    
    # Get transactions
    transactions = db.query(Transaction).filter(
        Transaction.asset_id == asset.id
    ).order_by(Transaction.transaction_date.desc()).all()
    
    ppf_transactions = []
    for trans in transactions:
        # Map generic TransactionType enum to PPF-specific display types
        if trans.transaction_type in (TransactionType.BUY, TransactionType.DEPOSIT):
            ppf_type = 'deposit'
        elif trans.transaction_type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
            ppf_type = 'interest'
        elif trans.transaction_type in (TransactionType.SELL, TransactionType.WITHDRAWAL):
            ppf_type = 'withdrawal'
        else:
            ppf_type = 'deposit'
        
        ppf_trans = PPFTransaction(
            id=trans.id,
            asset_id=trans.asset_id,
            transaction_date=trans.transaction_date.date() if trans.transaction_date else date.today(),
            transaction_type=ppf_type,
            amount=abs(trans.total_amount),
            balance_after_transaction=0.0,  # Will be calculated from cumulative transactions
            description=trans.description or '',
            financial_year=trans.reference_number,  # We stored FY in reference_number
            created_at=trans.created_at
        )
        ppf_transactions.append(ppf_trans)
    
    details = asset.details or {}
    ppf_account = PPFAccountWithTransactions(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"PPF - {asset.broker_name}",
        account_number=asset.account_id or "",
        bank_name=asset.broker_name or "",
        account_holder_name=asset.account_holder_name or "",
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        maturity_date=details.get('maturity_date'),
        interest_rate=details.get('interest_rate', 7.1),
        current_balance=asset.current_value,
        total_deposits=asset.total_invested,
        total_interest_earned=details.get('total_interest_earned', 0.0),
        financial_year=details.get('financial_year'),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
        transactions=ppf_transactions,
        transaction_count=len(ppf_transactions)
    )
    
    return ppf_account


@router.post("/", response_model=PPFAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_ppf_account(
    ppf_data: PPFAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new PPF account manually
    """
    # Calculate maturity date (15 years from opening)
    maturity_date = ppf_data.maturity_date
    if not maturity_date and ppf_data.opening_date:
        from dateutil.relativedelta import relativedelta
        maturity_date = ppf_data.opening_date + relativedelta(years=15)
    
    # Resolve portfolio: parameter > schema > user default
    resolved_portfolio_id = portfolio_id or ppf_data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    # Create asset record
    new_asset = Asset(
        user_id=current_user.id,
        asset_type=AssetType.PPF,
        name=ppf_data.nickname,  # Use nickname as the asset name
        symbol="PPF",
        account_id=ppf_data.account_number,
        broker_name=ppf_data.bank_name,
        account_holder_name=ppf_data.account_holder_name,
        quantity=1.0,  # PPF is account-based, not unit-based
        purchase_price=ppf_data.current_balance,
        current_price=ppf_data.current_balance,
        total_invested=ppf_data.total_deposits,
        current_value=ppf_data.current_balance,
        purchase_date=datetime.combine(ppf_data.opening_date, datetime.min.time()),
        portfolio_id=resolved_portfolio_id,
        details={
            'maturity_date': maturity_date.isoformat() if maturity_date else None,
            'interest_rate': ppf_data.interest_rate,
            'total_interest_earned': ppf_data.total_interest_earned,
            'financial_year': ppf_data.financial_year,
            'account_type': 'PPF'
        },
        notes=ppf_data.notes,
        is_active=True
    )
    
    new_asset.calculate_metrics()
    
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    return PPFAccountResponse(
        id=new_asset.id,
        user_id=new_asset.user_id,
        asset_id=new_asset.id,
        nickname=ppf_data.nickname,
        account_number=ppf_data.account_number,
        bank_name=ppf_data.bank_name,
        account_holder_name=ppf_data.account_holder_name,
        opening_date=ppf_data.opening_date,
        maturity_date=maturity_date,
        interest_rate=ppf_data.interest_rate,
        current_balance=ppf_data.current_balance,
        total_deposits=ppf_data.total_deposits,
        total_interest_earned=ppf_data.total_interest_earned,
        financial_year=ppf_data.financial_year,
        notes=ppf_data.notes,
        created_at=new_asset.created_at,
        updated_at=new_asset.last_updated
    )


@router.put("/{ppf_id}", response_model=PPFAccountResponse)
async def update_ppf_account(
    ppf_id: int,
    ppf_update: PPFAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing PPF account
    """
    asset = db.query(Asset).filter(
        Asset.id == ppf_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPF account not found"
        )
    
    # Update fields
    update_data = ppf_update.model_dump(exclude_unset=True)
    
    if 'nickname' in update_data:
        asset.name = update_data['nickname']
    if 'account_number' in update_data:
        asset.account_id = update_data['account_number']
    if 'bank_name' in update_data:
        asset.broker_name = update_data['bank_name']
    if 'account_holder_name' in update_data:
        asset.account_holder_name = update_data['account_holder_name']
    if 'opening_date' in update_data:
        asset.purchase_date = datetime.combine(update_data['opening_date'], datetime.min.time())
    if 'current_balance' in update_data:
        asset.current_value = update_data['current_balance']
        asset.current_price = update_data['current_balance']
    if 'total_deposits' in update_data:
        asset.total_invested = update_data['total_deposits']
    if 'notes' in update_data:
        asset.notes = update_data['notes']
    
    # Update details JSON
    if not asset.details:
        asset.details = {}
    
    if 'maturity_date' in update_data:
        asset.details['maturity_date'] = update_data['maturity_date'].isoformat() if update_data['maturity_date'] else None
    if 'interest_rate' in update_data:
        asset.details['interest_rate'] = update_data['interest_rate']
    if 'total_interest_earned' in update_data:
        asset.details['total_interest_earned'] = update_data['total_interest_earned']
    if 'financial_year' in update_data:
        asset.details['financial_year'] = update_data['financial_year']
    
    asset.calculate_metrics()
    
    db.commit()
    db.refresh(asset)
    
    details = asset.details or {}
    return PPFAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"PPF - {asset.broker_name}",
        account_number=asset.account_id or "",
        bank_name=asset.broker_name or "",
        account_holder_name=asset.account_holder_name or "",
        opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
        maturity_date=details.get('maturity_date'),
        interest_rate=details.get('interest_rate', 7.1),
        current_balance=asset.current_value,
        total_deposits=asset.total_invested,
        total_interest_earned=details.get('total_interest_earned', 0.0),
        financial_year=details.get('financial_year'),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.delete("/{ppf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ppf_account(
    ppf_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a PPF account
    """
    asset = db.query(Asset).filter(
        Asset.id == ppf_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPF account not found"
        )

    # Clear FK references that lack ON DELETE CASCADE/SET NULL in the DB
    db.query(Alert).filter(Alert.asset_id == ppf_id).update(
        {Alert.asset_id: None}, synchronize_session=False
    )
    db.query(AssetSnapshot).filter(AssetSnapshot.asset_id == ppf_id).update(
        {AssetSnapshot.asset_id: None}, synchronize_session=False
    )
    db.query(MutualFundHolding).filter(MutualFundHolding.asset_id == ppf_id).delete(
        synchronize_session=False
    )
    db.query(Transaction).filter(Transaction.asset_id == ppf_id).delete(
        synchronize_session=False
    )

    db.delete(asset)
    db.commit()

    return None


@router.post("/upload", response_model=PPFAccountResponse, status_code=status.HTTP_201_CREATED)
async def upload_ppf_statement_auto(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    portfolio_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a PPF statement PDF, auto-creating an account if needed
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    try:
        # Save file to temp location (PPF parser requires file path)
        upload_dir = f"backend/uploads/{current_user.id}"
        os.makedirs(upload_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        parser = PPFStatementParser()
        parsed_data = parser.parse_statement(file_path, password)

        account_details = parsed_data.get('account_details', {})

        # Resolve portfolio
        resolved_portfolio_id = portfolio_id or get_default_portfolio_id(current_user.id, db)

        # Check if account already exists by account number
        existing_asset = None
        acct_num = account_details.get('account_number', '').strip()
        if acct_num:
            existing_asset = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.PPF,
                Asset.account_id == acct_num
            ).first()

        if existing_asset:
            asset = existing_asset
            # Update with parsed data
            if account_details.get('current_balance'):
                asset.current_value = account_details['current_balance']
                asset.current_price = account_details['current_balance']
            if account_details.get('total_deposits'):
                asset.total_invested = account_details['total_deposits']
            if account_details.get('interest_rate'):
                if not asset.details:
                    asset.details = {}
                asset.details['interest_rate'] = account_details['interest_rate']
            if account_details.get('total_interest_earned'):
                if not asset.details:
                    asset.details = {}
                asset.details['total_interest_earned'] = account_details['total_interest_earned']
        else:
            # Create new PPF asset
            opening_date_str = account_details.get('opening_date', date.today().strftime('%Y-%m-%d'))
            opening_date = datetime.strptime(opening_date_str, '%Y-%m-%d') if isinstance(opening_date_str, str) else opening_date_str

            holder_name = (account_details.get('account_holder_name') or
                          account_details.get('account_holder', 'Unknown'))
            bank_name = account_details.get('bank_name') or account_details.get('bank', '')

            asset = Asset(
                user_id=current_user.id,
                asset_type=AssetType.PPF,
                portfolio_id=resolved_portfolio_id,
                name=f"PPF - {bank_name or 'Account'}",
                broker_name=bank_name,
                account_id=acct_num,
                account_holder_name=holder_name,
                purchase_date=opening_date,
                quantity=1,
                purchase_price=account_details.get('current_balance', 0),
                current_price=account_details.get('current_balance', 0),
                current_value=account_details.get('current_balance', 0),
                total_invested=account_details.get('total_deposits', 0),
                profit_loss=account_details.get('total_interest_earned', 0),
                details={
                    'interest_rate': account_details.get('interest_rate', 7.1),
                    'total_interest_earned': account_details.get('total_interest_earned', 0),
                    'financial_year': account_details.get('financial_year'),
                    'account_type': 'PPF',
                },
                is_active=True
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)

        # Add transactions with duplicate detection
        for trans_data in parsed_data.get('transactions', []):
            trans_date = trans_data.get('transaction_date')
            if trans_date:
                if isinstance(trans_date, str):
                    trans_date = datetime.strptime(trans_date, '%Y-%m-%d')
            else:
                trans_date = datetime.now()

            trans_type_str = trans_data.get('transaction_type', 'deposit')
            if trans_type_str == 'deposit':
                transaction_type = TransactionType.BUY
            elif trans_type_str == 'interest':
                transaction_type = TransactionType.DIVIDEND
            elif trans_type_str == 'withdrawal':
                transaction_type = TransactionType.SELL
            else:
                transaction_type = TransactionType.BUY

            amount = trans_data.get('amount', 0)

            existing = db.query(Transaction).filter(
                Transaction.asset_id == asset.id,
                Transaction.transaction_date == trans_date,
                Transaction.transaction_type == transaction_type,
                Transaction.total_amount == amount
            ).first()

            if not existing:
                transaction = Transaction(
                    asset_id=asset.id,
                    transaction_type=transaction_type,
                    transaction_date=trans_date,
                    quantity=1.0,
                    price_per_unit=amount,
                    total_amount=amount,
                    fees=0,
                    taxes=0,
                    description=trans_data.get('description', trans_type_str.title()),
                    reference_number=trans_data.get('financial_year')
                )
                db.add(transaction)

        asset.calculate_metrics()
        db.commit()
        db.refresh(asset)

        details = asset.details or {}
        return PPFAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"PPF - {asset.broker_name}",
            account_number=asset.account_id or '',
            bank_name=asset.broker_name or '',
            account_holder_name=asset.account_holder_name or '',
            opening_date=asset.purchase_date.date() if asset.purchase_date else date.today(),
            maturity_date=details.get('maturity_date'),
            interest_rate=details.get('interest_rate', 7.1),
            current_balance=asset.current_value,
            total_deposits=asset.total_invested,
            total_interest_earned=details.get('total_interest_earned', 0.0),
            financial_year=details.get('financial_year'),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PPF statement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process the PPF statement. Please check the file format and try again."
        )


@router.post("/{ppf_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_ppf_statement(
    ppf_id: int,
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PPF statement for a specific PPF account
    """
    # Verify the PPF account exists and belongs to the user
    asset = db.query(Asset).filter(
        Asset.id == ppf_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPF account not found"
        )
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Create upload directory
        upload_dir = f"backend/uploads/{current_user.id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create statement record
        statement = Statement(
            user_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file.content_type or "application/octet-stream",
            statement_type=StatementType.PPF_STATEMENT,
            status=StatementStatus.PROCESSING,
            password=password
        )
        
        db.add(statement)
        db.commit()
        db.refresh(statement)
        
        # Parse the statement
        try:
            statement.processing_started_at = datetime.now()
            db.commit()
            
            parser = PPFStatementParser()
            parsed_data = parser.parse_statement(file_path, password)

            # Validate that the statement matches the selected PPF account
            account_details = parsed_data.get('account_details', {})
            extracted_holder = (account_details.get('account_holder_name') or
                                account_details.get('account_holder', '')).strip()
            existing_holder = (asset.account_holder_name or '').strip()
            if extracted_holder and existing_holder:
                if extracted_holder.lower() != existing_holder.lower():
                    statement.status = StatementStatus.FAILED
                    statement.error_message = (
                        f"Statement mismatch: this statement belongs to '{extracted_holder}', "
                        f"but the selected account is held by '{existing_holder}'."
                    )
                    statement.processing_completed_at = datetime.now()
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Statement mismatch: this statement belongs to '{extracted_holder}', "
                            f"but the selected PPF account is held by '{existing_holder}'. "
                            f"Please use 'Add New Account' if this is a different account."
                        )
                    )

            extracted_acct_num = (account_details.get('account_number') or '').strip()
            existing_acct_id = (asset.account_id or '').strip()
            if extracted_acct_num and existing_acct_id:
                if extracted_acct_num != existing_acct_id:
                    statement.status = StatementStatus.FAILED
                    statement.error_message = (
                        f"Statement mismatch: statement is for account {extracted_acct_num}, "
                        f"but the selected account is {existing_acct_id}."
                    )
                    statement.processing_completed_at = datetime.now()
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Statement mismatch: this statement is for PPF account {extracted_acct_num}, "
                            f"but you selected account {existing_acct_id}. "
                            f"Please use 'Add New Account' if this is a different account."
                        )
                    )
            
            # Update asset with parsed data (if available)
            if account_details.get('current_balance'):
                asset.current_value = account_details['current_balance']
                asset.current_price = account_details['current_balance']
            if account_details.get('total_deposits'):
                asset.total_invested = account_details['total_deposits']
            if account_details.get('interest_rate'):
                if not asset.details:
                    asset.details = {}
                asset.details['interest_rate'] = account_details['interest_rate']
            if account_details.get('total_interest_earned'):
                if not asset.details:
                    asset.details = {}
                asset.details['total_interest_earned'] = account_details['total_interest_earned']
            
            # Link statement to asset
            statement.assets_found = 1
            
            # Add transactions (with duplicate detection)
            transactions_added = 0
            transactions_skipped = 0
            for trans_data in parsed_data.get('transactions', []):
                trans_date = trans_data.get('transaction_date')
                if trans_date:
                    trans_date = datetime.fromisoformat(trans_date)
                else:
                    trans_date = datetime.now()
                
                trans_type = trans_data.get('transaction_type', 'deposit')
                if trans_type == 'deposit':
                    transaction_type = TransactionType.BUY
                elif trans_type == 'interest':
                    transaction_type = TransactionType.DIVIDEND
                elif trans_type == 'withdrawal':
                    transaction_type = TransactionType.SELL
                else:
                    transaction_type = TransactionType.BUY
                
                amount = trans_data.get('amount', 0)
                
                # Check if transaction already exists (same asset, date, type, and amount)
                existing_transaction = db.query(Transaction).filter(
                    Transaction.asset_id == asset.id,
                    Transaction.transaction_date == trans_date,
                    Transaction.transaction_type == transaction_type,
                    Transaction.total_amount == amount
                ).first()
                
                if existing_transaction:
                    transactions_skipped += 1
                    continue
                
                transaction = Transaction(
                    asset_id=asset.id,
                    statement_id=statement.id,
                    transaction_type=transaction_type,
                    transaction_date=trans_date,
                    quantity=1.0,
                    price_per_unit=amount,
                    total_amount=amount,
                    description=trans_data.get('description', trans_type.title()),
                    reference_number=trans_data.get('financial_year')
                )
                db.add(transaction)
                transactions_added += 1
            
            # Update statement status
            statement.status = StatementStatus.PROCESSED
            statement.processing_completed_at = datetime.now()
            statement.assets_found = 1
            statement.transactions_found = transactions_added
            
            asset.calculate_metrics()
            
            db.commit()
            
            return {
                "message": "PPF statement processed successfully",
                "statement_id": statement.id,
                "asset_id": asset.id,
                "transactions_added": transactions_added,
                "account_number": account_details.get('account_number'),
                "current_balance": account_details.get('current_balance', 0)
            }
            
        except Exception as e:
            logger.error(f"Error processing PPF statement: {str(e)}")
            statement.status = StatementStatus.FAILED
            statement.error_message = str(e)
            statement.processing_completed_at = datetime.now()
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not process the PPF statement. Please check the file format and try again."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading PPF statement: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Statement upload failed. Please try again."
        )


@router.post("/{ppf_id}/transactions", response_model=PPFTransaction, status_code=status.HTTP_201_CREATED)
async def add_ppf_transaction(
    ppf_id: int,
    transaction_data: PPFTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a transaction to a PPF account
    """
    asset = db.query(Asset).filter(
        Asset.id == ppf_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PPF
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PPF account not found"
        )
    
    # Determine transaction type
    trans_type = transaction_data.transaction_type
    if trans_type == 'deposit':
        transaction_type = TransactionType.BUY
    elif trans_type == 'interest':
        transaction_type = TransactionType.DIVIDEND
    elif trans_type == 'withdrawal':
        transaction_type = TransactionType.SELL
    else:
        transaction_type = TransactionType.BUY
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        asset_id=asset.id,
        transaction_type=transaction_type,
        transaction_date=datetime.combine(transaction_data.transaction_date, datetime.min.time()),
        quantity=1.0,
        price=transaction_data.amount,
        amount=transaction_data.amount,
        balance_after=transaction_data.balance_after_transaction,
        description=transaction_data.description or trans_type.title(),
        details={
            'financial_year': transaction_data.financial_year
        }
    )
    
    db.add(transaction)
    
    # Update asset values
    if trans_type == 'deposit':
        asset.total_invested += transaction_data.amount
    elif trans_type == 'interest':
        if not asset.details:
            asset.details = {}
        current_interest = asset.details.get('total_interest_earned', 0)
        asset.details['total_interest_earned'] = current_interest + transaction_data.amount
    
    asset.current_value = transaction_data.balance_after_transaction
    asset.current_price = transaction_data.balance_after_transaction
    asset.calculate_metrics()
    
    db.commit()
    db.refresh(transaction)
    
    return PPFTransaction(
        id=transaction.id,
        asset_id=transaction.asset_id,
        transaction_date=transaction.transaction_date.date(),
        transaction_type=trans_type,
        amount=transaction_data.amount,
        balance_after_transaction=transaction_data.balance_after_transaction,
        description=transaction.description,
        financial_year=transaction_data.financial_year,
        created_at=transaction.created_at
    )

# Made with Bob