from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class TransactionType(str, enum.Enum):
    """Enum for transaction types"""
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    BONUS = "bonus"
    SPLIT = "split"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE = "fee"
    TAX = "tax"


class Transaction(Base):
    """Transaction model for all asset transactions"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Amounts
    quantity = Column(Float, default=0.0)  # Number of units/shares
    price_per_unit = Column(Float, default=0.0)  # Price per unit at transaction
    total_amount = Column(Float, nullable=False)  # Total transaction amount
    fees = Column(Float, default=0.0)  # Transaction fees
    taxes = Column(Float, default=0.0)  # Taxes paid
    
    # Additional information
    description = Column(Text)  # Transaction description
    reference_number = Column(String)  # Bank/broker reference number
    notes = Column(Text)  # User notes
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("Asset", back_populates="transactions")
    statement = relationship("Statement", back_populates="transactions")

# Made with Bob
