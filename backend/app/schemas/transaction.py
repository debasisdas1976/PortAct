from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    """Base transaction schema"""
    transaction_type: TransactionType
    transaction_date: datetime
    quantity: float = Field(default=0.0, ge=0)
    price_per_unit: float = Field(default=0.0, ge=0)
    total_amount: float = Field(..., description="Total transaction amount")
    fees: float = Field(default=0.0, ge=0)
    taxes: float = Field(default=0.0, ge=0)
    description: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    asset_id: int


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""
    transaction_type: Optional[TransactionType] = None
    transaction_date: Optional[datetime] = None
    quantity: Optional[float] = Field(None, ge=0)
    price_per_unit: Optional[float] = Field(None, ge=0)
    total_amount: Optional[float] = None
    fees: Optional[float] = Field(None, ge=0)
    taxes: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class TransactionInDB(TransactionBase):
    """Schema for transaction in database"""
    id: int
    asset_id: int
    statement_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Transaction(TransactionInDB):
    """Schema for transaction response"""
    pass


class TransactionWithAsset(Transaction):
    """Schema for transaction with asset details"""
    asset_name: str
    asset_type: str

# Made with Bob
