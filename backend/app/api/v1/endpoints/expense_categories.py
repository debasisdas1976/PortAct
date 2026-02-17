from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.expense_category import ExpenseCategory
from app.models.expense import Expense
from app.schemas.expense_category import (
    ExpenseCategory as ExpenseCategorySchema,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCategoryWithStats,
    ExpenseCategoryTree,
    CategorySummary
)

router = APIRouter()


@router.get("/", response_model=List[ExpenseCategorySchema])
async def get_expense_categories(
    is_income: Optional[bool] = None,
    is_active: Optional[bool] = None,
    parent_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all expense categories (system + user-defined)
    """
    query = db.query(ExpenseCategory).filter(
        or_(
            ExpenseCategory.is_system == True,
            ExpenseCategory.user_id == current_user.id
        )
    )
    
    if is_income is not None:
        query = query.filter(ExpenseCategory.is_income == is_income)
    
    if is_active is not None:
        query = query.filter(ExpenseCategory.is_active == is_active)
    
    if parent_id is not None:
        query = query.filter(ExpenseCategory.parent_id == parent_id)
    
    categories = query.offset(skip).limit(limit).all()
    return categories


@router.get("/tree", response_model=List[ExpenseCategoryTree])
async def get_expense_categories_tree(
    is_income: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get expense categories in hierarchical tree structure
    """
    query = db.query(ExpenseCategory).filter(
        or_(
            ExpenseCategory.is_system == True,
            ExpenseCategory.user_id == current_user.id
        ),
        ExpenseCategory.is_active == True
    )
    
    if is_income is not None:
        query = query.filter(ExpenseCategory.is_income == is_income)
    
    all_categories = query.all()
    
    # Build tree structure
    category_dict = {cat.id: cat for cat in all_categories}
    tree = []
    
    for category in all_categories:
        if category.parent_id is None:
            # Root category
            cat_dict = category.__dict__.copy()
            cat_dict['subcategories'] = []
            tree.append(ExpenseCategoryTree(**cat_dict))
        else:
            # Child category - will be added to parent
            pass
    
    # Add subcategories
    for category in all_categories:
        if category.parent_id is not None:
            parent = category_dict.get(category.parent_id)
            if parent:
                for tree_cat in tree:
                    if tree_cat.id == parent.id:
                        cat_dict = category.__dict__.copy()
                        cat_dict['subcategories'] = []
                        tree_cat.subcategories.append(ExpenseCategoryTree(**cat_dict))
    
    return tree


@router.get("/summary", response_model=List[CategorySummary])
async def get_category_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get expense summary by category
    """
    query = db.query(
        ExpenseCategory.id,
        ExpenseCategory.name,
        func.sum(Expense.amount).label('total_amount'),
        func.count(Expense.id).label('transaction_count')
    ).join(
        Expense, Expense.category_id == ExpenseCategory.id
    ).filter(
        Expense.user_id == current_user.id
    ).group_by(
        ExpenseCategory.id,
        ExpenseCategory.name
    )
    
    if start_date:
        query = query.filter(Expense.transaction_date >= start_date)
    if end_date:
        query = query.filter(Expense.transaction_date <= end_date)
    
    results = query.all()
    
    # Calculate total for percentage
    total = sum(r.total_amount for r in results)
    
    summaries = []
    for result in results:
        percentage = (result.total_amount / total * 100) if total > 0 else 0
        summaries.append(CategorySummary(
            category_id=result.id,
            category_name=result.name,
            total_amount=result.total_amount,
            transaction_count=result.transaction_count,
            percentage=percentage
        ))
    
    return summaries


@router.get("/{category_id}", response_model=ExpenseCategoryWithStats)
async def get_expense_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific expense category with statistics
    """
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        or_(
            ExpenseCategory.is_system == True,
            ExpenseCategory.user_id == current_user.id
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense category not found"
        )
    
    # Get statistics
    expense_count = db.query(func.count(Expense.id)).filter(
        Expense.category_id == category_id,
        Expense.user_id == current_user.id
    ).scalar() or 0
    
    total_amount = db.query(func.sum(Expense.amount)).filter(
        Expense.category_id == category_id,
        Expense.user_id == current_user.id
    ).scalar() or 0.0
    
    subcategory_count = db.query(func.count(ExpenseCategory.id)).filter(
        ExpenseCategory.parent_id == category_id
    ).scalar() or 0
    
    cat_dict = category.__dict__.copy()
    cat_dict['expense_count'] = expense_count
    cat_dict['total_amount'] = total_amount
    cat_dict['subcategory_count'] = subcategory_count
    
    return ExpenseCategoryWithStats(**cat_dict)


@router.post("/", response_model=ExpenseCategorySchema, status_code=status.HTTP_201_CREATED)
async def create_expense_category(
    category_data: ExpenseCategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new expense category
    """
    # Check if category with same name exists
    existing = db.query(ExpenseCategory).filter(
        ExpenseCategory.user_id == current_user.id,
        ExpenseCategory.name == category_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = ExpenseCategory(
        **category_data.model_dump(),
        user_id=current_user.id,
        is_system=False
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.put("/{category_id}", response_model=ExpenseCategorySchema)
async def update_expense_category(
    category_id: int,
    category_data: ExpenseCategoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an expense category (user-defined or system categories)
    """
    # Allow updating both user categories and system categories
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        or_(
            ExpenseCategory.user_id == current_user.id,
            ExpenseCategory.is_system == True
        )
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense category not found"
        )
    
    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an expense category (only user-defined categories)
    """
    category = db.query(ExpenseCategory).filter(
        ExpenseCategory.id == category_id,
        ExpenseCategory.user_id == current_user.id,
        ExpenseCategory.is_system == False
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense category not found or cannot be deleted"
        )
    
    # Check if category has expenses
    expense_count = db.query(func.count(Expense.id)).filter(
        Expense.category_id == category_id
    ).scalar()
    
    if expense_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {expense_count} associated expenses"
        )
    
    db.delete(category)
    db.commit()
    
    return None


@router.post("/recategorize", status_code=status.HTTP_200_OK)
async def recategorize_expenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Re-categorize all uncategorized or existing expenses based on category keywords
    """
    # Get all active categories with keywords
    categories = db.query(ExpenseCategory).filter(
        or_(
            ExpenseCategory.is_system == True,
            ExpenseCategory.user_id == current_user.id
        ),
        ExpenseCategory.is_active == True,
        ExpenseCategory.keywords.isnot(None)
    ).all()
    
    # Get all expenses for the user
    expenses = db.query(Expense).filter(
        Expense.user_id == current_user.id
    ).all()
    
    categorized_count = 0
    updated_count = 0
    
    for expense in expenses:
        description_lower = expense.description.lower() if expense.description else ""
        merchant_lower = expense.merchant_name.lower() if expense.merchant_name else ""
        combined_text = f"{description_lower} {merchant_lower}"
        
        # Try to match with categories
        matched_category = None
        for category in categories:
            if not category.keywords:
                continue
                
            keywords = [k.strip().lower() for k in category.keywords.split(',') if k.strip()]
            
            # Check if any keyword matches
            for keyword in keywords:
                if keyword in combined_text:
                    matched_category = category
                    break
            
            if matched_category:
                break
        
        # Update expense if a match is found
        if matched_category:
            if expense.category_id != matched_category.id:
                expense.category_id = matched_category.id
                expense.is_categorized = True
                updated_count += 1
            elif not expense.is_categorized:
                expense.is_categorized = True
                categorized_count += 1
    
    db.commit()
    
    return {
        "message": "Re-categorization complete",
        "total_expenses": len(expenses),
        "updated": updated_count,
        "marked_categorized": categorized_count,
        "total_affected": updated_count + categorized_count
    }

# Made with Bob