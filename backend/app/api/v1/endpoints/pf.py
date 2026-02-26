"""
PF (Provident Fund/EPF) Account API Endpoints
"""
import logging
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.api.dependencies import get_current_active_user, get_db, get_default_portfolio_id
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.schemas.pf import (
    PFAccountCreate,
    PFAccountUpdate,
    PFAccountResponse,
    PFAccountWithTransactions,
    PFTransaction,
    PFTransactionCreate,
    PFStatementUpload,
    PFSummary,
)
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.alert import Alert
from app.models.mutual_fund_holding import MutualFundHolding
from app.services.pf_parser import PFStatementParser

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[PFAccountResponse])
async def get_all_pf_accounts(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all PF accounts for the current user"""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    pf_accounts = []
    for asset in assets:
        # Ensure required fields have valid values
        uan = asset.details.get('uan_number', '').strip()
        if not uan or len(uan) < 12:
            uan = '000000000000'
        
        holder_name = (asset.account_holder_name or '').strip()
        if not holder_name:
            holder_name = 'Unknown'
        
        employer = (asset.broker_name or '').strip()
        if not employer:
            employer = 'Unknown Employer'
        
        pf_account = PFAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"PF - {employer}",
            uan_number=uan,
            pf_number=asset.account_id or None,
            account_holder_name=holder_name,
            employer_name=employer,
            date_of_joining=datetime.strptime(asset.details.get('date_of_joining'), '%Y-%m-%d').date() if asset.details.get('date_of_joining') else date.today(),
            date_of_exit=datetime.strptime(asset.details.get('date_of_exit'), '%Y-%m-%d').date() if asset.details.get('date_of_exit') else None,
            current_balance=asset.current_value,
            employee_contribution=asset.details.get('employee_contribution', 0),
            employer_contribution=asset.details.get('employer_contribution', 0),
            pension_contribution=asset.details.get('pension_contribution', 0),
            total_interest_earned=asset.profit_loss,
            interest_rate=asset.details.get('interest_rate', 8.25),
            is_active=asset.details.get('is_active', True),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        pf_accounts.append(pf_account)
    
    return pf_accounts


@router.get("/summary", response_model=PFSummary)
async def get_pf_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary statistics for all PF accounts"""
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    total_accounts = len(assets)
    active_accounts = sum(1 for asset in assets if asset.details.get('is_active', True))
    total_balance = sum(asset.current_value for asset in assets)
    employee_contribution = sum(asset.details.get('employee_contribution', 0) for asset in assets)
    employer_contribution = sum(asset.details.get('employer_contribution', 0) for asset in assets)
    pension_contribution = sum(asset.details.get('pension_contribution', 0) for asset in assets)
    total_interest = sum(asset.profit_loss for asset in assets)
    
    interest_rates = [asset.details.get('interest_rate', 8.25) for asset in assets if asset.details.get('interest_rate')]
    avg_interest_rate = sum(interest_rates) / len(interest_rates) if interest_rates else 8.25
    
    return PFSummary(
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        total_balance=total_balance,
        employee_contribution=employee_contribution,
        employer_contribution=employer_contribution,
        pension_contribution=pension_contribution,
        total_interest_earned=total_interest,
        average_interest_rate=avg_interest_rate
    )


@router.get("/{account_id}", response_model=PFAccountWithTransactions)
async def get_pf_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific PF account with its transactions"""
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="PF account not found")
    
    transactions = db.query(Transaction).filter(
        Transaction.asset_id == asset.id
    ).order_by(Transaction.transaction_date.desc()).all()
    
    pf_transactions = []
    for trans in transactions:
        # Get transaction type value directly from enum
        trans_type_value = trans.transaction_type.value if hasattr(trans.transaction_type, 'value') else str(trans.transaction_type)
        
        pf_trans = PFTransaction(
            id=trans.id,
            asset_id=trans.asset_id,
            transaction_date=trans.transaction_date.date() if trans.transaction_date else date.today(),
            transaction_type=trans_type_value,  # Use enum value directly (deposit, transfer_in, interest, etc.)
            amount=abs(trans.total_amount),
            balance_after_transaction=0.0,
            contribution_type=trans.details.get('contribution_type') if hasattr(trans, 'details') else None,
            description=trans.description or '',
            financial_year=trans.reference_number,
            created_at=trans.created_at
        )
        pf_transactions.append(pf_trans)
    
    # Ensure required fields have valid values
    uan = asset.details.get('uan_number', '').strip()
    if not uan or len(uan) < 12:
        uan = '000000000000'
    
    holder_name = (asset.account_holder_name or '').strip()
    if not holder_name:
        holder_name = 'Unknown'
    
    employer = (asset.broker_name or '').strip()
    if not employer:
        employer = 'Unknown Employer'
    
    pf_account = PFAccountWithTransactions(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"PF - {employer}",
        uan_number=uan,
        pf_number=asset.account_id or None,
        account_holder_name=holder_name,
        employer_name=employer,
        date_of_joining=datetime.strptime(asset.details.get('date_of_joining'), '%Y-%m-%d').date() if asset.details.get('date_of_joining') else date.today(),
        date_of_exit=datetime.strptime(asset.details.get('date_of_exit'), '%Y-%m-%d').date() if asset.details.get('date_of_exit') else None,
        current_balance=asset.current_value,
        employee_contribution=asset.details.get('employee_contribution', 0),
        employer_contribution=asset.details.get('employer_contribution', 0),
        pension_contribution=asset.details.get('pension_contribution', 0),
        total_interest_earned=asset.profit_loss,
        interest_rate=asset.details.get('interest_rate', 8.25),
        is_active=asset.details.get('is_active', True),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated,
        transactions=pf_transactions,
        transaction_count=len(pf_transactions)
    )
    
    return pf_account


@router.post("/", response_model=PFAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_pf_account(
    pf_data: PFAccountCreate,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new PF account manually"""
    resolved_portfolio_id = portfolio_id or pf_data.portfolio_id or get_default_portfolio_id(current_user.id, db)

    asset = Asset(
        user_id=current_user.id,
        asset_type=AssetType.PF,
        name=pf_data.nickname,
        broker_name=pf_data.employer_name,
        account_id=pf_data.pf_number,
        account_holder_name=pf_data.account_holder_name,
        purchase_date=datetime.combine(pf_data.date_of_joining, datetime.min.time()),
        quantity=1,
        purchase_price=pf_data.current_balance,
        current_price=pf_data.current_balance,
        current_value=pf_data.current_balance,
        total_invested=pf_data.employee_contribution + pf_data.employer_contribution,
        profit_loss=pf_data.total_interest_earned,
        notes=pf_data.notes,
        portfolio_id=resolved_portfolio_id,
        details={
            'uan_number': pf_data.uan_number,
            'date_of_joining': pf_data.date_of_joining.strftime('%Y-%m-%d'),
            'date_of_exit': pf_data.date_of_exit.strftime('%Y-%m-%d') if pf_data.date_of_exit else None,
            'employee_contribution': pf_data.employee_contribution,
            'employer_contribution': pf_data.employer_contribution,
            'pension_contribution': pf_data.pension_contribution,
            'interest_rate': pf_data.interest_rate,
            'is_active': pf_data.is_active,
        }
    )
    
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return PFAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name,
        uan_number=pf_data.uan_number,
        pf_number=asset.account_id or "",
        account_holder_name=asset.account_holder_name or "",
        employer_name=asset.broker_name or "",
        date_of_joining=pf_data.date_of_joining,
        date_of_exit=pf_data.date_of_exit,
        current_balance=asset.current_value,
        employee_contribution=pf_data.employee_contribution,
        employer_contribution=pf_data.employer_contribution,
        pension_contribution=pf_data.pension_contribution,
        total_interest_earned=asset.profit_loss,
        interest_rate=pf_data.interest_rate,
        is_active=pf_data.is_active,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.put("/{account_id}", response_model=PFAccountResponse)
async def update_pf_account(
    account_id: int,
    pf_data: PFAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update an existing PF account"""
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="PF account not found")
    
    update_data = pf_data.dict(exclude_unset=True)
    
    if 'nickname' in update_data:
        asset.name = update_data['nickname']
    if 'pf_number' in update_data:
        asset.account_id = update_data['pf_number']
    if 'employer_name' in update_data:
        asset.broker_name = update_data['employer_name']
    if 'date_of_exit' in update_data:
        asset.details['date_of_exit'] = update_data['date_of_exit'].strftime('%Y-%m-%d') if update_data['date_of_exit'] else None
    if 'current_balance' in update_data:
        asset.current_value = update_data['current_balance']
        asset.current_price = update_data['current_balance']
    if 'employee_contribution' in update_data:
        asset.details['employee_contribution'] = update_data['employee_contribution']
    if 'employer_contribution' in update_data:
        asset.details['employer_contribution'] = update_data['employer_contribution']
    if 'pension_contribution' in update_data:
        asset.details['pension_contribution'] = update_data['pension_contribution']
    if 'total_interest_earned' in update_data:
        asset.profit_loss = update_data['total_interest_earned']
    if 'interest_rate' in update_data:
        asset.details['interest_rate'] = update_data['interest_rate']
    if 'is_active' in update_data:
        asset.details['is_active'] = update_data['is_active']
    if 'notes' in update_data:
        asset.notes = update_data['notes']
    
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(asset)
    
    # Ensure required fields have valid values
    uan = asset.details.get('uan_number', '').strip()
    if not uan or len(uan) < 12:
        uan = '000000000000'  # Default UAN if not found
    
    holder_name = (asset.account_holder_name or '').strip()
    if not holder_name:
        holder_name = 'Unknown'
    
    employer = (asset.broker_name or '').strip()
    if not employer:
        employer = 'Unknown Employer'
    
    return PFAccountResponse(
        id=asset.id,
        user_id=asset.user_id,
        asset_id=asset.id,
        nickname=asset.name or f"PF - {employer}",
        uan_number=uan,
        pf_number=asset.account_id or None,
        account_holder_name=holder_name,
        employer_name=employer,
        date_of_joining=datetime.strptime(asset.details.get('date_of_joining'), '%Y-%m-%d').date() if asset.details.get('date_of_joining') else date.today(),
        date_of_exit=datetime.strptime(asset.details.get('date_of_exit'), '%Y-%m-%d').date() if asset.details.get('date_of_exit') else None,
        current_balance=asset.current_value,
        employee_contribution=asset.details.get('employee_contribution', 0),
        employer_contribution=asset.details.get('employer_contribution', 0),
        pension_contribution=asset.details.get('pension_contribution', 0),
        total_interest_earned=asset.profit_loss,
        interest_rate=asset.details.get('interest_rate', 8.25),
        is_active=asset.details.get('is_active', True),
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.last_updated
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pf_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a PF account and all its transactions"""
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="PF account not found")

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


@router.post("/{account_id}/transactions", response_model=PFTransaction, status_code=status.HTTP_201_CREATED)
async def add_pf_transaction(
    account_id: int,
    transaction_data: PFTransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a transaction to a PF account"""
    asset = db.query(Asset).filter(
        Asset.id == account_id,
        Asset.user_id == current_user.id,
        Asset.asset_type == AssetType.PF
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="PF account not found")
    
    trans_type_map = {
        'employee_contribution': TransactionType.DEPOSIT,
        'employer_contribution': TransactionType.TRANSFER_IN,
        'pension_contribution': TransactionType.DEPOSIT,
        'interest': TransactionType.INTEREST,
        'withdrawal': TransactionType.WITHDRAWAL,
        'transfer': TransactionType.TRANSFER_OUT
    }

    trans_type = trans_type_map.get(transaction_data.transaction_type, TransactionType.DEPOSIT)
    
    existing = db.query(Transaction).filter(
        Transaction.asset_id == asset.id,
        Transaction.transaction_date == datetime.combine(transaction_data.transaction_date, datetime.min.time()),
        Transaction.transaction_type == trans_type,
        Transaction.total_amount == transaction_data.amount
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate transaction detected")
    
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
    
    if transaction_data.transaction_type == 'employee_contribution':
        asset.details['employee_contribution'] = asset.details.get('employee_contribution', 0) + transaction_data.amount
    elif transaction_data.transaction_type == 'employer_contribution':
        asset.details['employer_contribution'] = asset.details.get('employer_contribution', 0) + transaction_data.amount
    elif transaction_data.transaction_type == 'pension_contribution':
        asset.details['pension_contribution'] = asset.details.get('pension_contribution', 0) + transaction_data.amount
    elif transaction_data.transaction_type == 'interest':
        asset.profit_loss += transaction_data.amount
    
    asset.current_value = transaction_data.balance_after_transaction
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    db.refresh(transaction)
    
    return PFTransaction(
        id=transaction.id,
        asset_id=transaction.asset_id,
        transaction_date=transaction.transaction_date.date(),
        transaction_type=transaction_data.transaction_type,
        amount=transaction_data.amount,
        balance_after_transaction=transaction_data.balance_after_transaction,
        contribution_type=transaction_data.contribution_type,
        description=transaction_data.description,
        financial_year=transaction_data.financial_year,
        created_at=transaction.created_at
    )


@router.post("/upload", response_model=PFAccountResponse, status_code=status.HTTP_201_CREATED)
async def upload_pf_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    portfolio_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload and parse a PF statement PDF"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        content = await file.read()
        parser = PFStatementParser(content, password)
        account_data, transactions = parser.parse()
        
        # Resolve portfolio: use provided value or fall back to user's default
        resolved_portfolio_id = portfolio_id or get_default_portfolio_id(current_user.id, db)

        existing_asset = None
        if account_data.get('uan_number'):
            # Find existing PF account by UAN number
            all_pf_assets = db.query(Asset).filter(
                Asset.user_id == current_user.id,
                Asset.asset_type == AssetType.PF
            ).all()

            for asset_item in all_pf_assets:
                if asset_item.details.get('uan_number') == account_data['uan_number']:
                    existing_asset = asset_item
                    break

        if existing_asset:
            asset = existing_asset
        else:
            date_of_joining = datetime.strptime(account_data.get('date_of_joining', date.today().strftime('%Y-%m-%d')), '%Y-%m-%d')

            asset = Asset(
                user_id=current_user.id,
                asset_type=AssetType.PF,
                portfolio_id=resolved_portfolio_id,
                name=f"PF - {account_data.get('employer_name', 'Account')}",
                broker_name=account_data.get('employer_name', ''),
                account_id=account_data.get('pf_number', ''),
                account_holder_name=account_data.get('account_holder_name', ''),
                purchase_date=date_of_joining,
                quantity=1,
                purchase_price=account_data.get('current_balance', 0),
                current_price=account_data.get('current_balance', 0),
                current_value=account_data.get('current_balance', 0),
                total_invested=account_data.get('employee_contribution', 0) + account_data.get('employer_contribution', 0),
                profit_loss=account_data.get('total_interest_earned', 0),
                details={
                    'uan_number': account_data.get('uan_number', ''),
                    'date_of_joining': date_of_joining.strftime('%Y-%m-%d'),
                    'date_of_exit': account_data.get('date_of_exit'),
                    'employee_contribution': account_data.get('employee_contribution', 0),
                    'employer_contribution': account_data.get('employer_contribution', 0),
                    'pension_contribution': account_data.get('pension_contribution', 0),
                    'interest_rate': account_data.get('interest_rate', 8.25),
                    'is_active': account_data.get('is_active', True),
                }
            )
            
            db.add(asset)
            db.commit()
            db.refresh(asset)
        
        # Separate interest from contributions:
        # The passbook's Employee Share / Employer Share totals include interest.
        # Sum up interest transactions and subtract from share totals so that
        # contributions reflect only actual deposits.
        total_employee_interest = sum(
            t['amount'] for t in transactions if t['transaction_type'] == 'employee_interest'
        )
        total_employer_interest = sum(
            t['amount'] for t in transactions if t['transaction_type'] == 'employer_interest'
        )
        total_interest = total_employee_interest + total_employer_interest

        if total_interest > 0:
            emp_share = account_data.get('employee_contribution', 0)
            er_share = account_data.get('employer_contribution', 0)
            # Subtract interest from share totals to get pure contributions.
            # The passbook balance (current_value) stays as-is since
            # Employee Share + Employer Share is the most reliable number.
            emp_contrib = emp_share - total_employee_interest if emp_share >= total_employee_interest else emp_share
            er_contrib = er_share - total_employer_interest if er_share >= total_employer_interest else er_share

            logger.info(
                f"PF interest split: emp_share={emp_share}, er_share={er_share}, "
                f"emp_interest={total_employee_interest}, er_interest={total_employer_interest}, "
                f"emp_contrib={emp_contrib}, er_contrib={er_contrib}, "
                f"total_interest={total_interest}, balance={asset.current_value}"
            )

            # Reassign the whole dict so SQLAlchemy detects the change
            updated_details = dict(asset.details)
            updated_details['employee_contribution'] = emp_contrib
            updated_details['employer_contribution'] = er_contrib
            asset.details = updated_details
            flag_modified(asset, 'details')

            asset.total_invested = emp_contrib + er_contrib
            asset.profit_loss = total_interest

            db.flush()

        for trans_data in transactions:
            trans_type_map = {
                'employee_contribution': TransactionType.DEPOSIT,
                'employer_contribution': TransactionType.TRANSFER_IN,
                'pension_contribution': TransactionType.DEPOSIT,
                'employee_interest': TransactionType.INTEREST,
                'employer_interest': TransactionType.DIVIDEND,
                'interest': TransactionType.INTEREST,
                'interest_credit': TransactionType.INTEREST,
                'withdrawal': TransactionType.WITHDRAWAL,
                'transfer': TransactionType.TRANSFER_OUT
            }
            
            trans_type = trans_type_map.get(trans_data['transaction_type'], TransactionType.DEPOSIT)
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
        
        # Ensure required fields have valid values
        uan = asset.details.get('uan_number', '').strip()
        if not uan or len(uan) < 12:
            uan = '000000000000'
        
        holder_name = (asset.account_holder_name or '').strip()
        if not holder_name:
            holder_name = 'Unknown'
        
        employer = (asset.broker_name or '').strip()
        if not employer:
            employer = 'Unknown Employer'
        
        return PFAccountResponse(
            id=asset.id,
            user_id=asset.user_id,
            asset_id=asset.id,
            nickname=asset.name or f"PF - {employer}",
            uan_number=uan,
            pf_number=asset.account_id or None,
            account_holder_name=holder_name,
            employer_name=employer,
            date_of_joining=datetime.strptime(asset.details.get('date_of_joining'), '%Y-%m-%d').date() if asset.details.get('date_of_joining') else date.today(),
            date_of_exit=datetime.strptime(asset.details.get('date_of_exit'), '%Y-%m-%d').date() if asset.details.get('date_of_exit') else None,
            current_balance=asset.current_value,
            employee_contribution=asset.details.get('employee_contribution', 0),
            employer_contribution=asset.details.get('employer_contribution', 0),
            pension_contribution=asset.details.get('pension_contribution', 0),
            total_interest_earned=asset.profit_loss,
            interest_rate=asset.details.get('interest_rate', 8.25),
            is_active=asset.details.get('is_active', True),
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not process the PF statement. Please check the file format.")

# Made with Bob
