from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class CryptoExchange(str, enum.Enum):
    """Enum for supported crypto exchanges"""
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    WAZIRX = "wazirx"
    COINDCX = "coindcx"
    ZEBPAY = "zebpay"
    COINSWITCH = "coinswitch"
    KUCOIN = "kucoin"
    BYBIT = "bybit"
    OKX = "okx"
    METAMASK = "metamask"
    TRUST_WALLET = "trust_wallet"
    LEDGER = "ledger"
    TREZOR = "trezor"
    TANGEM = "tangem"
    GETBIT = "getbit"
    OTHER = "other"


class CryptoAccount(Base):
    """Crypto account/wallet model for tracking cryptocurrency holdings"""
    __tablename__ = "crypto_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Account details
    exchange_name = Column(Enum(CryptoExchange), nullable=False, index=True)
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
    assets = relationship("Asset", back_populates="crypto_account", cascade="all, delete-orphan")

# Made with Bob