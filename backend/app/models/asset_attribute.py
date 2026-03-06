from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class AssetAttribute(Base):
    """User-defined custom attribute for assets (e.g., Risk Profile, Bucket Strategy)."""
    __tablename__ = "asset_attributes"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_asset_attributes_user_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False, index=True)
    display_label = Column(String(150), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="asset_attributes")
    values = relationship(
        "AssetAttributeValue",
        back_populates="attribute",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AssetAttributeValue.sort_order",
    )
    assignments = relationship(
        "AssetAttributeAssignment",
        back_populates="attribute",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AssetAttributeValue(Base):
    """An allowed value for a custom attribute (e.g., 'High Risk')."""
    __tablename__ = "asset_attribute_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "label", name="uq_attr_value_label"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer, ForeignKey("asset_attributes.id", ondelete="CASCADE"), nullable=False)
    label = Column(String(100), nullable=False)
    color = Column(String(20))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    attribute = relationship("AssetAttribute", back_populates="values")
    assignments = relationship(
        "AssetAttributeAssignment",
        back_populates="attribute_value",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AssetAttributeAssignment(Base):
    """Links an asset to exactly one value per attribute."""
    __tablename__ = "asset_attribute_assignments"
    __table_args__ = (
        UniqueConstraint("asset_id", "attribute_id", name="uq_asset_attr_assignment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_id = Column(Integer, ForeignKey("asset_attributes.id", ondelete="CASCADE"), nullable=False)
    attribute_value_id = Column(Integer, ForeignKey("asset_attribute_values.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("Asset", back_populates="attribute_assignments")
    attribute = relationship("AssetAttribute", back_populates="assignments")
    attribute_value = relationship("AssetAttributeValue", back_populates="assignments")
