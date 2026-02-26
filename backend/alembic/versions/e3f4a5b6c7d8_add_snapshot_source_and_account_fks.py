"""Add snapshot_source discriminator and account FK columns to asset_snapshots

Replaces the hack of stuffing fake asset_type strings ('bank_account',
'demat_cash', 'crypto_cash') into AssetSnapshot.  Now each row has a
snapshot_source discriminator and a proper FK to the source entity.

Revision ID: e3f4a5b6c7d8
Revises: de14e6363936
Create Date: 2026-02-26

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'de14e6363936'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add snapshot_source column (defaults to 'asset' for all existing rows)
    op.add_column('asset_snapshots',
        sa.Column('snapshot_source', sa.String(20), nullable=False,
                  server_default='asset'))

    # 2. Add nullable FK columns for account sources
    op.add_column('asset_snapshots',
        sa.Column('bank_account_id', sa.Integer(), nullable=True))
    op.add_column('asset_snapshots',
        sa.Column('demat_account_id', sa.Integer(), nullable=True))
    op.add_column('asset_snapshots',
        sa.Column('crypto_account_id', sa.Integer(), nullable=True))

    # 3. Add FK constraints (SET NULL on delete — preserve historical data)
    op.create_foreign_key(
        'fk_asset_snap_bank_account', 'asset_snapshots', 'bank_accounts',
        ['bank_account_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(
        'fk_asset_snap_demat_account', 'asset_snapshots', 'demat_accounts',
        ['demat_account_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(
        'fk_asset_snap_crypto_account', 'asset_snapshots', 'crypto_accounts',
        ['crypto_account_id'], ['id'], ondelete='SET NULL')

    # 4. Make asset_type nullable (NULL for non-asset sources)
    op.alter_column('asset_snapshots', 'asset_type',
                    existing_type=sa.String(), nullable=True)

    # 5. Backfill snapshot_source from existing fake asset_type strings
    op.execute("""
        UPDATE asset_snapshots
        SET snapshot_source = 'bank_account', asset_type = NULL
        WHERE asset_type IN ('bank_account', 'bank_balance')
    """)
    op.execute("""
        UPDATE asset_snapshots
        SET snapshot_source = 'demat_cash', asset_type = NULL
        WHERE asset_type = 'demat_cash'
    """)
    op.execute("""
        UPDATE asset_snapshots
        SET snapshot_source = 'crypto_cash', asset_type = NULL
        WHERE asset_type = 'crypto_cash'
    """)

    # 6. Add index on snapshot_source for filtered queries
    op.create_index('idx_asset_snap_source', 'asset_snapshots', ['snapshot_source'])


def downgrade() -> None:
    # Restore fake asset_type strings from snapshot_source
    op.execute("""
        UPDATE asset_snapshots SET asset_type = 'bank_account'
        WHERE snapshot_source = 'bank_account' AND asset_type IS NULL
    """)
    op.execute("""
        UPDATE asset_snapshots SET asset_type = 'demat_cash'
        WHERE snapshot_source = 'demat_cash' AND asset_type IS NULL
    """)
    op.execute("""
        UPDATE asset_snapshots SET asset_type = 'crypto_cash'
        WHERE snapshot_source = 'crypto_cash' AND asset_type IS NULL
    """)

    op.drop_index('idx_asset_snap_source', table_name='asset_snapshots')
    op.alter_column('asset_snapshots', 'asset_type',
                    existing_type=sa.String(), nullable=False)
    op.drop_constraint('fk_asset_snap_crypto_account', 'asset_snapshots', type_='foreignkey')
    op.drop_constraint('fk_asset_snap_demat_account', 'asset_snapshots', type_='foreignkey')
    op.drop_constraint('fk_asset_snap_bank_account', 'asset_snapshots', type_='foreignkey')
    op.drop_column('asset_snapshots', 'crypto_account_id')
    op.drop_column('asset_snapshots', 'demat_account_id')
    op.drop_column('asset_snapshots', 'bank_account_id')
    op.drop_column('asset_snapshots', 'snapshot_source')
