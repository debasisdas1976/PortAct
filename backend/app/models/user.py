from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User model for authentication and profile"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Profile fields
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)

    # Employment & salary fields
    is_employed = Column(Boolean, nullable=True, default=True)
    basic_salary = Column(Float, nullable=True)
    da_percentage = Column(Float, nullable=True, default=0)
    employer_name = Column(String(200), nullable=True)
    date_of_joining = Column(Date, nullable=True)
    pf_employee_pct = Column(Float, nullable=True, default=12)
    pf_employer_pct = Column(Float, nullable=True, default=12)
    
    # Relationships
    assets = relationship("Asset", back_populates="owner", cascade="all, delete-orphan")
    statements = relationship("Statement", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    bank_accounts = relationship("BankAccount", back_populates="user", cascade="all, delete-orphan")
    demat_accounts = relationship("DematAccount", back_populates="user", cascade="all, delete-orphan")
    crypto_accounts = relationship("CryptoAccount", back_populates="user", cascade="all, delete-orphan")
    expense_categories = relationship("ExpenseCategory", back_populates="user", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="owner", cascade="all, delete-orphan")

# Made with Bob
