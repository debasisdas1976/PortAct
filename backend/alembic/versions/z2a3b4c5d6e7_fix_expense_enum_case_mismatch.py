"""Fix expense enum case mismatch (lowercase -> uppercase)

The expensetype, paymentmethod, and banktype PostgreSQL enums were created
with lowercase labels by migration cf70a5dc799b, but SQLAlchemy's Enum()
uses Python enum .name attributes (UPPERCASE) by default. This mismatch
causes 'invalid input value for enum' errors on any query that filters
by these enum columns.

Revision ID: z2a3b4c5d6e7
Revises: y1z2a3b4c5d6
Create Date: 2026-02-25
"""
from alembic import op

revision = 'z2a3b4c5d6e7'
down_revision = 'y1z2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename expensetype labels: lowercase -> UPPERCASE
    op.execute("ALTER TYPE expensetype RENAME VALUE 'debit' TO 'DEBIT'")
    op.execute("ALTER TYPE expensetype RENAME VALUE 'credit' TO 'CREDIT'")
    op.execute("ALTER TYPE expensetype RENAME VALUE 'transfer' TO 'TRANSFER'")

    # Rename paymentmethod labels: lowercase -> UPPERCASE
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'cash' TO 'CASH'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'debit_card' TO 'DEBIT_CARD'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'credit_card' TO 'CREDIT_CARD'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'upi' TO 'UPI'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'net_banking' TO 'NET_BANKING'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'cheque' TO 'CHEQUE'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'wallet' TO 'WALLET'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'other' TO 'OTHER'")

    # Rename banktype labels: lowercase -> UPPERCASE
    op.execute("ALTER TYPE banktype RENAME VALUE 'savings' TO 'SAVINGS'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'current' TO 'CURRENT'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'credit_card' TO 'CREDIT_CARD'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'fixed_deposit' TO 'FIXED_DEPOSIT'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'recurring_deposit' TO 'RECURRING_DEPOSIT'")


def downgrade() -> None:
    op.execute("ALTER TYPE expensetype RENAME VALUE 'DEBIT' TO 'debit'")
    op.execute("ALTER TYPE expensetype RENAME VALUE 'CREDIT' TO 'credit'")
    op.execute("ALTER TYPE expensetype RENAME VALUE 'TRANSFER' TO 'transfer'")

    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'CASH' TO 'cash'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'DEBIT_CARD' TO 'debit_card'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'CREDIT_CARD' TO 'credit_card'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'UPI' TO 'upi'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'NET_BANKING' TO 'net_banking'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'CHEQUE' TO 'cheque'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'WALLET' TO 'wallet'")
    op.execute("ALTER TYPE paymentmethod RENAME VALUE 'OTHER' TO 'other'")

    op.execute("ALTER TYPE banktype RENAME VALUE 'SAVINGS' TO 'savings'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'CURRENT' TO 'current'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'CREDIT_CARD' TO 'credit_card'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'FIXED_DEPOSIT' TO 'fixed_deposit'")
    op.execute("ALTER TYPE banktype RENAME VALUE 'RECURRING_DEPOSIT' TO 'recurring_deposit'")
