"""
Script to fix mutual fund holding percentages for funds with incorrect data
This script identifies holdings with total percentage > 150% and corrects them
Works for any fund (Canara Robeco, Kotak Small Cap, etc.)
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.mutual_fund_holding import MutualFundHolding
from app.models.asset import Asset
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/portact")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def fix_all_mf_holdings():
    """Fix all mutual fund holdings with incorrect percentages"""
    db = SessionLocal()
    
    try:
        # Find all equity mutual funds
        all_funds = db.query(Asset).filter(
            Asset.asset_type == 'EQUITY_MUTUAL_FUND'
        ).all()
        
        if not all_funds:
            print("No equity mutual funds found in database")
            return
        
        print(f"Checking {len(all_funds)} equity mutual funds...\n")
        
        for fund in all_funds:
            print(f"\nProcessing: {fund.name}")
            
            # Get all holdings for this fund
            holdings = db.query(MutualFundHolding).filter(
                MutualFundHolding.asset_id == fund.id
            ).all()
            
            if not holdings:
                print(f"  No holdings found")
                continue
            
            # Calculate total percentage
            total_pct = sum(h.holding_percentage for h in holdings)
            print(f"  Total percentage: {total_pct:.2f}%")
            
            # If total is way over 100%, the percentages need to be divided by 100
            if total_pct > 150:
                print(f"  ⚠️  Total percentage is {total_pct:.2f}% - needs correction!")
                print(f"  Dividing all percentages by 100...")
                
                for holding in holdings:
                    old_pct = holding.holding_percentage
                    new_pct = old_pct / 100
                    holding.holding_percentage = new_pct
                    
                    # Recalculate holding value
                    if fund.quantity and fund.current_price:
                        holding.calculate_holding_value(fund.quantity, fund.current_price)
                    
                    print(f"    {holding.stock_name}: {old_pct:.2f}% → {new_pct:.2f}%")
                
                db.commit()
                
                # Verify the fix
                new_total = sum(h.holding_percentage for h in holdings)
                print(f"  ✓ New total percentage: {new_total:.2f}%")
            else:
                print(f"  ✓ Percentages look correct (total: {total_pct:.2f}%)")
        
        print("\n✓ Done!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Mutual Fund Holdings Percentage Fix")
    print("=" * 60)
    fix_all_mf_holdings()

# Made with Bob
