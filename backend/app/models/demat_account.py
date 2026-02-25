from enum import auto
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import UpperStrEnum


class AccountMarket(UpperStrEnum):
    """Whether the demat account trades domestic (INR) or international stocks"""
    DOMESTIC = auto()
    INTERNATIONAL = auto()


class DematAccount(Base):
    """Demat/Trading account model for tracking stock trading accounts"""
    __tablename__ = "demat_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Portfolio association
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    # Account details
    broker_name = Column(String(50), nullable=False, index=True)  # References brokers.name
    account_market = Column(Enum(AccountMarket), nullable=False, default=AccountMarket.DOMESTIC, server_default='DOMESTIC')
    account_id = Column(String, nullable=False)  # Client ID / Account Number
    account_holder_name = Column(String)
    demat_account_number = Column(String)  # DP ID + Client ID
    
    # Balance information
    cash_balance = Column(Float, default=0.0)  # Available cash in trading account (in INR)
    cash_balance_usd = Column(Float)  # Cash balance in USD (for US brokers like Vested, INDMoney)
    currency = Column(String, default='INR')  # Currency of the account (INR or USD)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary trading account
    
    # Additional information
    nickname = Column(String)  # User-defined nickname for the account
    notes = Column(Text)
    last_statement_date = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="demat_accounts")
    portfolio = relationship("Portfolio", foreign_keys=[portfolio_id])
    assets = relationship("Asset", back_populates="demat_account", cascade="all, delete-orphan", passive_deletes=True)

# Made with Bob