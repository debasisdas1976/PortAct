from enum import auto
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import UpperStrEnum, LowerEnum


class ExpenseType(UpperStrEnum):
    """Enum for expense transaction types"""
    DEBIT = auto()  # Money out
    CREDIT = auto()  # Money in
    TRANSFER = auto()  # Transfer between accounts


class PaymentMethod(UpperStrEnum):
    """Enum for payment methods"""
    CASH = auto()
    DEBIT_CARD = auto()
    CREDIT_CARD = auto()
    UPI = auto()
    NET_BANKING = auto()
    CHEQUE = auto()
    WALLET = auto()
    OTHER = auto()


class Expense(Base):
    """Expense model for tracking all financial transactions from bank statements"""
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)

    # Portfolio association
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    
    # Transaction details
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    transaction_type = Column(LowerEnum(ExpenseType), nullable=False, index=True)
    
    # Amount information
    amount = Column(Float, nullable=False)  # Transaction amount
    balance_after = Column(Float)  # Account balance after transaction
    
    # Transaction description
    description = Column(Text, nullable=False)  # Original transaction description
    merchant_name = Column(String)  # Extracted merchant name
    reference_number = Column(String)  # Bank reference/transaction ID
    
    # Payment details
    payment_method = Column(LowerEnum(PaymentMethod), nullable=True)
    
    # Categorization
    is_categorized = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)  # Recurring transaction
    is_split = Column(Boolean, default=False)  # Split transaction
    
    # Additional information
    location = Column(String)  # Transaction location if available
    notes = Column(Text)  # User notes
    tags = Column(String)  # Comma-separated tags
    
    # Reconciliation
    is_reconciled = Column(Boolean, default=False)
    reconciled_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    bank_account = relationship("BankAccount", back_populates="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")
    statement = relationship("Statement", back_populates="expenses")
    portfolio = relationship("Portfolio", foreign_keys=[portfolio_id])

# Made with Bob