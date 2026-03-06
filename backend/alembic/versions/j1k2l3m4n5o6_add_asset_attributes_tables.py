"""Add asset_attributes, asset_attribute_values, and asset_attribute_assignments tables

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'j1k2l3m4n5o6'
down_revision = 'i0j1k2l3m4n5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'asset_attributes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('display_label', sa.String(150), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('color', sa.String(20)),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('user_id', 'name', name='uq_asset_attributes_user_name'),
    )

    op.create_table(
        'asset_attribute_values',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('attribute_id', sa.Integer(), sa.ForeignKey('asset_attributes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('color', sa.String(20)),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('attribute_id', 'label', name='uq_attr_value_label'),
    )

    op.create_table(
        'asset_attribute_assignments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('attribute_id', sa.Integer(), sa.ForeignKey('asset_attributes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attribute_value_id', sa.Integer(), sa.ForeignKey('asset_attribute_values.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('asset_id', 'attribute_id', name='uq_asset_attr_assignment'),
    )


def downgrade() -> None:
    op.drop_table('asset_attribute_assignments')
    op.drop_table('asset_attribute_values')
    op.drop_table('asset_attributes')
