from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExpenseCategoryBase(BaseModel):
    """Base expense category schema"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[int] = None
    is_income: bool = Field(default=False)
    is_active: bool = Field(default=True)
    keywords: Optional[str] = None


class ExpenseCategoryCreate(ExpenseCategoryBase):
    """Schema for creating an expense category"""
    pass


class ExpenseCategoryUpdate(BaseModel):
    """Schema for updating an expense category"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    parent_id: Optional[int] = None
    is_income: Optional[bool] = None
    is_active: Optional[bool] = None
    keywords: Optional[str] = None


class ExpenseCategoryInDB(ExpenseCategoryBase):
    """Schema for expense category in database"""
    id: int
    user_id: Optional[int] = None
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ExpenseCategory(ExpenseCategoryInDB):
    """Schema for expense category response"""
    pass


class ExpenseCategoryWithStats(ExpenseCategory):
    """Schema for expense category with statistics"""
    expense_count: int = 0
    total_amount: float = 0.0
    subcategory_count: int = 0


class ExpenseCategoryTree(ExpenseCategory):
    """Schema for expense category with subcategories"""
    subcategories: List['ExpenseCategoryTree'] = []


# Update forward references
ExpenseCategoryTree.model_rebuild()


class CategorySummary(BaseModel):
    """Schema for category-wise expense summary"""
    category_id: int
    category_name: str
    total_amount: float
    transaction_count: int
    percentage: float
    
    class Config:
        from_attributes = True

# Made with Bob