"""Fix FK ondelete rules and add missing expenses.category_id FK

Aligns database FK constraints with SQLAlchemy model definitions:

- transactions.asset_id: NO ACTION → CASCADE
- alerts.asset_id: NO ACTION → SET NULL
- assets.demat_account_id: NO ACTION → CASCADE
- asset_snapshots.asset_id: NO ACTION → SET NULL
- expenses.category_id: add missing FK to expense_categories.id

Revision ID: fc01d2e3f4a5
Revises: e3f4a5b6c7d8
Create Date: 2026-02-26

"""
from alembic import op


revision = "fc01d2e3f4a5"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None

# (table, column, ref_table, constraint_name, desired_ondelete)
_FK_FIXES = [
    ("transactions", "asset_id", "assets", "transactions_asset_id_fkey", "CASCADE"),
    ("alerts", "asset_id", "assets", "alerts_asset_id_fkey", "SET NULL"),
    ("assets", "demat_account_id", "demat_accounts", "assets_demat_account_id_fkey", "CASCADE"),
    ("asset_snapshots", "asset_id", "assets", "asset_snapshots_asset_id_fkey", "SET NULL"),
]


def upgrade() -> None:
    # ── Fix existing FK ondelete rules ────────────────────────────────
    for table, col, ref_table, constraint, ondelete in _FK_FIXES:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, ref_table,
            [col], ["id"],
            ondelete=ondelete,
        )

    # ── Add missing expenses.category_id FK ───────────────────────────
    op.create_foreign_key(
        "expenses_category_id_fkey",
        "expenses", "expense_categories",
        ["category_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Remove the new expenses FK
    op.drop_constraint("expenses_category_id_fkey", "expenses", type_="foreignkey")

    # Revert FK ondelete rules to NO ACTION (PG default)
    for table, col, ref_table, constraint, _ondelete in _FK_FIXES:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, ref_table,
            [col], ["id"],
        )
