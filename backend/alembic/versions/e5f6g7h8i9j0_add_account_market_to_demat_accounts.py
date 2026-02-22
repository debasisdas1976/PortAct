"""add_account_market_to_demat_accounts

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the enum type idempotently (may already exist if create_all ran before migrations)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE accountmarket AS ENUM ('DOMESTIC', 'INTERNATIONAL');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # Add nullable column first, then backfill, then set NOT NULL
    op.add_column(
        'demat_accounts',
        sa.Column('account_market', sa.Enum('DOMESTIC', 'INTERNATIONAL', name='accountmarket', create_type=False), nullable=True)
    )

    # Set default for all existing rows
    op.execute("UPDATE demat_accounts SET account_market = 'DOMESTIC'::accountmarket")

    # Set Vested/INDMoney accounts to international
    op.execute(
        "UPDATE demat_accounts SET account_market = 'INTERNATIONAL'::accountmarket "
        "WHERE broker_name::text IN ('VESTED', 'INDMONEY')"
    )

    # Now make it NOT NULL with a default
    op.alter_column('demat_accounts', 'account_market', nullable=False,
                     server_default=sa.text("'DOMESTIC'::accountmarket"))


def downgrade() -> None:
    op.drop_column('demat_accounts', 'account_market')
    op.execute("DROP TYPE IF EXISTS accountmarket")
