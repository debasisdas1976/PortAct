from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MutualFundHoldingBase(BaseModel):
    """Base schema for mutual fund holdings"""
    stock_name: str = Field(..., min_length=1, max_length=200)
    stock_symbol: Optional[str] = Field(None, max_length=50)
    isin: Optional[str] = Field(None, max_length=50)
    holding_percentage: float = Field(..., ge=0, le=100)
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[str] = None


class MutualFundHoldingCreate(MutualFundHoldingBase):
    """Schema for creating a mutual fund holding"""
    asset_id: int
    stock_current_price: Optional[float] = 0.0
    data_source: Optional[str] = None


class MutualFundHoldingUpdate(BaseModel):
    """Schema for updating a mutual fund holding"""
    stock_name: Optional[str] = Field(None, min_length=1, max_length=200)
    stock_symbol: Optional[str] = Field(None, max_length=50)
    isin: Optional[str] = Field(None, max_length=50)
    holding_percentage: Optional[float] = Field(None, ge=0, le=100)
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[str] = None
    stock_current_price: Optional[float] = None


class MutualFundHoldingInDB(MutualFundHoldingBase):
    """Schema for mutual fund holding in database"""
    id: int
    asset_id: int
    user_id: int
    holding_value: float
    quantity_held: float
    stock_current_price: float
    data_source: Optional[str] = None
    last_updated: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class MutualFundHolding(MutualFundHoldingInDB):
    """Schema for mutual fund holding response"""
    pass


class MutualFundWithHoldings(BaseModel):
    """Schema for mutual fund with its holdings"""
    asset_id: int
    fund_name: str
    fund_symbol: Optional[str] = None
    isin: Optional[str] = None
    units_held: float
    current_nav: float
    total_value: float
    holdings: list[MutualFundHolding]
    holdings_count: int
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HoldingsDashboardStock(BaseModel):
    """Schema for aggregated stock holdings across MFs and direct holdings"""
    stock_name: str
    stock_symbol: Optional[str] = None
    isin: Optional[str] = None
    
    # Direct holdings
    direct_quantity: float = 0.0
    direct_value: float = 0.0
    direct_invested: float = 0.0
    
    # Mutual fund holdings
    mf_quantity: float = 0.0  # Approximate quantity through MFs
    mf_value: float = 0.0  # Total value through MFs
    mf_holding_percentage: float = 0.0  # Average holding percentage across MFs
    mf_count: int = 0  # Number of MFs holding this stock
    mutual_funds: list[str] = []  # Names of MFs holding this stock
    
    # Combined totals
    total_quantity: float = 0.0
    total_value: float = 0.0
    
    # Stock details
    current_price: float = 0.0
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[str] = None
    
    # Performance (for direct holdings)
    profit_loss: float = 0.0
    profit_loss_percentage: float = 0.0


class HoldingsDashboardResponse(BaseModel):
    """Schema for holdings dashboard response"""
    stocks: list[HoldingsDashboardStock]
    summary: dict
    last_updated: datetime
    
    class Config:
        from_attributes = True


class FundMappingPreview(BaseModel):
    """Schema for fund mapping preview before import"""
    fund_name_from_excel: str
    matched_asset_id: Optional[int] = None
    matched_asset_name: Optional[str] = None
    similarity_score: float
    holdings_count: int
    can_auto_import: bool
    needs_confirmation: bool
    all_matched_asset_ids: List[int] = []  # All matching asset IDs (for multiple matches)
    match_count: int = 0  # Number of matching funds found


class FundMappingConfirmation(BaseModel):
    """Schema for user to confirm/modify fund mappings"""
    fund_name_from_excel: str
    asset_ids: list[int]  # List of asset IDs to update (can be multiple for same fund)


class UploadPreviewResponse(BaseModel):
    """Schema for upload preview response"""
    temp_file_id: str  # Temporary ID to reference the uploaded file
    total_funds_in_file: int
    total_funds_in_portfolio: int
    mappings: List[FundMappingPreview]
    message: str


class ConfirmImportRequest(BaseModel):
    """Schema for confirming import with mappings"""
    temp_file_id: str
    confirmed_mappings: List[FundMappingConfirmation]


# Made with Bob