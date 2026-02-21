"""add_bank_and_broker_master_tables

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-02-21 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'h4i5j6k7l8m9'
down_revision = 'g3h4i5j6k7l8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Banks ────────────────────────────────────────────────────────────────

    # 1. Create banks table (IF NOT EXISTS for idempotency)
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'banks'"
    )).scalar()

    if not table_exists:
        op.create_table(
            'banks',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('display_label', sa.String(100), nullable=False),
            sa.Column('bank_type', sa.String(20), server_default='commercial'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )

    # 2. Seed default banks
    op.execute("""
        INSERT INTO banks (name, display_label, bank_type, is_active, sort_order) VALUES
        ('icici_bank',          'ICICI Bank',            'commercial',    true, 1),
        ('hdfc_bank',           'HDFC Bank',             'commercial',    true, 2),
        ('idfc_first_bank',     'IDFC First Bank',       'small_finance', true, 3),
        ('state_bank_of_india', 'State Bank of India',   'commercial',    true, 4),
        ('axis_bank',           'Axis Bank',             'commercial',    true, 5),
        ('kotak_mahindra_bank', 'Kotak Mahindra Bank',   'commercial',    true, 6),
        ('yes_bank',            'Yes Bank',              'commercial',    true, 7),
        ('scapia',              'Scapia',                'payment',       true, 8),
        ('other',               'Other',                 'commercial',    true, 99)
        ON CONFLICT (name) DO NOTHING
    """)

    # 3. Convert bank_name column from ENUM to VARCHAR (skip if already varchar)
    col_type = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'bank_accounts' AND column_name = 'bank_name'
    """)).scalar()

    if col_type == 'USER-DEFINED':
        op.execute("""
            ALTER TABLE bank_accounts
            ALTER COLUMN bank_name TYPE VARCHAR(50)
            USING bank_name::text
        """)

    # 4. Normalize existing data to lowercase
    op.execute("UPDATE bank_accounts SET bank_name = LOWER(bank_name)")

    # 5. Drop the old PostgreSQL enum type
    op.execute("DROP TYPE IF EXISTS bankname")

    # ── Brokers ──────────────────────────────────────────────────────────────

    # 6. Create brokers table
    table_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'brokers'"
    )).scalar()

    if not table_exists:
        op.create_table(
            'brokers',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(50), nullable=False, unique=True, index=True),
            sa.Column('display_label', sa.String(100), nullable=False),
            sa.Column('broker_type', sa.String(20), server_default='discount'),
            sa.Column('supported_markets', sa.String(20), server_default='domestic'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )

    # 7. Seed default brokers
    op.execute("""
        INSERT INTO brokers (name, display_label, broker_type, supported_markets, is_active, sort_order) VALUES
        ('zerodha',          'Zerodha',           'discount',      'domestic',       true, 1),
        ('groww',            'Groww',              'discount',      'domestic',       true, 2),
        ('upstox',           'Upstox',             'discount',      'domestic',       true, 3),
        ('angel_one',        'Angel One',          'discount',      'domestic',       true, 4),
        ('icici_direct',     'ICICI Direct',       'full_service',  'domestic',       true, 5),
        ('hdfc_securities',  'HDFC Securities',    'full_service',  'domestic',       true, 6),
        ('kotak_securities', 'Kotak Securities',   'full_service',  'domestic',       true, 7),
        ('axis_direct',      'Axis Direct',        'full_service',  'domestic',       true, 8),
        ('sharekhan',        'Sharekhan',          'full_service',  'domestic',       true, 9),
        ('motilal_oswal',    'Motilal Oswal',      'full_service',  'domestic',       true, 10),
        ('iifl_securities',  'IIFL Securities',    'full_service',  'domestic',       true, 11),
        ('indmoney',         'INDmoney',           'discount',      'international', true, 12),
        ('vested',           'Vested',             'international', 'international', true, 13),
        ('other',            'Other',              'discount',      'domestic',       true, 99)
        ON CONFLICT (name) DO NOTHING
    """)

    # 8. Convert broker_name column from ENUM to VARCHAR (skip if already varchar)
    col_type = conn.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'demat_accounts' AND column_name = 'broker_name'
    """)).scalar()

    if col_type == 'USER-DEFINED':
        op.execute("""
            ALTER TABLE demat_accounts
            ALTER COLUMN broker_name TYPE VARCHAR(50)
            USING broker_name::text
        """)

    # 9. Normalize existing data to lowercase
    op.execute("UPDATE demat_accounts SET broker_name = LOWER(broker_name)")

    # 10. Drop the old PostgreSQL enum type
    op.execute("DROP TYPE IF EXISTS brokername")


def downgrade() -> None:
    # Recreate the BankName enum
    op.execute("""
        CREATE TYPE bankname AS ENUM (
            'icici_bank', 'hdfc_bank', 'idfc_first_bank', 'state_bank_of_india',
            'axis_bank', 'kotak_mahindra_bank', 'yes_bank', 'scapia', 'other'
        )
    """)
    op.execute("UPDATE bank_accounts SET bank_name = LOWER(bank_name)")
    op.execute("""
        ALTER TABLE bank_accounts
        ALTER COLUMN bank_name TYPE bankname
        USING bank_name::bankname
    """)
    op.drop_table('banks')

    # Recreate the BrokerName enum
    op.execute("""
        CREATE TYPE brokername AS ENUM (
            'zerodha', 'groww', 'upstox', 'angel_one', 'icici_direct',
            'hdfc_securities', 'kotak_securities', 'axis_direct', 'sharekhan',
            'motilal_oswal', 'iifl_securities', 'indmoney', 'vested', 'other'
        )
    """)
    op.execute("UPDATE demat_accounts SET broker_name = LOWER(broker_name)")
    op.execute("""
        ALTER TABLE demat_accounts
        ALTER COLUMN broker_name TYPE brokername
        USING broker_name::brokername
    """)
    op.drop_table('brokers')
