"""
Diagnostic script to identify why asset prices are not updating
"""
import sys
sys.path.append('/Users/debasis/Debasis/personal/Projects/PortAct/backend')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import asset, user, crypto_account  # Import all models
from app.models.asset import Asset, AssetType
from app.services.price_updater import (
    get_stock_price_nse,
    get_mutual_fund_price,
    get_us_stock_price,
    get_crypto_price,
    update_asset_price
)
from datetime import datetime

def diagnose_asset_price_updates():
    """Diagnose why asset prices are not updating"""
    
    db = SessionLocal()
    
    try:
        # Get all active assets
        assets = db.query(Asset).filter(Asset.is_active == True).all()
        
        print("=" * 100)
        print("ASSET PRICE UPDATE DIAGNOSIS REPORT")
        print("=" * 100)
        print(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Active Assets: {len(assets)}\n")
        
        # Group assets by update status
        failed_assets = []
        never_updated = []
        successfully_updated = []
        
        for asset in assets:
            if asset.price_update_failed:
                failed_assets.append(asset)
            elif asset.last_price_update:
                successfully_updated.append(asset)
            else:
                never_updated.append(asset)
        
        print(f"✓ Successfully Updated: {len(successfully_updated)}")
        print(f"⚠ Failed Updates: {len(failed_assets)}")
        print(f"⚠ Never Updated: {len(never_updated)}")
        
        # Detailed analysis of failed assets
        if failed_assets:
            print("\n" + "=" * 100)
            print("FAILED PRICE UPDATES - DETAILED ANALYSIS")
            print("=" * 100)
            
            for asset in failed_assets:
                print(f"\n{'─' * 100}")
                print(f"Asset: {asset.name}")
                print(f"Symbol: {asset.symbol}")
                print(f"Type: {asset.asset_type.value}")
                print(f"Current Price: ₹{asset.current_price:,.2f}")
                print(f"Error: {asset.price_update_error}")
                print(f"\nDiagnosing issue...")
                
                # Try to fetch price and diagnose
                if asset.asset_type == AssetType.STOCK:
                    print(f"  → Attempting to fetch NSE price for '{asset.symbol}'...")
                    price = get_stock_price_nse(asset.symbol)
                    if price:
                        print(f"  ✓ Successfully fetched: ₹{price:,.2f}")
                        print(f"  → Issue: Price fetch works, but may have failed during scheduled update")
                    else:
                        print(f"  ✗ Failed to fetch NSE price")
                        print(f"  → Possible reasons:")
                        print(f"     1. Symbol '{asset.symbol}' not found on NSE")
                        print(f"     2. NSE API is down or rate-limited")
                        print(f"     3. Symbol format is incorrect")
                        
                elif asset.asset_type in [AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]:
                    print(f"  → Attempting to fetch NAV for '{asset.symbol}'...")
                    price = get_mutual_fund_price(asset.symbol)
                    if price:
                        print(f"  ✓ Successfully fetched: ₹{price:,.2f}")
                        print(f"  → Issue: Price fetch works, but may have failed during scheduled update")
                    else:
                        print(f"  ✗ Failed to fetch NAV")
                        print(f"  → Possible reasons:")
                        print(f"     1. Symbol/ISIN '{asset.symbol}' not found in AMFI database")
                        print(f"     2. Fund name doesn't match AMFI naming convention")
                        print(f"     3. AMFI API is down")
                        print(f"  → Suggestions:")
                        print(f"     - Check if symbol is correct ISIN or fund name")
                        print(f"     - Try searching AMFI database manually")
                        print(f"     - For ETFs like GOLDBEES, SILVERBEES, use exact AMFI names")
                        
                elif asset.asset_type == AssetType.US_STOCK:
                    print(f"  → Attempting to fetch US stock price for '{asset.symbol}'...")
                    price = get_us_stock_price(asset.symbol)
                    if price:
                        print(f"  ✓ Successfully fetched: ${price:,.2f}")
                        print(f"  → Issue: Price fetch works, but may have failed during scheduled update")
                    else:
                        print(f"  ✗ Failed to fetch US stock price")
                        print(f"  → Possible reasons:")
                        print(f"     1. Symbol '{asset.symbol}' not found")
                        print(f"     2. API rate limit exceeded")
                        print(f"     3. Symbol format is incorrect")
                        
                elif asset.asset_type == AssetType.CRYPTO:
                    print(f"  → Attempting to fetch crypto price for '{asset.symbol}'...")
                    coin_id = asset.details.get('coin_id') if asset.details else None
                    price = get_crypto_price(asset.symbol, coin_id)
                    if price:
                        print(f"  ✓ Successfully fetched: ${price:,.2f}")
                        print(f"  → Issue: Price fetch works, but may have failed during scheduled update")
                    else:
                        print(f"  ✗ Failed to fetch crypto price")
                        print(f"  → Possible reasons:")
                        print(f"     1. Coin ID not found in CoinGecko")
                        print(f"     2. Symbol '{asset.symbol}' doesn't match CoinGecko naming")
                        print(f"     3. API rate limit exceeded")
        
        # Analysis of never updated assets
        if never_updated:
            print("\n" + "=" * 100)
            print("NEVER UPDATED ASSETS - ANALYSIS")
            print("=" * 100)
            
            for asset in never_updated:
                print(f"\n{'─' * 100}")
                print(f"Asset: {asset.name}")
                print(f"Symbol: {asset.symbol}")
                print(f"Type: {asset.asset_type.value}")
                print(f"Current Price: ₹{asset.current_price:,.2f}")
                print(f"Created: {asset.created_at}")
                print(f"\n  → This asset has never had a price update attempt")
                print(f"  → Possible reasons:")
                print(f"     1. Asset was created after last scheduled update")
                print(f"     2. Price updater hasn't run yet")
                print(f"     3. Asset type not supported by price updater")
        
        # Summary and recommendations
        print("\n" + "=" * 100)
        print("RECOMMENDATIONS")
        print("=" * 100)
        
        print("\n1. For ETFs (GOLDBEES-E, SILVERBEES-E, etc.):")
        print("   - These are listed on NSE as stocks, not mutual funds")
        print("   - Symbol should be without '-E' suffix for NSE API")
        print("   - Example: Use 'GOLDBEES' instead of 'GOLDBEES-E'")
        print("   - Or update asset_type to 'stock' instead of 'equity_mutual_fund'")
        
        print("\n2. For Mutual Funds:")
        print("   - Ensure symbol is the correct ISIN code")
        print("   - Or use exact fund name as per AMFI database")
        print("   - Check AMFI website: https://www.amfiindia.com/")
        
        print("\n3. For Failed Updates:")
        print("   - Use the manual 'Refresh' button in UI to retry")
        print("   - Or use the 'Edit' button to manually set the price")
        print("   - Check if the symbol/ISIN is correct")
        
        print("\n4. General:")
        print("   - Ensure price updater scheduler is running")
        print("   - Check backend logs for API errors")
        print("   - Verify internet connectivity for external APIs")
        
        print("\n" + "=" * 100)
        print("END OF REPORT")
        print("=" * 100)
        
    except Exception as e:
        print(f"\n✗ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose_asset_price_updates()

# Made with Bob
