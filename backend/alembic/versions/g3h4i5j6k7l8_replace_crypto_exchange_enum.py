"""replace_crypto_exchange_enum_with_master_table

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-02-21 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'g3h4i5j6k7l8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create master table (IF NOT EXISTS for idempotency — create_all may
    #    have already created it)
    conn = op.get_bind()
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'crypto_exchanges'"
    )).scalar()

    if not table_exists:
        op.create_table(
            'crypto_exchanges',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('display_label', sa.String(100), nullable=False),
            sa.Column('exchange_type', sa.String(20), server_default='exchange'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )

    # 2. Seed default exchanges (skip rows that already exist)
    op.execute("""
        INSERT INTO crypto_exchanges (name, display_label, exchange_type, sort_order) VALUES
        ('binance',       'Binance',       'exchange', 1),
        ('coinbase',      'Coinbase',      'exchange', 2),
        ('kraken',        'Kraken',        'exchange', 3),
        ('wazirx',        'WazirX',        'exchange', 4),
        ('coindcx',       'CoinDCX',       'exchange', 5),
        ('zebpay',        'ZebPay',        'exchange', 6),
        ('coinswitch',    'CoinSwitch',    'exchange', 7),
        ('kucoin',        'KuCoin',        'exchange', 8),
        ('bybit',         'Bybit',         'exchange', 9),
        ('okx',           'OKX',           'exchange', 10),
        ('metamask',      'MetaMask',      'wallet',   11),
        ('trust_wallet',  'Trust Wallet',  'wallet',   12),
        ('ledger',        'Ledger',        'wallet',   13),
        ('trezor',        'Trezor',        'wallet',   14),
        ('tangem',        'Tangem',        'wallet',   15),
        ('getbit',        'Getbit',        'exchange', 16),
        ('other',         'Other',         'exchange', 99)
        ON CONFLICT (name) DO NOTHING
    """)

    # 3. Convert exchange_name column from ENUM to VARCHAR (skip if already varchar)
    col_type = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'crypto_accounts' AND column_name = 'exchange_name'
    """)).scalar()

    if col_type == 'USER-DEFINED':
        op.execute("""
            ALTER TABLE crypto_accounts
            ALTER COLUMN exchange_name TYPE VARCHAR(50)
            USING exchange_name::text
        """)

    # 4. Normalize existing data to lowercase
    op.execute("UPDATE crypto_accounts SET exchange_name = LOWER(exchange_name)")

    # 5. Drop the old PostgreSQL enum type
    op.execute("DROP TYPE IF EXISTS cryptoexchange")


def downgrade() -> None:
    # Recreate the enum type
    op.execute("""
        CREATE TYPE cryptoexchange AS ENUM (
            'BINANCE', 'COINBASE', 'KRAKEN', 'WAZIRX', 'COINDCX', 'ZEBPAY',
            'COINSWITCH', 'KUCOIN', 'BYBIT', 'OKX', 'METAMASK', 'TRUST_WALLET',
            'LEDGER', 'TREZOR', 'OTHER', 'TANGEM', 'GETBIT'
        )
    """)

    # Uppercase existing data back
    op.execute("UPDATE crypto_accounts SET exchange_name = UPPER(exchange_name)")

    # Convert column back to enum
    op.execute("""
        ALTER TABLE crypto_accounts
        ALTER COLUMN exchange_name TYPE cryptoexchange
        USING exchange_name::cryptoexchange
    """)

    # Drop the master table
    op.drop_table('crypto_exchanges')
