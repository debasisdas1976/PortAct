"""add_bank_accounts_and_expense_tracking

Revision ID: cf70a5dc799b
Revises: 92808804c3ea
Create Date: 2026-02-13 22:57:09.052370

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'cf70a5dc799b'
down_revision = '92808804c3ea'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums idempotently (may already exist if create_all ran before migrations)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE banktype AS ENUM ('savings', 'current', 'credit_card', 'fixed_deposit', 'recurring_deposit');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE expensetype AS ENUM ('debit', 'credit', 'transfer');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod AS ENUM ('cash', 'debit_card', 'credit_card', 'upi', 'net_banking', 'cheque', 'wallet', 'other');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # Create bank_accounts table (use postgresql.ENUM with create_type=False since types already exist)
    op.create_table(
        'bank_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bank_name', sa.String(50), nullable=False),
        sa.Column('account_type', postgresql.ENUM('savings', 'current', 'credit_card',
                  'fixed_deposit', 'recurring_deposit', name='banktype',
                  create_type=False), nullable=False),
        sa.Column('account_number', sa.String(), nullable=False),
        sa.Column('account_holder_name', sa.String(), nullable=True),
        sa.Column('ifsc_code', sa.String(), nullable=True),
        sa.Column('branch_name', sa.String(), nullable=True),
        sa.Column('current_balance', sa.Float(), nullable=True, server_default='0'),
        sa.Column('available_balance', sa.Float(), nullable=True, server_default='0'),
        sa.Column('credit_limit', sa.Float(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_primary', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('nickname', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_statement_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bank_accounts_id'), 'bank_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_bank_accounts_bank_name'), 'bank_accounts', ['bank_name'], unique=False)
    op.create_index(op.f('ix_bank_accounts_account_type'), 'bank_accounts', ['account_type'], unique=False)

    # Create expenses table
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bank_account_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('statement_id', sa.Integer(), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transaction_type', postgresql.ENUM('debit', 'credit', 'transfer',
                  name='expensetype', create_type=False), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('balance_after', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('merchant_name', sa.String(), nullable=True),
        sa.Column('reference_number', sa.String(), nullable=True),
        sa.Column('payment_method', postgresql.ENUM('cash', 'debit_card', 'credit_card',
                  'upi', 'net_banking', 'cheque', 'wallet', 'other',
                  name='paymentmethod', create_type=False), nullable=True),
        sa.Column('is_categorized', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_recurring', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_split', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('is_reconciled', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id']),
        sa.ForeignKeyConstraint(['statement_id'], ['statements.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)
    op.create_index(op.f('ix_expenses_transaction_date'), 'expenses', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_expenses_transaction_type'), 'expenses', ['transaction_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_expenses_transaction_type'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_transaction_date'), table_name='expenses')
    op.drop_index(op.f('ix_expenses_id'), table_name='expenses')
    op.drop_table('expenses')

    op.drop_index(op.f('ix_bank_accounts_account_type'), table_name='bank_accounts')
    op.drop_index(op.f('ix_bank_accounts_bank_name'), table_name='bank_accounts')
    op.drop_index(op.f('ix_bank_accounts_id'), table_name='bank_accounts')
    op.drop_table('bank_accounts')

    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS expensetype")
    op.execute("DROP TYPE IF EXISTS banktype")
