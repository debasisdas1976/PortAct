"""Add has_parser and supported_formats to master tables

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-02-23 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 't6u7v8w9x0y1'
down_revision = 's5t6u7v8w9x0'
branch_labels = None
depends_on = None


def _add_columns_if_missing(table_name: str, conn):
    """Add has_parser and supported_formats columns to a table if they don't exist."""
    for col_name, col_type, default in [
        ('has_parser', sa.Boolean(), 'false'),
        ('supported_formats', sa.String(100), None),
    ]:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ), {'table': table_name, 'col': col_name}).scalar()
        if not exists:
            op.add_column(
                table_name,
                sa.Column(col_name, col_type, server_default=default, nullable=True),
            )


def upgrade() -> None:
    conn = op.get_bind()

    # ── Add columns to all 4 master tables ────────────────────────────────
    for table in ('brokers', 'banks', 'crypto_exchanges', 'institutions'):
        _add_columns_if_missing(table, conn)

    # ── Insert aggregator/depository brokers that have parsers ────────────
    op.execute("""
        INSERT INTO brokers (name, display_label, broker_type, supported_markets, website, has_parser, supported_formats, is_active, sort_order) VALUES
        ('nsdl_cas',   'NSDL CAS (Consolidated)',  'aggregator', 'domestic', 'nsdl.co.in',      true, 'pdf', true, 20),
        ('cdsl_cas',   'CDSL CAS (Consolidated)',   'aggregator', 'domestic', 'cdslindia.com',   true, 'pdf', true, 21),
        ('mf_central', 'MF Central CAS',            'aggregator', 'domestic', 'mfcentral.com',   true, 'pdf', true, 22),
        ('direct_mf',  'Direct MF / Kuvera',        'aggregator', 'domestic', 'kuvera.in',       true, 'pdf', true, 23)
        ON CONFLICT (name) DO UPDATE SET
            has_parser = EXCLUDED.has_parser,
            supported_formats = EXCLUDED.supported_formats
    """)

    # ── Seed has_parser / supported_formats for brokers ───────────────────
    # Brokers with CSV/Excel parsers
    op.execute("""
        UPDATE brokers SET has_parser = true, supported_formats = 'csv,xlsx'
        WHERE name IN ('zerodha', 'groww')
    """)
    op.execute("""
        UPDATE brokers SET has_parser = true, supported_formats = 'csv'
        WHERE name IN ('icici_direct', 'vested', 'indmoney')
    """)

    # Ensure remaining brokers without parsers are marked accordingly
    op.execute("""
        UPDATE brokers SET has_parser = false, supported_formats = NULL
        WHERE has_parser IS NULL OR (has_parser = false AND supported_formats IS NOT NULL)
    """)

    # ── Seed has_parser / supported_formats for banks ─────────────────────
    op.execute("""
        UPDATE banks SET has_parser = true, supported_formats = 'pdf'
        WHERE name IN (
            'icici_bank', 'hdfc_bank', 'idfc_first_bank',
            'state_bank_of_india', 'kotak_mahindra_bank', 'axis_bank'
        )
    """)
    op.execute("""
        UPDATE banks SET has_parser = false, supported_formats = NULL
        WHERE has_parser IS NULL
    """)

    # ── Crypto exchanges and institutions: no parsers yet ─────────────────
    op.execute("UPDATE crypto_exchanges SET has_parser = false WHERE has_parser IS NULL")
    op.execute("UPDATE institutions SET has_parser = false WHERE has_parser IS NULL")


def downgrade() -> None:
    for table in ('institutions', 'crypto_exchanges', 'banks', 'brokers'):
        op.drop_column(table, 'supported_formats')
        op.drop_column(table, 'has_parser')

    # Remove aggregator brokers added by this migration
    op.execute("""
        DELETE FROM brokers
        WHERE name IN ('nsdl_cas', 'cdsl_cas', 'mf_central', 'direct_mf')
    """)
