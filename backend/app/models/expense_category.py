from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ExpenseCategory(Base):
    """Expense category model for categorizing transactions"""
    __tablename__ = "expense_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system categories
    
    # Category details
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    icon = Column(String)  # Icon name or emoji
    color = Column(String)  # Hex color code for UI
    
    # Category hierarchy
    parent_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=True)
    
    # Category type
    is_system = Column(Boolean, default=False)  # System-defined categories
    is_income = Column(Boolean, default=False)  # True for income categories
    is_active = Column(Boolean, default=True)
    
    # Keywords for auto-categorization
    keywords = Column(Text)  # Comma-separated keywords for matching
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="expense_categories")
    expenses = relationship("Expense", back_populates="category")
    parent = relationship("ExpenseCategory", remote_side=[id], backref="subcategories")

# Made with Bob