#!/usr/bin/env python3
"""
Backfill ISIN for existing assets that don't have it
"""
import sys
sys.path.insert(0, '/Users/debasis/Debasis/personal/Projects/PortAct/backend')

# Import all models first to avoid circular import issues
from app.models import user, asset, demat_account, crypto_account, statement, transaction, bank_account, expense, expense_category, alert
from app.core.database import SessionLocal
from app.models.asset import Asset, AssetType
from app.services.isin_lookup import lookup_isin_for_asset
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_isin():
    """Backfill ISIN for assets that don't have it"""
    db = SessionLocal()
    
    try:
        # Get all assets without ISIN
        assets = db.query(Asset).filter(
            (Asset.isin == None) | (Asset.isin == '')
        ).all()
        
        logger.info(f"Found {len(assets)} assets without ISIN")
        
        updated_count = 0
        failed_count = 0
        
        for asset in assets:
            try:
                # ISIN is only applicable for Indian Stocks and Mutual Funds
                if asset.asset_type not in [AssetType.STOCK, AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]:
                    logger.debug(f"Skipping {asset.symbol} ({asset.asset_type.value}) - ISIN only for Indian stocks and mutual funds")
                    continue
                
                logger.info(f"Looking up ISIN for {asset.symbol} ({asset.name})...")
                
                isin, api_symbol = lookup_isin_for_asset(
                    asset_type=asset.asset_type.value,
                    symbol=asset.symbol or '',
                    name=asset.name or ''
                )
                
                if isin:
                    asset.isin = isin
                    if api_symbol and not asset.api_symbol:
                        asset.api_symbol = api_symbol
                    
                    logger.info(f"✓ Updated {asset.symbol}: ISIN={isin}, API Symbol={api_symbol}")
                    updated_count += 1
                else:
                    logger.warning(f"✗ Could not find ISIN for {asset.symbol} ({asset.name})")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing {asset.symbol}: {str(e)}")
                failed_count += 1
        
        # Commit all changes
        db.commit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Backfill complete!")
        logger.info(f"Updated: {updated_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total processed: {updated_count + failed_count}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_isin()

# Made with Bob
