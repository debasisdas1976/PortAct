from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class StatementStatus(str, enum.Enum):
    """Enum for statement processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class StatementType(str, enum.Enum):
    """Enum for statement types"""
    BANK_STATEMENT = "bank_statement"
    BROKER_STATEMENT = "broker_statement"
    MUTUAL_FUND_STATEMENT = "mutual_fund_statement"
    DEMAT_STATEMENT = "demat_statement"
    CRYPTO_STATEMENT = "crypto_statement"
    INSURANCE_STATEMENT = "insurance_statement"
    PPF_STATEMENT = "ppf_statement"
    VESTED_STATEMENT = "vested_statement"
    INDMONEY_STATEMENT = "indmoney_statement"
    OTHER = "other"


class Statement(Base):
    """Statement model for uploaded financial documents"""
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # File information
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path in storage
    file_size = Column(Integer)  # Size in bytes
    file_type = Column(String)  # MIME type
    
    # Statement details
    statement_type = Column(Enum(StatementType), nullable=False)
    statement_date = Column(DateTime(timezone=True))  # Statement period date
    institution_name = Column(String)  # Bank/broker name
    account_number = Column(String)  # Masked account number
    password = Column(String)  # Password for encrypted PDFs (stored encrypted)
    
    # Processing status
    status = Column(Enum(StatementStatus), default=StatementStatus.UPLOADED)
    processing_started_at = Column(DateTime(timezone=True))
    processing_completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)  # Error details if processing failed
    
    # Extracted data summary
    assets_found = Column(Integer, default=0)
    transactions_found = Column(Integer, default=0)
    
    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="statements")
    assets = relationship("Asset", back_populates="statement", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="statement", cascade="all, delete-orphan")

# Made with Bob
