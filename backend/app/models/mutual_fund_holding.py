from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class MutualFundHolding(Base):
    """Model for storing individual stock holdings within mutual funds"""
    __tablename__ = "mutual_fund_holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)  # Link to mutual fund asset
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Stock identification
    stock_name = Column(String, nullable=False)
    stock_symbol = Column(String, index=True)  # Stock ticker/symbol
    isin = Column(String, index=True)  # ISIN of the stock
    
    # Holding details
    holding_percentage = Column(Float, nullable=False)  # Percentage of fund invested in this stock
    holding_value = Column(Float, default=0.0)  # Calculated value based on user's MF units
    quantity_held = Column(Float, default=0.0)  # Approximate number of shares held through MF
    
    # Stock details
    sector = Column(String)  # Sector of the stock
    industry = Column(String)  # Industry classification
    market_cap = Column(String)  # Large/Mid/Small cap
    
    # Price information
    stock_current_price = Column(Float, default=0.0)  # Current price of the underlying stock
    
    # Metadata
    data_source = Column(String)  # Source of holdings data (e.g., 'mfapi', 'amfi')
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    asset = relationship("Asset", backref="holdings")
    owner = relationship("User", backref="mutual_fund_holdings")
    
    def calculate_holding_value(self, mf_units: float, mf_current_nav: float):
        """
        Calculate the value of this stock holding based on MF units owned
        
        Args:
            mf_units: Number of mutual fund units owned by user
            mf_current_nav: Current NAV of the mutual fund
        """
        total_mf_value = mf_units * mf_current_nav
        self.holding_value = total_mf_value * (self.holding_percentage / 100)
        
        # Calculate approximate quantity of shares
        if self.stock_current_price is not None and self.stock_current_price > 0:
            self.quantity_held = self.holding_value / self.stock_current_price


# Made with Bob