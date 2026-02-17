#!/usr/bin/env python3
"""
Test the consolidated MF upload API endpoint
Simulates the actual API call to find all errors
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.consolidated_mf_parser import ConsolidatedMFParser, match_fund_to_asset
from app.models.mutual_fund_holding import MutualFundHolding
from app.models.asset import Asset, AssetType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def test_upload_flow():
    """Test the complete upload flow"""
    
    print("=" * 80)
    print("TESTING CONSOLIDATED MF UPLOAD FLOW")
    print("=" * 80)
    
    # Step 1: Parse the file
    print("\n1. Parsing Excel file...")
    excel_file = "../statements/mfs/MF-Holdings.xlsx"
    parser = ConsolidatedMFParser(excel_file)
    all_funds = parser.parse_all_funds()
    print(f"   ✓ Parsed {len(all_funds)} funds")
    
    # Step 2: Connect to database
    print("\n2. Connecting to database...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        print("   ✓ Connected to database")
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False
    
    # Step 3: Get user's equity funds
    print("\n3. Fetching user's equity mutual funds...")
    try:
        equity_funds = db.query(Asset).filter(
            Asset.user_id == 1,  # Assuming user_id = 1
            Asset.asset_type == AssetType.EQUITY_MUTUAL_FUND
        ).all()
        print(f"   ✓ Found {len(equity_funds)} equity funds in portfolio")
        
        if equity_funds:
            print("\n   User's funds:")
            for fund in equity_funds[:5]:
                print(f"     - {fund.name}")
                print(f"       Units: {fund.quantity}, NAV: {fund.current_price}")
    except Exception as e:
        print(f"   ✗ Error fetching funds: {e}")
        return False
    
    # Step 4: Match and test import
    print("\n4. Testing fund matching and import...")
    
    if not equity_funds:
        print("   ⚠ No equity funds in portfolio - cannot test matching")
        return True
    
    asset_names = [fund.name for fund in equity_funds]
    asset_map = {fund.name: fund for fund in equity_funds}
    
    results = []
    for fund_name_from_excel, holdings in all_funds.items():
        print(f"\n   Processing: {fund_name_from_excel}")
        print(f"   Holdings: {len(holdings)}")
        
        # Match fund name
        matched_asset_name, similarity_score = match_fund_to_asset(
            fund_name_from_excel,
            asset_names
        )
        
        print(f"   Best match: {matched_asset_name} (score: {similarity_score:.2f})")
        
        if similarity_score < 0.6:
            print(f"   ⚠ Score too low, skipping")
            continue
        
        # Get the matched asset
        asset = asset_map[matched_asset_name]
        
        # Test creating holdings
        print(f"   Testing holding creation...")
        try:
            created_count = 0
            for holding_data in holdings[:3]:  # Test first 3
                holding = MutualFundHolding(
                    asset_id=asset.id,
                    user_id=1,
                    stock_name=holding_data['name'],
                    isin=holding_data.get('isin'),
                    holding_percentage=holding_data['percentage'],
                    sector=holding_data.get('sector'),
                    industry=holding_data.get('industry'),
                    data_source='test'
                )
                
                # Test calculate_holding_value
                if asset.quantity and asset.current_price:
                    try:
                        holding.calculate_holding_value(asset.quantity, asset.current_price)
                        print(f"     ✓ {holding_data['name']}: {holding_data['percentage']:.2f}% = ₹{holding.holding_value:.2f}")
                    except Exception as e:
                        print(f"     ✗ Error calculating value: {e}")
                        raise
                else:
                    print(f"     ⚠ Cannot calculate value (units={asset.quantity}, nav={asset.current_price})")
                
                created_count += 1
            
            print(f"   ✓ Successfully created {created_count} test holdings")
            
        except Exception as e:
            print(f"   ✗ Error creating holdings: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    db.close()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = test_upload_flow()
    sys.exit(0 if success else 1)

# Made with Bob
