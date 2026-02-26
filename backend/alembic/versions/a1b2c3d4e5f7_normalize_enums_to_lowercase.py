"""Normalize all PostgreSQL enum labels to lowercase

All 10 UpperStrEnum-based PostgreSQL types had UPPERCASE labels (e.g. 'STOCK')
while the asset_type_master table, seed data, and frontend all use lowercase
('stock'). This caused persistent case-mismatch bugs.

Uses the VARCHAR-cast approach because some enum types (notably assettype) have
duplicate labels in both cases due to earlier migrations, which prevents using
ALTER TYPE ... RENAME VALUE.

Revision ID: a1b2c3d4e5f7
Revises: z2a3b4c5d6e7
Create Date: 2026-02-26

"""
from alembic import op

revision = 'a1b2c3d4e5f7'
down_revision = 'z2a3b4c5d6e7'
branch_labels = None
depends_on = None

# (pg_type_name, [(table, column), ...], [lowercase labels])
ENUM_SPECS = [
    ("assettype", [("assets", "asset_type")], [
        "stock", "us_stock", "equity_mutual_fund", "hybrid_mutual_fund",
        "debt_mutual_fund", "commodity", "crypto", "savings_account",
        "recurring_deposit", "fixed_deposit", "real_estate", "ppf", "pf",
        "nps", "ssy", "insurance_policy", "gratuity", "cash", "nsc",
        "kvp", "scss", "mis", "corporate_bond", "rbi_bond",
        "tax_saving_bond", "reit", "invit", "sovereign_gold_bond",
        "esop", "rsu",
    ]),
    ("transactiontype", [("transactions", "transaction_type")], [
        "buy", "sell", "deposit", "withdrawal", "dividend", "interest",
        "bonus", "split", "transfer_in", "transfer_out", "fee", "tax",
    ]),
    ("banktype", [("bank_accounts", "account_type")], [
        "savings", "current", "credit_card", "fixed_deposit",
        "recurring_deposit",
    ]),
    ("expensetype", [("expenses", "transaction_type")], [
        "debit", "credit", "transfer",
    ]),
    ("paymentmethod", [("expenses", "payment_method")], [
        "cash", "debit_card", "credit_card", "upi", "net_banking",
        "cheque", "wallet", "other",
    ]),
    ("statementstatus", [("statements", "status")], [
        "uploaded", "processing", "processed", "failed",
    ]),
    ("statementtype", [("statements", "statement_type")], [
        "bank_statement", "broker_statement", "mutual_fund_statement",
        "demat_statement", "crypto_statement", "insurance_statement",
        "ppf_statement", "pf_statement", "ssy_statement", "nps_statement",
        "vested_statement", "indmoney_statement", "other",
    ]),
    ("alertseverity", [("alerts", "severity")], [
        "info", "warning", "critical",
    ]),
    ("alerttype", [("alerts", "alert_type")], [
        "price_change", "news_event", "dividend_announcement",
        "earnings_report", "regulatory_change", "maturity_reminder",
        "rebalance_suggestion", "market_volatility",
    ]),
    ("accountmarket", [("demat_accounts", "account_market")], [
        "domestic", "international",
    ]),
]


def upgrade() -> None:
    # Drop server_default that depends on the accountmarket enum type
    op.execute(
        "ALTER TABLE demat_accounts "
        "ALTER COLUMN account_market DROP DEFAULT"
    )

    for pg_type, columns, labels in ENUM_SPECS:
        # Step 1: Convert columns to VARCHAR, lowercasing data
        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} "
                f"TYPE VARCHAR USING LOWER({col}::text)"
            )

        # Step 2: Drop the old enum type (may have duplicate upper/lower labels)
        op.execute(f"DROP TYPE {pg_type}")

        # Step 3: Recreate with lowercase-only labels
        labels_sql = ", ".join(f"'{label}'" for label in labels)
        op.execute(f"CREATE TYPE {pg_type} AS ENUM ({labels_sql})")

        # Step 4: Convert columns back to the enum type
        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} "
                f"TYPE {pg_type} USING {col}::{pg_type}"
            )

    # Fix AssetSnapshot.asset_type (plain String column, not an enum)
    op.execute(
        "UPDATE asset_snapshots SET asset_type = LOWER(asset_type) "
        "WHERE asset_type != LOWER(asset_type)"
    )

    # Re-add server_default with lowercase value
    op.execute(
        "ALTER TABLE demat_accounts "
        "ALTER COLUMN account_market SET DEFAULT 'domestic'::accountmarket"
    )


def downgrade() -> None:
    # Reverse: recreate enum types with UPPERCASE labels
    for pg_type, columns, labels in ENUM_SPECS:
        upper_labels = [label.upper() for label in labels]

        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} "
                f"TYPE VARCHAR USING UPPER({col}::text)"
            )

        op.execute(f"DROP TYPE {pg_type}")

        labels_sql = ", ".join(f"'{label}'" for label in upper_labels)
        op.execute(f"CREATE TYPE {pg_type} AS ENUM ({labels_sql})")

        for table, col in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {col} "
                f"TYPE {pg_type} USING {col}::{pg_type}"
            )

    # Revert AssetSnapshot.asset_type back to UPPERCASE
    op.execute(
        "UPDATE asset_snapshots SET asset_type = UPPER(asset_type) "
        "WHERE asset_type NOT IN ('bank_account', 'demat_cash', 'crypto_cash') "
        "AND asset_type != UPPER(asset_type)"
    )

    # Revert server_default
    op.execute(
        "ALTER TABLE demat_accounts "
        "ALTER COLUMN account_market SET DEFAULT 'DOMESTIC'::accountmarket"
    )
