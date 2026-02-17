from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PortfolioSnapshot(Base):
    """
    Historical snapshot of portfolio value taken at end of day.
    Stores overall portfolio metrics for tracking performance over time.
    """
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False, index=True)
    
    # Portfolio metrics at snapshot time
    total_invested = Column(Float, default=0.0)
    total_current_value = Column(Float, default=0.0)
    total_profit_loss = Column(Float, default=0.0)
    total_profit_loss_percentage = Column(Float, default=0.0)
    total_assets_count = Column(Integer, default=0)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="portfolio_snapshots")
    asset_snapshots = relationship("AssetSnapshot", back_populates="portfolio_snapshot", cascade="all, delete-orphan")
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_user_snapshot_date', 'user_id', 'snapshot_date'),
    )


class AssetSnapshot(Base):
    """
    Historical snapshot of individual asset values.
    Stores detailed metrics for each asset at end of day.
    """
    __tablename__ = "asset_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_snapshot_id = Column(Integer, ForeignKey("portfolio_snapshots.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)  # Nullable to support bank accounts
    snapshot_date = Column(Date, nullable=False, index=True)
    
    # Asset identification (stored for historical reference)
    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_symbol = Column(String)
    
    # Asset metrics at snapshot time
    quantity = Column(Float, default=0.0)
    purchase_price = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    total_invested = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    profit_loss = Column(Float, default=0.0)
    profit_loss_percentage = Column(Float, default=0.0)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    portfolio_snapshot = relationship("PortfolioSnapshot", back_populates="asset_snapshots")
    asset = relationship("Asset")
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_asset_snapshot_date', 'asset_id', 'snapshot_date'),
        Index('idx_portfolio_snapshot', 'portfolio_snapshot_id', 'snapshot_date'),
    )

# Made with Bob