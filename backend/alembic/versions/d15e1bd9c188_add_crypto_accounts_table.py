"""add_crypto_accounts_table

Revision ID: d15e1bd9c188
Revises: 6a29a12afd8a
Create Date: 2026-02-15 14:38:50.366166

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd15e1bd9c188'
down_revision = '6a29a12afd8a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE cryptoexchange AS ENUM (
                'binance', 'coinbase', 'kraken', 'wazirx', 'coindcx', 'zebpay',
                'coinswitch', 'kucoin', 'bybit', 'okx', 'metamask', 'trust_wallet',
                'ledger', 'trezor', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create crypto_accounts table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE IF NOT EXISTS crypto_accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            exchange_name cryptoexchange NOT NULL,
            account_id VARCHAR NOT NULL,
            account_holder_name VARCHAR,
            wallet_address VARCHAR,
            cash_balance_usd FLOAT DEFAULT 0.0,
            total_value_usd FLOAT DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE,
            is_primary BOOLEAN DEFAULT FALSE,
            nickname VARCHAR,
            notes TEXT,
            last_sync_date TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    op.create_index('ix_crypto_accounts_exchange_name', 'crypto_accounts', ['exchange_name'])
    
    # Add crypto_account_id to assets table
    op.add_column('assets', sa.Column('crypto_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_assets_crypto_account_id', 'assets', 'crypto_accounts', ['crypto_account_id'], ['id'])


def downgrade() -> None:
    # Remove crypto_account_id from assets table
    op.drop_constraint('fk_assets_crypto_account_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'crypto_account_id')
    
    # Drop crypto_accounts table
    op.drop_index(op.f('ix_crypto_accounts_exchange_name'), table_name='crypto_accounts')
    op.drop_table('crypto_accounts')
    
    # Drop enum type
    op.execute('DROP TYPE cryptoexchange')