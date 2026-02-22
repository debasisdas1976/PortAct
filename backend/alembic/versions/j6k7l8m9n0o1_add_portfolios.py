"""add_portfolios

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2026-02-21 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'j6k7l8m9n0o1'
down_revision = 'i5j6k7l8m9n0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop orphaned table from a previous failed attempt (if exists)
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS portfolios CASCADE"))

    # 1. Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_portfolios_id'), 'portfolios', ['id'])
    op.create_index('idx_portfolios_user', 'portfolios', ['user_id'])

    # 2. Add portfolio_id column to assets (nullable)
    op.add_column('assets', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_assets_portfolio_id', 'assets', 'portfolios', ['portfolio_id'], ['id'])
    op.create_index('idx_assets_portfolio', 'assets', ['portfolio_id'])

    # 3. Data migration: create a default portfolio per user and assign all assets
    conn = op.get_bind()

    all_users = conn.execute(sa.text("SELECT id FROM users")).fetchall()

    for (uid,) in all_users:
        result = conn.execute(
            sa.text(
                "INSERT INTO portfolios (user_id, name, is_default, is_active) "
                "VALUES (:uid, 'Default', true, true) RETURNING id"
            ),
            {"uid": uid},
        )
        portfolio_id = result.fetchone()[0]

        conn.execute(
            sa.text("UPDATE assets SET portfolio_id = :pid WHERE user_id = :uid"),
            {"pid": portfolio_id, "uid": uid},
        )


def downgrade() -> None:
    op.drop_index('idx_assets_portfolio', table_name='assets')
    op.drop_constraint('fk_assets_portfolio_id', 'assets', type_='foreignkey')
    op.drop_column('assets', 'portfolio_id')
    op.drop_index('idx_portfolios_user', table_name='portfolios')
    op.drop_index(op.f('ix_portfolios_id'), table_name='portfolios')
    op.drop_table('portfolios')
