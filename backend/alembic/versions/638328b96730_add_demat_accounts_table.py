"""add_demat_accounts_table

Revision ID: 638328b96730
Revises: 6c64e6666c62
Create Date: 2026-02-15 13:14:19.785066

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '638328b96730'
down_revision = '6c64e6666c62'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create demat_accounts table
    op.create_table(
        'demat_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('broker_name', sa.String(50), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('account_holder_name', sa.String(), nullable=True),
        sa.Column('demat_account_number', sa.String(), nullable=True),
        sa.Column('cash_balance', sa.Float(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('nickname', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_statement_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_demat_accounts_id'), 'demat_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_demat_accounts_broker_name'), 'demat_accounts', ['broker_name'], unique=False)

    # Add demat_account_id FK column to assets
    op.add_column('assets', sa.Column('demat_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'assets', 'demat_accounts', ['demat_account_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'assets', type_='foreignkey')
    op.drop_column('assets', 'demat_account_id')

    op.drop_index(op.f('ix_demat_accounts_broker_name'), table_name='demat_accounts')
    op.drop_index(op.f('ix_demat_accounts_id'), table_name='demat_accounts')
    op.drop_table('demat_accounts')
