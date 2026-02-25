from enum import auto
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import UpperStrEnum


class AssetType(UpperStrEnum):
    """Enum for different asset types"""
    STOCK = auto()
    US_STOCK = auto()
    EQUITY_MUTUAL_FUND = auto()
    HYBRID_MUTUAL_FUND = auto()
    DEBT_MUTUAL_FUND = auto()
    COMMODITY = auto()
    CRYPTO = auto()
    SAVINGS_ACCOUNT = auto()
    RECURRING_DEPOSIT = auto()
    FIXED_DEPOSIT = auto()
    REAL_ESTATE = auto()
    PPF = auto()
    PF = auto()
    NPS = auto()
    SSY = auto()
    INSURANCE_POLICY = auto()
    GRATUITY = auto()
    CASH = auto()
    NSC = auto()
    KVP = auto()
    SCSS = auto()
    MIS = auto()
    CORPORATE_BOND = auto()
    RBI_BOND = auto()
    TAX_SAVING_BOND = auto()
    REIT = auto()
    INVIT = auto()
    SOVEREIGN_GOLD_BOND = auto()
    ESOP = auto()
    RSU = auto()


class Asset(Base):
    """Universal asset model for all investment types"""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("statements.id"), nullable=True)  # Link to source statement
    demat_account_id = Column(Integer, ForeignKey("demat_accounts.id", ondelete="CASCADE"), nullable=True)  # Link to demat account
    crypto_account_id = Column(Integer, ForeignKey("crypto_accounts.id"), nullable=True)  # Link to crypto account
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)  # Link to portfolio

    # Asset identification
    asset_type = Column(Enum(AssetType), nullable=False, index=True)
    name = Column(String, nullable=False)  # Stock name, property address, etc.
    symbol = Column(String, index=True)  # Ticker symbol, ISIN, etc. (for display)
    api_symbol = Column(String, index=True)  # Symbol used for API price fetching (can be different from display symbol)
    isin = Column(String, index=True)  # ISIN code for stocks, commodities, and mutual funds
    
    # Account information
    account_id = Column(String, index=True)  # Account/Client ID from broker
    broker_name = Column(String)  # Broker/Institution name (e.g., Zerodha, Groww)
    account_holder_name = Column(String)  # Name of the account holder
    
    # Quantity and value
    quantity = Column(Float, default=0.0)  # Shares, units, grams, etc.
    purchase_price = Column(Float, default=0.0)  # Average purchase price per unit
    current_price = Column(Float, default=0.0)  # Current market price per unit
    total_invested = Column(Float, default=0.0)  # Total amount invested
    current_value = Column(Float, default=0.0)  # Current total value
    
    # Performance metrics
    profit_loss = Column(Float, default=0.0)  # Absolute profit/loss
    profit_loss_percentage = Column(Float, default=0.0)  # Percentage profit/loss
    
    # Asset-specific details (stored as JSON for flexibility)
    details = Column(JSON, default={})
    # Examples:
    # For stocks: {"exchange": "NSE", "sector": "IT", "market_cap": "Large"}
    # For FD: {"bank_name": "HDFC", "maturity_date": "2025-12-31", "interest_rate": 7.5}
    # For real estate: {"property_type": "Apartment", "area_sqft": 1200, "location": "Mumbai"}
    # For crypto: {"blockchain": "Ethereum", "wallet_address": "0x..."}
    
    # Status and metadata
    is_active = Column(Boolean, default=True)  # Active or sold/closed
    notes = Column(Text)  # User notes
    
    # Price update tracking
    price_update_failed = Column(Boolean, default=False)  # Flag for failed price updates
    last_price_update = Column(DateTime(timezone=True))  # Last successful price update
    price_update_error = Column(Text)  # Error message from last failed update
    
    # Timestamps
    purchase_date = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="assets")
    statement = relationship("Statement", back_populates="assets")
    demat_account = relationship("DematAccount", back_populates="assets")
    crypto_account = relationship("CryptoAccount", back_populates="assets")
    portfolio = relationship("Portfolio", back_populates="assets")
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan", passive_deletes=True)
    
    def calculate_metrics(self):
        """Calculate profit/loss metrics"""
        if self.total_invested > 0:
            self.current_value = self.quantity * self.current_price
            self.profit_loss = self.current_value - self.total_invested
            self.profit_loss_percentage = (self.profit_loss / self.total_invested) * 100
        else:
            self.profit_loss = 0.0
            self.profit_loss_percentage = 0.0

# Made with Bob
