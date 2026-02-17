"""
Fix asset_id column to be nullable in asset_snapshots table
"""
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE asset_snapshots ALTER COLUMN asset_id DROP NOT NULL'))
    conn.commit()
    print("✅ Successfully made asset_id nullable in asset_snapshots table")

# Made with Bob
