from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class BankType(str, enum.Enum):
    """Enum for bank account types"""
    SAVINGS = "savings"
    CURRENT = "current"
    CREDIT_CARD = "credit_card"
    FIXED_DEPOSIT = "fixed_deposit"
    RECURRING_DEPOSIT = "recurring_deposit"


class BankAccount(Base):
    """Bank account model for tracking bank accounts and balances"""
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Account details
    bank_name = Column(String(50), nullable=False, index=True)  # References banks.name
    account_type = Column(Enum(BankType), nullable=False, index=True)
    account_number = Column(String, nullable=False)  # Masked or full account number
    account_holder_name = Column(String)
    ifsc_code = Column(String)
    branch_name = Column(String)
    
    # Balance information
    current_balance = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)  # For credit cards: available limit
    credit_limit = Column(Float, default=0.0)  # For credit cards
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary account for the user
    
    # Additional information
    nickname = Column(String)  # User-defined nickname for the account
    notes = Column(Text)
    last_statement_date = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="bank_accounts")
    expenses = relationship("Expense", back_populates="bank_account", cascade="all, delete-orphan")

# Made with Bob