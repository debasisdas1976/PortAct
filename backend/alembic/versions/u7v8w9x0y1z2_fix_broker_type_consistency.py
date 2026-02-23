"""Fix broker_type consistency: INDmoney discount->international

Revision ID: u7v8w9x0y1z2
Revises: t6u7v8w9x0y1
Create Date: 2026-02-23 18:00:00.000000

"""
from alembic import op


revision = 'u7v8w9x0y1z2'
down_revision = 't6u7v8w9x0y1'
branch_labels = None
depends_on = None


def upgrade():
    # Fix INDmoney: it serves international markets, so broker_type should be
    # 'international' rather than 'discount'
    op.execute("""
        UPDATE brokers
        SET broker_type = 'international'
        WHERE name = 'indmoney' AND broker_type = 'discount'
    """)


def downgrade():
    op.execute("""
        UPDATE brokers
        SET broker_type = 'discount'
        WHERE name = 'indmoney' AND broker_type = 'international'
    """)
