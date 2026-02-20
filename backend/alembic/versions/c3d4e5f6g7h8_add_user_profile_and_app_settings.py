"""add_user_profile_and_app_settings

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-19 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- User profile columns ---
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('state', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('pincode', sa.String(10), nullable=True))

    # --- Employment & salary columns ---
    op.add_column('users', sa.Column('basic_salary', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('da_percentage', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('employer_name', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('date_of_joining', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('pf_employee_pct', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('pf_employer_pct', sa.Float(), nullable=True))

    # --- App settings table (IF NOT EXISTS for idempotency) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            value_type VARCHAR(20) DEFAULT 'string',
            category VARCHAR(50),
            label VARCHAR(200),
            description TEXT,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """)

    # Seed default settings
    op.execute("""
        INSERT INTO app_settings (key, value, value_type, category, label, description) VALUES
        ('price_update_interval_minutes', '30', 'int', 'scheduler', 'Price Update Interval (minutes)', 'How often asset prices are refreshed from market APIs.'),
        ('eod_snapshot_hour', '13', 'int', 'scheduler', 'EOD Snapshot Hour (UTC)', 'Hour (UTC, 0-23) when the daily portfolio snapshot is captured. 13 UTC = 6:30 PM IST.'),
        ('eod_snapshot_minute', '30', 'int', 'scheduler', 'EOD Snapshot Minute', 'Minute (0-59) for the daily portfolio snapshot.'),
        ('news_morning_hour', '9', 'int', 'scheduler', 'Morning News Hour (IST)', 'IST hour (0-23) for the morning AI news alert run.'),
        ('news_evening_hour', '18', 'int', 'scheduler', 'Evening News Hour (IST)', 'IST hour (0-23) for the evening AI news alert run.'),
        ('news_limit_per_user', '10', 'int', 'scheduler', 'News Assets per Run', 'Maximum number of portfolio assets analysed per user in each scheduled news run.'),
        ('ai_news_provider', 'openai', 'string', 'ai', 'AI News Provider', 'Which AI provider to use for generating portfolio news alerts (openai or grok).'),
        ('session_timeout_minutes', '30', 'int', 'general', 'Session Timeout (minutes)', 'Idle time before the user session expires and requires re-login.')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('app_settings')

    op.drop_column('users', 'pf_employer_pct')
    op.drop_column('users', 'pf_employee_pct')
    op.drop_column('users', 'date_of_joining')
    op.drop_column('users', 'employer_name')
    op.drop_column('users', 'da_percentage')
    op.drop_column('users', 'basic_salary')
    op.drop_column('users', 'pincode')
    op.drop_column('users', 'state')
    op.drop_column('users', 'city')
    op.drop_column('users', 'address')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone')
