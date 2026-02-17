"""
Script to remove duplicate PPF transactions from the database.
Keeps the oldest transaction for each unique combination of:
- asset_id
- transaction_date
- transaction_type
- total_amount
"""

import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.transaction import Transaction
from app.models.asset import Asset, AssetType

# Create database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def remove_duplicate_ppf_transactions():
    """Remove duplicate PPF transactions, keeping only the oldest one."""
    db = SessionLocal()
    
    try:
        # Get all PPF assets
        ppf_assets = db.query(Asset).filter(Asset.asset_type == AssetType.PPF).all()
        ppf_asset_ids = [asset.id for asset in ppf_assets]
        
        if not ppf_asset_ids:
            print("No PPF assets found.")
            return
        
        print(f"Found {len(ppf_asset_ids)} PPF assets")
        
        # Get all transactions for PPF assets
        all_transactions = db.query(Transaction).filter(
            Transaction.asset_id.in_(ppf_asset_ids)
        ).order_by(Transaction.id).all()
        
        print(f"Total PPF transactions: {len(all_transactions)}")
        
        # Group transactions by unique key
        seen = {}
        duplicates_to_delete = []
        
        for trans in all_transactions:
            # Create unique key
            key = (
                trans.asset_id,
                trans.transaction_date,
                trans.transaction_type,
                trans.total_amount
            )
            
            if key in seen:
                # This is a duplicate, mark for deletion
                duplicates_to_delete.append(trans.id)
                print(f"Duplicate found: ID={trans.id}, Date={trans.transaction_date}, "
                      f"Type={trans.transaction_type}, Amount={trans.total_amount}")
            else:
                # First occurrence, keep it
                seen[key] = trans.id
        
        print(f"\nFound {len(duplicates_to_delete)} duplicate transactions")
        
        if duplicates_to_delete:
            # Delete duplicates
            deleted_count = db.query(Transaction).filter(
                Transaction.id.in_(duplicates_to_delete)
            ).delete(synchronize_session=False)
            
            db.commit()
            print(f"Deleted {deleted_count} duplicate transactions")
            
            # Verify
            remaining = db.query(Transaction).filter(
                Transaction.asset_id.in_(ppf_asset_ids)
            ).count()
            print(f"Remaining PPF transactions: {remaining}")
        else:
            print("No duplicates found!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting PPF duplicate transaction cleanup...")
    remove_duplicate_ppf_transactions()
    print("Cleanup complete!")

# Made with Bob
