from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.expense import ExpenseType, PaymentMethod


class ExpenseBase(BaseModel):
    """Base expense schema"""
    bank_account_id: int
    category_id: Optional[int] = None
    transaction_date: datetime
    transaction_type: ExpenseType
    amount: float = Field(..., description="Transaction amount")
    balance_after: Optional[float] = None
    description: str = Field(..., min_length=1, max_length=500)
    merchant_name: Optional[str] = Field(None, max_length=200)
    reference_number: Optional[str] = Field(None, max_length=100)
    payment_method: Optional[PaymentMethod] = None
    is_recurring: bool = Field(default=False)
    is_split: bool = Field(default=False)
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    tags: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    """Schema for creating an expense"""
    pass


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense"""
    category_id: Optional[int] = None
    transaction_date: Optional[datetime] = None
    transaction_type: Optional[ExpenseType] = None
    amount: Optional[float] = None
    balance_after: Optional[float] = None
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    merchant_name: Optional[str] = Field(None, max_length=200)
    reference_number: Optional[str] = Field(None, max_length=100)
    payment_method: Optional[PaymentMethod] = None
    is_categorized: Optional[bool] = None
    is_recurring: Optional[bool] = None
    is_split: Optional[bool] = None
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    tags: Optional[str] = None
    is_reconciled: Optional[bool] = None


class ExpenseInDB(ExpenseBase):
    """Schema for expense in database"""
    id: int
    user_id: int
    statement_id: Optional[int] = None
    is_categorized: bool
    is_reconciled: bool
    reconciled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Expense(ExpenseInDB):
    """Schema for expense response"""
    pass


class ExpenseWithDetails(Expense):
    """Schema for expense with related details"""
    bank_account_name: Optional[str] = None
    category_name: Optional[str] = None


class ExpenseSummary(BaseModel):
    """Schema for expense summary"""
    total_expenses: int
    total_debits: float
    total_credits: float
    net_amount: float
    categorized_count: int
    uncategorized_count: int
    
    class Config:
        from_attributes = True


class MonthlyExpenseReport(BaseModel):
    """Schema for monthly expense report"""
    month: str
    year: int
    total_income: float
    total_expenses: float
    net_savings: float
    category_breakdown: list
    top_merchants: list
    payment_method_breakdown: dict
    
    class Config:
        from_attributes = True


class ExpenseFilter(BaseModel):
    """Schema for filtering expenses"""
    bank_account_id: Optional[int] = None
    category_id: Optional[int] = None
    transaction_type: Optional[ExpenseType] = None
    payment_method: Optional[PaymentMethod] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_categorized: Optional[bool] = None
    is_reconciled: Optional[bool] = None
    search_query: Optional[str] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)

# Made with Bob