from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class CryptoAccount(Base):
    """Crypto account/wallet model for tracking cryptocurrency holdings"""
    __tablename__ = "crypto_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Portfolio association
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    # Account details
    exchange_name = Column(String(50), nullable=False, index=True)  # References crypto_exchanges.name
    account_id = Column(String, nullable=False)  # Account ID / Wallet Address
    account_holder_name = Column(String)
    wallet_address = Column(String)  # Public wallet address (for transparency)

    # Balance information (in USD)
    cash_balance_usd = Column(Float, default=0.0)  # Available cash/stablecoin balance in USD
    total_value_usd = Column(Float, default=0.0)  # Total portfolio value in USD

    # Account status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary crypto account

    # Additional information
    nickname = Column(String)  # User-defined nickname for the account
    notes = Column(Text)
    last_sync_date = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="crypto_accounts")
    portfolio = relationship("Portfolio", foreign_keys=[portfolio_id])
    assets = relationship("Asset", back_populates="crypto_account", cascade="all, delete-orphan")
