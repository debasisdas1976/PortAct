"""add_website_to_master_tables

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-02-21 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'i5j6k7l8m9n0'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add website column to banks (if not already present)
    col_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'banks' AND column_name = 'website'"
    )).scalar()
    if not col_exists:
        op.add_column('banks', sa.Column('website', sa.String(200), nullable=True))

    # Add website column to brokers
    col_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'brokers' AND column_name = 'website'"
    )).scalar()
    if not col_exists:
        op.add_column('brokers', sa.Column('website', sa.String(200), nullable=True))

    # Add website column to crypto_exchanges
    col_exists = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'crypto_exchanges' AND column_name = 'website'"
    )).scalar()
    if not col_exists:
        op.add_column('crypto_exchanges', sa.Column('website', sa.String(200), nullable=True))

    # Seed website URLs for banks
    op.execute("""
        UPDATE banks SET website = CASE name
            WHEN 'icici_bank'          THEN 'icicibank.com'
            WHEN 'hdfc_bank'           THEN 'hdfcbank.com'
            WHEN 'idfc_first_bank'     THEN 'idfcfirstbank.com'
            WHEN 'state_bank_of_india' THEN 'sbi.co.in'
            WHEN 'axis_bank'           THEN 'axisbank.com'
            WHEN 'kotak_mahindra_bank' THEN 'kotak.com'
            WHEN 'yes_bank'            THEN 'yesbank.in'
            WHEN 'scapia'              THEN 'scapia.com'
        END
        WHERE name IN (
            'icici_bank', 'hdfc_bank', 'idfc_first_bank', 'state_bank_of_india',
            'axis_bank', 'kotak_mahindra_bank', 'yes_bank', 'scapia'
        )
    """)

    # Seed website URLs for brokers
    op.execute("""
        UPDATE brokers SET website = CASE name
            WHEN 'zerodha'          THEN 'zerodha.com'
            WHEN 'groww'            THEN 'groww.in'
            WHEN 'upstox'           THEN 'upstox.com'
            WHEN 'angel_one'        THEN 'angelone.in'
            WHEN 'icici_direct'     THEN 'icicidirect.com'
            WHEN 'hdfc_securities'  THEN 'hdfcsec.com'
            WHEN 'kotak_securities' THEN 'kotaksecurities.com'
            WHEN 'axis_direct'      THEN 'axisdirect.in'
            WHEN 'sharekhan'        THEN 'sharekhan.com'
            WHEN 'motilal_oswal'    THEN 'motilaloswal.com'
            WHEN 'iifl_securities'  THEN 'iifl.com'
            WHEN 'indmoney'         THEN 'indmoney.com'
            WHEN 'vested'           THEN 'vested.co.in'
        END
        WHERE name IN (
            'zerodha', 'groww', 'upstox', 'angel_one', 'icici_direct',
            'hdfc_securities', 'kotak_securities', 'axis_direct', 'sharekhan',
            'motilal_oswal', 'iifl_securities', 'indmoney', 'vested'
        )
    """)

    # Seed website URLs for crypto exchanges
    op.execute("""
        UPDATE crypto_exchanges SET website = CASE name
            WHEN 'binance'      THEN 'binance.com'
            WHEN 'coinbase'     THEN 'coinbase.com'
            WHEN 'kraken'       THEN 'kraken.com'
            WHEN 'wazirx'       THEN 'wazirx.com'
            WHEN 'coindcx'      THEN 'coindcx.com'
            WHEN 'zebpay'       THEN 'zebpay.com'
            WHEN 'coinswitch'   THEN 'coinswitch.co'
            WHEN 'kucoin'       THEN 'kucoin.com'
            WHEN 'bybit'        THEN 'bybit.com'
            WHEN 'okx'          THEN 'okx.com'
            WHEN 'metamask'     THEN 'metamask.io'
            WHEN 'trust_wallet' THEN 'trustwallet.com'
            WHEN 'ledger'       THEN 'ledger.com'
            WHEN 'trezor'       THEN 'trezor.io'
            WHEN 'tangem'       THEN 'tangem.com'
            WHEN 'getbit'       THEN 'getbit.com'
        END
        WHERE name IN (
            'binance', 'coinbase', 'kraken', 'wazirx', 'coindcx', 'zebpay',
            'coinswitch', 'kucoin', 'bybit', 'okx', 'metamask', 'trust_wallet',
            'ledger', 'trezor', 'tangem', 'getbit'
        )
    """)


def downgrade() -> None:
    op.drop_column('crypto_exchanges', 'website')
    op.drop_column('brokers', 'website')
    op.drop_column('banks', 'website')
