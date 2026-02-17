"""
Script to mark the portfolio snapshots migration as applied
without actually running it (since tables already exist)
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def mark_migration_applied():
    """Mark the migration as applied in alembic_version table"""
    engine = create_engine(settings.DATABASE_URL)
    
    migration_id = 'f1a2b3c4d5e6'
    
    with engine.connect() as conn:
        # Check if migration is already marked
        result = conn.execute(
            text("SELECT version_num FROM alembic_version WHERE version_num = :version"),
            {"version": migration_id}
        )
        
        if result.fetchone():
            print(f"Migration {migration_id} is already marked as applied")
        else:
            # Mark the migration as applied
            conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": migration_id}
            )
            conn.commit()
            print(f"Successfully marked migration {migration_id} as applied")
    
    engine.dispose()

if __name__ == "__main__":
    mark_migration_applied()

# Made with Bob
