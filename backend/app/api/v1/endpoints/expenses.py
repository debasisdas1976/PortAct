from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, extract
from datetime import datetime, timedelta
from app.core.database import get_db
from app.api.dependencies import get_current_active_user, get_default_portfolio_id
from app.models.user import User
from app.models.expense import Expense, ExpenseType, PaymentMethod
from app.models.bank_account import BankAccount
from app.models.expense_category import ExpenseCategory
from app.schemas.expense import (
    Expense as ExpenseSchema,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseWithDetails,
    ExpenseSummary,
    MonthlyExpenseReport,
    ExpenseFilter
)

router = APIRouter()


@router.get("/")
async def get_expenses(
    bank_account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[ExpenseType] = None,
    payment_method: Optional[PaymentMethod] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    is_categorized: Optional[bool] = None,
    is_reconciled: Optional[bool] = None,
    search_query: Optional[str] = None,
    portfolio_id: Optional[int] = None,
    order_by: Optional[str] = Query("transaction_date", regex="^(transaction_date|amount|description|merchant_name|transaction_type|category_name|bank_account_name)$"),
    order: Optional[str] = Query("desc", regex="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all expenses with advanced filtering and sorting
    """
    # Join with related tables for sorting by name fields
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

    if portfolio_id is not None:
        query = query.filter(Expense.portfolio_id == portfolio_id)

    # Add joins if sorting by related table fields
    if order_by == "category_name":
        query = query.outerjoin(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
    elif order_by == "bank_account_name":
        query = query.join(BankAccount, Expense.bank_account_id == BankAccount.id)
    
    if bank_account_id:
        query = query.filter(Expense.bank_account_id == bank_account_id)
    
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    
    if transaction_type:
        query = query.filter(Expense.transaction_type == transaction_type)
    
    if payment_method:
        query = query.filter(Expense.payment_method == payment_method)
    
    if start_date:
        query = query.filter(Expense.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(Expense.transaction_date <= end_date)
    
    if min_amount is not None:
        query = query.filter(Expense.amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(Expense.amount <= max_amount)
    
    if is_categorized is not None:
        query = query.filter(Expense.is_categorized == is_categorized)
    
    if is_reconciled is not None:
        query = query.filter(Expense.is_reconciled == is_reconciled)
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Expense.description.ilike(search_pattern),
                Expense.merchant_name.ilike(search_pattern),
                Expense.reference_number.ilike(search_pattern)
            )
        )
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply sorting
    if order_by == "category_name":
        # Sort by category name (handle NULL values)
        if order == "desc":
            query = query.order_by(ExpenseCategory.name.desc().nullslast())
        else:
            query = query.order_by(ExpenseCategory.name.asc().nullslast())
    elif order_by == "bank_account_name":
        # Sort by bank account nickname or bank name
        if order == "desc":
            query = query.order_by(BankAccount.nickname.desc().nullslast(), BankAccount.bank_name.desc())
        else:
            query = query.order_by(BankAccount.nickname.asc().nullslast(), BankAccount.bank_name.asc())
    else:
        # Sort by expense table columns
        order_column = getattr(Expense, order_by, Expense.transaction_date)
        if order == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    
    expenses = query.offset(skip).limit(limit).all()

    # Batch-load all referenced bank accounts and categories in two queries
    bank_account_ids = {e.bank_account_id for e in expenses if e.bank_account_id}
    category_ids = {e.category_id for e in expenses if e.category_id}

    bank_account_map = {}
    if bank_account_ids:
        bank_accounts = db.query(BankAccount).filter(BankAccount.id.in_(bank_account_ids)).all()
        for ba in bank_accounts:
            bank_account_map[ba.id] = ba.nickname or f"{ba.bank_name} - {ba.account_number[-4:]}"

    category_map = {}
    if category_ids:
        categories = db.query(ExpenseCategory).filter(ExpenseCategory.id.in_(category_ids)).all()
        for cat in categories:
            category_map[cat.id] = cat.name

    # Enrich with bank account and category names from the pre-loaded maps
    result = []
    for expense in expenses:
        expense_dict = expense.__dict__.copy()

        if expense.bank_account_id:
            expense_dict['bank_account_name'] = bank_account_map.get(expense.bank_account_id)

        if expense.category_id:
            expense_dict['category_name'] = category_map.get(expense.category_id)

        result.append(ExpenseWithDetails(**expense_dict))

    return {
        "items": result,
        "total": total_count,
        "page": skip // limit if limit > 0 else 0,
        "size": limit
    }


@router.get("/summary", response_model=ExpenseSummary)
async def get_expenses_summary(
    bank_account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[ExpenseType] = None,
    payment_method: Optional[PaymentMethod] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    is_categorized: Optional[bool] = None,
    is_reconciled: Optional[bool] = None,
    search_query: Optional[str] = None,
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get expense summary statistics with same filters as main endpoint
    """
    # Build base query with all filters
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

    if portfolio_id is not None:
        query = query.filter(Expense.portfolio_id == portfolio_id)

    if bank_account_id:
        query = query.filter(Expense.bank_account_id == bank_account_id)

    if category_id:
        query = query.filter(Expense.category_id == category_id)

    if transaction_type:
        query = query.filter(Expense.transaction_type == transaction_type)

    if payment_method:
        query = query.filter(Expense.payment_method == payment_method)

    if start_date:
        query = query.filter(Expense.transaction_date >= start_date)

    if end_date:
        query = query.filter(Expense.transaction_date <= end_date)

    if min_amount is not None:
        query = query.filter(Expense.amount >= min_amount)

    if max_amount is not None:
        query = query.filter(Expense.amount <= max_amount)

    if is_categorized is not None:
        query = query.filter(Expense.is_categorized == is_categorized)

    if is_reconciled is not None:
        query = query.filter(Expense.is_reconciled == is_reconciled)

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Expense.description.ilike(search_pattern),
                Expense.merchant_name.ilike(search_pattern),
                Expense.reference_number.ilike(search_pattern)
            )
        )

    total_expenses = query.count()

    # Build debit query with same filters
    debit_query = db.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_type == ExpenseType.DEBIT
    )

    if portfolio_id is not None:
        debit_query = debit_query.filter(Expense.portfolio_id == portfolio_id)
    if bank_account_id:
        debit_query = debit_query.filter(Expense.bank_account_id == bank_account_id)
    if category_id:
        debit_query = debit_query.filter(Expense.category_id == category_id)
    if payment_method:
        debit_query = debit_query.filter(Expense.payment_method == payment_method)
    if start_date:
        debit_query = debit_query.filter(Expense.transaction_date >= start_date)
    if end_date:
        debit_query = debit_query.filter(Expense.transaction_date <= end_date)
    if min_amount is not None:
        debit_query = debit_query.filter(Expense.amount >= min_amount)
    if max_amount is not None:
        debit_query = debit_query.filter(Expense.amount <= max_amount)
    if is_categorized is not None:
        debit_query = debit_query.filter(Expense.is_categorized == is_categorized)
    if is_reconciled is not None:
        debit_query = debit_query.filter(Expense.is_reconciled == is_reconciled)
    if search_query:
        search_pattern = f"%{search_query}%"
        debit_query = debit_query.filter(
            or_(
                Expense.description.ilike(search_pattern),
                Expense.merchant_name.ilike(search_pattern),
                Expense.reference_number.ilike(search_pattern)
            )
        )

    total_debits = debit_query.scalar() or 0.0

    # Build credit query with same filters
    credit_query = db.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_type == ExpenseType.CREDIT
    )

    if portfolio_id is not None:
        credit_query = credit_query.filter(Expense.portfolio_id == portfolio_id)
    if bank_account_id:
        credit_query = credit_query.filter(Expense.bank_account_id == bank_account_id)
    if category_id:
        credit_query = credit_query.filter(Expense.category_id == category_id)
    if payment_method:
        credit_query = credit_query.filter(Expense.payment_method == payment_method)
    if start_date:
        credit_query = credit_query.filter(Expense.transaction_date >= start_date)
    if end_date:
        credit_query = credit_query.filter(Expense.transaction_date <= end_date)
    if min_amount is not None:
        credit_query = credit_query.filter(Expense.amount >= min_amount)
    if max_amount is not None:
        credit_query = credit_query.filter(Expense.amount <= max_amount)
    if is_categorized is not None:
        credit_query = credit_query.filter(Expense.is_categorized == is_categorized)
    if is_reconciled is not None:
        credit_query = credit_query.filter(Expense.is_reconciled == is_reconciled)
    if search_query:
        search_pattern = f"%{search_query}%"
        credit_query = credit_query.filter(
            or_(
                Expense.description.ilike(search_pattern),
                Expense.merchant_name.ilike(search_pattern),
                Expense.reference_number.ilike(search_pattern)
            )
        )
    
    total_credits = credit_query.scalar() or 0.0
    
    categorized_count = query.filter(Expense.is_categorized == True).count()
    uncategorized_count = query.filter(Expense.is_categorized == False).count()
    
    return ExpenseSummary(
        total_expenses=total_expenses,
        total_debits=total_debits,
        total_credits=total_credits,
        net_amount=total_credits - total_debits,
        categorized_count=categorized_count,
        uncategorized_count=uncategorized_count
    )


@router.get("/monthly-report", response_model=MonthlyExpenseReport)
async def get_monthly_expense_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive monthly expense report
    """
    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get all expenses for the month
    month_query = db.query(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_date >= start_date,
        Expense.transaction_date < end_date
    )
    if portfolio_id is not None:
        month_query = month_query.filter(Expense.portfolio_id == portfolio_id)
    expenses = month_query.all()

    # Calculate totals
    total_income = sum(e.amount for e in expenses if e.transaction_type == ExpenseType.CREDIT)
    total_expenses = sum(e.amount for e in expenses if e.transaction_type == ExpenseType.DEBIT)
    net_savings = total_income - total_expenses

    # Category breakdown
    cat_query = db.query(
        ExpenseCategory.name,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).join(
        Expense, Expense.category_id == ExpenseCategory.id
    ).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_date >= start_date,
        Expense.transaction_date < end_date,
        Expense.transaction_type == ExpenseType.DEBIT
    )
    if portfolio_id is not None:
        cat_query = cat_query.filter(Expense.portfolio_id == portfolio_id)
    category_breakdown = cat_query.group_by(
        ExpenseCategory.name
    ).all()
    
    category_list = [
        {
            'category': cat.name,
            'amount': float(cat.total),
            'count': cat.count,
            'percentage': (float(cat.total) / total_expenses * 100) if total_expenses > 0 else 0
        }
        for cat in category_breakdown
    ]
    
    # Top merchants
    merchant_query = db.query(
        Expense.merchant_name,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_date >= start_date,
        Expense.transaction_date < end_date,
        Expense.transaction_type == ExpenseType.DEBIT,
        Expense.merchant_name.isnot(None)
    )
    if portfolio_id is not None:
        merchant_query = merchant_query.filter(Expense.portfolio_id == portfolio_id)
    top_merchants = merchant_query.group_by(
        Expense.merchant_name
    ).order_by(
        func.sum(Expense.amount).desc()
    ).limit(10).all()
    
    merchant_list = [
        {
            'merchant': m.merchant_name,
            'amount': float(m.total),
            'count': m.count
        }
        for m in top_merchants
    ]
    
    # Payment method breakdown
    payment_query = db.query(
        Expense.payment_method,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_date >= start_date,
        Expense.transaction_date < end_date,
        Expense.transaction_type == ExpenseType.DEBIT,
        Expense.payment_method.isnot(None)
    )
    if portfolio_id is not None:
        payment_query = payment_query.filter(Expense.portfolio_id == portfolio_id)
    payment_breakdown = payment_query.group_by(
        Expense.payment_method
    ).all()
    
    payment_dict = {
        p.payment_method.value: float(p.total)
        for p in payment_breakdown
    }
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    return MonthlyExpenseReport(
        month=month_names[month - 1],
        year=year,
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        category_breakdown=category_list,
        top_merchants=merchant_list,
        payment_method_breakdown=payment_dict
    )


@router.get("/dashboard/monthly-by-category")
async def get_monthly_expenses_by_category(
    months: int = Query(12, ge=1, le=24, description="Number of months to retrieve"),
    year: Optional[int] = Query(None, description="Specific year for single month view"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Specific month for single month view"),
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get monthly expense breakdown by category for the dashboard
    Returns data for the last N months or a specific month if year and month are provided
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    # Calculate date range
    if year and month:
        # Single month view
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        months = 1
    else:
        # Range view
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=months)
    
    # Get all expenses in the date range
    dashboard_query = db.query(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.transaction_date >= start_date,
        Expense.transaction_date <= end_date,
        Expense.transaction_type == ExpenseType.DEBIT
    )
    if portfolio_id is not None:
        dashboard_query = dashboard_query.filter(Expense.portfolio_id == portfolio_id)
    expenses = dashboard_query.all()
    
    # Get all categories (including income categories to handle all cases)
    categories = db.query(ExpenseCategory).filter(
        ExpenseCategory.user_id == current_user.id
    ).all()
    
    # Create a dictionary to store monthly data
    monthly_data = {}
    category_totals = {}
    category_map = {}
    
    # Initialize data structure
    if year and month:
        # For single month view, use the exact month specified
        month_key = start_date.strftime('%Y-%m')
        month_label = start_date.strftime('%b %Y')
        monthly_data[month_key] = {
            'month': month_label,
            'year': start_date.year,
            'month_num': start_date.month,
            'categories': {},
            'total': 0
        }
    else:
        # For range view, iterate backwards from end_date
        for i in range(months):
            month_date = end_date - relativedelta(months=i)
            month_key = month_date.strftime('%Y-%m')
            month_label = month_date.strftime('%b %Y')
            monthly_data[month_key] = {
                'month': month_label,
                'year': month_date.year,
                'month_num': month_date.month,
                'categories': {},
                'total': 0
            }
    
    # Build category map for quick lookup
    for category in categories:
        category_map[category.id] = {
            'name': category.name,
            'icon': category.icon or '📁',
            'color': category.color or '#999999',
            'is_income': category.is_income
        }
        category_totals[category.id] = {
            'name': category.name,
            'icon': category.icon or '📁',
            'color': category.color or '#999999',
            'total': 0
        }
    
    # Add uncategorized
    category_totals[None] = {
        'name': 'Uncategorized',
        'icon': '❓',
        'color': '#999999',
        'total': 0
    }
    
    # Process expenses
    for expense in expenses:
        month_key = expense.transaction_date.strftime('%Y-%m')
        
        if month_key in monthly_data:
            category_id = expense.category_id
            
            # Get category info - try from the expense's category relationship first
            if category_id:
                # Try to get from category_map first
                if category_id in category_map:
                    category_info = category_map[category_id]
                    category_name = category_info['name']
                    category_icon = category_info['icon']
                    category_color = category_info['color']
                else:
                    # Fetch the category directly from the expense relationship
                    category = db.query(ExpenseCategory).filter(
                        ExpenseCategory.id == category_id
                    ).first()
                    
                    if category:
                        category_name = category.name
                        category_icon = category.icon or '📁'
                        category_color = category.color or '#999999'
                        # Add to category_map for future use
                        category_map[category_id] = {
                            'name': category_name,
                            'icon': category_icon,
                            'color': category_color,
                            'is_income': category.is_income
                        }
                    else:
                        # Category was deleted, show as uncategorized
                        category_name = 'Uncategorized (Deleted Category)'
                        category_icon = '❓'
                        category_color = '#999999'
            else:
                # Truly uncategorized expense
                category_name = 'Uncategorized'
                category_icon = '❓'
                category_color = '#999999'
            
            # Add to monthly data
            if category_id not in monthly_data[month_key]['categories']:
                monthly_data[month_key]['categories'][category_id] = {
                    'name': category_name,
                    'icon': category_icon,
                    'color': category_color,
                    'amount': 0
                }
            
            monthly_data[month_key]['categories'][category_id]['amount'] += expense.amount
            monthly_data[month_key]['total'] += expense.amount
            
            # Add to category totals (initialize if not exists)
            if category_id not in category_totals:
                category_totals[category_id] = {
                    'name': category_name,
                    'icon': category_icon,
                    'color': category_color,
                    'total': 0
                }
            category_totals[category_id]['total'] += expense.amount
    
    # Convert to list and sort by date
    monthly_list = sorted(
        monthly_data.values(),
        key=lambda x: (x['year'], x['month_num'])
    )
    
    # Convert categories dict to list for each month
    for month in monthly_list:
        month['categories'] = list(month['categories'].values())
    
    # Convert category totals to list and sort by total
    category_totals_list = sorted(
        [{'id': k, **v} for k, v in category_totals.items() if v['total'] > 0],
        key=lambda x: x['total'],
        reverse=True
    )
    
    return {
        'monthly_data': monthly_list,
        'category_totals': category_totals_list,
        'total_expenses': sum(month['total'] for month in monthly_list),
        'months_count': len(monthly_list)
    }


@router.get("/{expense_id}", response_model=ExpenseWithDetails)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific expense by ID
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    expense_dict = expense.__dict__.copy()
    
    # Get bank account name
    if expense.bank_account_id:
        bank_account = db.query(BankAccount).filter(BankAccount.id == expense.bank_account_id).first()
        expense_dict['bank_account_name'] = bank_account.nickname or f"{bank_account.bank_name} - {bank_account.account_number[-4:]}" if bank_account else None
    
    # Get category name
    if expense.category_id:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == expense.category_id).first()
        expense_dict['category_name'] = category.name if category else None
    
    return ExpenseWithDetails(**expense_dict)


@router.post("/", response_model=ExpenseSchema, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new expense
    """
    # Verify bank account belongs to user
    bank_account = db.query(BankAccount).filter(
        BankAccount.id == expense_data.bank_account_id,
        BankAccount.user_id == current_user.id
    ).first()
    
    if not bank_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )
    
    expense_dict = expense_data.model_dump()

    # Auto-assign to default portfolio if not specified
    if not expense_dict.get('portfolio_id'):
        expense_dict['portfolio_id'] = get_default_portfolio_id(current_user.id, db)

    expense = Expense(
        **expense_dict,
        user_id=current_user.id,
        is_categorized=expense_data.category_id is not None
    )

    db.add(expense)
    db.commit()
    db.refresh(expense)

    return expense


@router.put("/{expense_id}", response_model=ExpenseSchema)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an expense
    Automatically learns from manual categorizations to improve future auto-categorization
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Update fields
    update_data = expense_data.model_dump(exclude_unset=True)
    
    # Update is_categorized if category_id is being set
    if 'category_id' in update_data:
        update_data['is_categorized'] = update_data['category_id'] is not None
        
        # Learn from manual categorization
        if update_data['category_id'] is not None and expense.merchant_name:
            from app.services.expense_categorizer import ExpenseCategorizer
            categorizer = ExpenseCategorizer(db, user_id=current_user.id)
            categorizer.learn_from_categorization(
                expense.merchant_name,
                update_data['category_id']
            )
    
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an expense
    """
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    db.delete(expense)
    db.commit()
    
    return None

# Made with Bob