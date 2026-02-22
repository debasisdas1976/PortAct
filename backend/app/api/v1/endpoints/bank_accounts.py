from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_default_portfolio_id
from app.models.user import User
from app.models.bank_account import BankAccount, BankType
from app.models.expense import Expense, ExpenseType
from app.schemas.bank_account import (
    BankAccount as BankAccountSchema,
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountWithExpenses,
    BankAccountSummary
)

router = APIRouter()


@router.get("/", response_model=List[BankAccountSchema])
async def get_bank_accounts(
    portfolio_id: Optional[int] = None,
    bank_name: Optional[str] = None,
    account_type: Optional[BankType] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all bank accounts for the current user with optional filtering
    """
    query = db.query(BankAccount).filter(BankAccount.user_id == current_user.id)

    if portfolio_id is not None:
        query = query.filter(BankAccount.portfolio_id == portfolio_id)

    if bank_name:
        query = query.filter(BankAccount.bank_name == bank_name)

    if account_type:
        query = query.filter(BankAccount.account_type == account_type)

    if is_active is not None:
        query = query.filter(BankAccount.is_active == is_active)

    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/summary", response_model=BankAccountSummary)
async def get_bank_accounts_summary(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of all bank accounts
    """
    query = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id,
        BankAccount.is_active == True
    )
    if portfolio_id is not None:
        query = query.filter(BankAccount.portfolio_id == portfolio_id)
    accounts = query.all()
    
    total_balance = sum(acc.current_balance for acc in accounts)
    total_credit_limit = sum(acc.credit_limit for acc in accounts if acc.account_type == BankType.CREDIT_CARD)
    
    accounts_by_type = {}
    accounts_by_bank = {}
    
    for account in accounts:
        # By type
        type_key = account.account_type.value
        accounts_by_type[type_key] = accounts_by_type.get(type_key, 0) + 1
        
        # By bank
        bank_key = account.bank_name
        accounts_by_bank[bank_key] = accounts_by_bank.get(bank_key, 0) + 1
    
    return BankAccountSummary(
        total_accounts=len(accounts),
        total_balance=total_balance,
        total_credit_limit=total_credit_limit,
        accounts_by_type=accounts_by_type,
        accounts_by_bank=accounts_by_bank
    )


@router.get("/{account_id}", response_model=BankAccountWithExpenses)
async def get_bank_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific bank account by ID with expense statistics
    """
    account = db.query(BankAccount).filter(
        BankAccount.id == account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    # Get expense statistics
    expense_count = db.query(func.count(Expense.id)).filter(
        Expense.bank_account_id == account_id
    ).scalar()
    
    total_debits = db.query(func.sum(Expense.amount)).filter(
        Expense.bank_account_id == account_id,
        Expense.transaction_type == ExpenseType.DEBIT
    ).scalar() or 0.0
    
    total_credits = db.query(func.sum(Expense.amount)).filter(
        Expense.bank_account_id == account_id,
        Expense.transaction_type == ExpenseType.CREDIT
    ).scalar() or 0.0
    
    # Convert to dict and add statistics
    account_dict = {
        **account.__dict__,
        "expense_count": expense_count,
        "total_debits": total_debits,
        "total_credits": total_credits
    }
    
    return BankAccountWithExpenses(**account_dict)


@router.post("/", response_model=BankAccountSchema, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    account_data: BankAccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new bank account
    """
    # Check if account already exists
    existing = db.query(BankAccount).filter(
        BankAccount.user_id == current_user.id,
        BankAccount.account_number == account_data.account_number,
        BankAccount.bank_name == account_data.bank_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bank account with this account number already exists"
        )
    
    # If this is set as primary, unset other primary accounts
    if account_data.is_primary:
        db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id,
            BankAccount.is_primary == True
        ).update({"is_primary": False})
    
    account_dict = account_data.model_dump()

    # Auto-assign to default portfolio if not specified
    if not account_dict.get('portfolio_id'):
        account_dict['portfolio_id'] = get_default_portfolio_id(current_user.id, db)

    account = BankAccount(
        **account_dict,
        user_id=current_user.id
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


@router.put("/{account_id}", response_model=BankAccountSchema)
async def update_bank_account(
    account_id: int,
    account_data: BankAccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a bank account
    """
    account = db.query(BankAccount).filter(
        BankAccount.id == account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    # If setting as primary, unset other primary accounts
    if account_data.is_primary and not account.is_primary:
        db.query(BankAccount).filter(
            BankAccount.user_id == current_user.id,
            BankAccount.is_primary == True
        ).update({"is_primary": False})
    
    # Update fields
    update_data = account_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a bank account
    """
    account = db.query(BankAccount).filter(
        BankAccount.id == account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    db.delete(account)
    db.commit()
    
    return None

# Made with Bob