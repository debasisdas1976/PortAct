from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.statement import StatementStatus, StatementType


class StatementBase(BaseModel):
    """Base statement schema"""
    statement_type: StatementType
    statement_date: Optional[datetime] = None
    institution_name: Optional[str] = None
    account_number: Optional[str] = None
    password: Optional[str] = None


class StatementCreate(StatementBase):
    """Schema for creating a statement"""
    filename: str
    file_path: str
    file_size: int
    file_type: str


class StatementUpdate(BaseModel):
    """Schema for updating a statement"""
    statement_type: Optional[StatementType] = None
    statement_date: Optional[datetime] = None
    institution_name: Optional[str] = None
    account_number: Optional[str] = None
    status: Optional[StatementStatus] = None


class StatementInDB(StatementBase):
    """Schema for statement in database"""
    id: int
    user_id: int
    filename: str
    file_path: str
    file_size: int
    file_type: str
    status: StatementStatus
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    assets_found: int
    transactions_found: int
    uploaded_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Statement(StatementInDB):
    """Schema for statement response"""
    pass


class StatementUploadResponse(BaseModel):
    """Schema for statement upload response"""
    statement_id: int
    filename: str
    status: str
    message: str

class UploadConfig(BaseModel):
    """Configuration for uploading a statement to an existing account"""
    endpoint: str
    pre_filled: Dict[str, Any] = {}
    fields_needed: List[str] = ["file"]
    accepts: str = ".pdf,.csv,.xlsx"


class AccountItem(BaseModel):
    """A single account entry in the grouped accounts response"""
    account_source: str  # "demat_account", "bank_account", "crypto_account", "asset"
    account_id: int
    asset_type: Optional[str] = None
    display_name: str
    institution_name: Optional[str] = None
    sub_info: Optional[str] = None
    last_statement_date: Optional[datetime] = None
    upload_config: UploadConfig


class AccountGroup(BaseModel):
    """A group of accounts of the same type"""
    group_type: str
    display_name: str
    accounts: List[AccountItem]


class PortfolioAccountsResponse(BaseModel):
    """Response for GET /statements/accounts"""
    groups: List[AccountGroup]
