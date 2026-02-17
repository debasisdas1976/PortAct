"""
Debug script to test snapshot functionality and identify discrepancies
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.asset import Asset
from app.models.bank_account import BankAccount
from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
from app.services.eod_snapshot_service import EODSnapshotService
from datetime import date

def test_snapshot():
    db = SessionLocal()
    try:
        # Get the first active user
        user = db.query(User).filter(User.is_active == True).first()
        if not user:
            print("No active users found")
            return
        
        print(f"\n=== Testing Snapshot for User {user.id} ({user.email}) ===\n")
        
        # Get current portfolio data
        print("--- Current Portfolio Data ---")
        assets = db.query(Asset).filter(
            Asset.user_id == user.id,
            Asset.is_active == True
        ).all()
        
        bank_accounts = db.query(BankAccount).filter(
            BankAccount.user_id == user.id,
            BankAccount.is_active == True
        ).all()
        
        # Calculate current totals
        asset_total_invested = 0.0
        asset_total_current = 0.0
        
        print(f"\nAssets ({len(assets)}):")
        for asset in assets:
            asset.calculate_metrics()
            print(f"  - {asset.name} ({asset.symbol}): "
                  f"Invested={asset.total_invested:.2f}, "
                  f"Current={asset.current_value:.2f}")
            asset_total_invested += asset.total_invested
            asset_total_current += asset.current_value
        
        bank_total = 0.0
        print(f"\nBank Accounts ({len(bank_accounts)}):")
        for bank in bank_accounts:
            print(f"  - {bank.bank_name.value} ({bank.account_type.value}): "
                  f"Balance={bank.current_balance:.2f}")
            bank_total += bank.current_balance
        
        portfolio_total_invested = asset_total_invested + bank_total
        portfolio_total_current = asset_total_current + bank_total
        
        print(f"\n--- Portfolio Totals ---")
        print(f"Assets Invested: ₹{asset_total_invested:,.2f}")
        print(f"Assets Current: ₹{asset_total_current:,.2f}")
        print(f"Bank Accounts: ₹{bank_total:,.2f}")
        print(f"Total Invested: ₹{portfolio_total_invested:,.2f}")
        print(f"Total Current: ₹{portfolio_total_current:,.2f}")
        print(f"Profit/Loss: ₹{(portfolio_total_current - portfolio_total_invested):,.2f}")
        
        # Take snapshot
        print(f"\n--- Taking Snapshot ---")
        snapshot = EODSnapshotService.capture_snapshot(db, user.id, date.today())
        
        # Verify snapshot data
        print(f"\n--- Snapshot Data ---")
        print(f"Snapshot ID: {snapshot.id}")
        print(f"Date: {snapshot.snapshot_date}")
        print(f"Total Invested: ₹{snapshot.total_invested:,.2f}")
        print(f"Total Current: ₹{snapshot.total_current_value:,.2f}")
        print(f"Profit/Loss: ₹{snapshot.total_profit_loss:,.2f}")
        print(f"Assets Count: {snapshot.total_assets_count}")
        
        # Get asset snapshots
        asset_snapshots = db.query(AssetSnapshot).filter(
            AssetSnapshot.portfolio_snapshot_id == snapshot.id
        ).all()
        
        print(f"\n--- Asset Snapshots ({len(asset_snapshots)}) ---")
        snapshot_total_invested = 0.0
        snapshot_total_current = 0.0
        
        for snap in asset_snapshots:
            print(f"  - {snap.asset_name} ({snap.asset_symbol}): "
                  f"Type={snap.asset_type}, "
                  f"Invested={snap.total_invested:.2f}, "
                  f"Current={snap.current_value:.2f}")
            snapshot_total_invested += snap.total_invested
            snapshot_total_current += snap.current_value
        
        print(f"\n--- Verification ---")
        print(f"Sum of Asset Snapshots Invested: ₹{snapshot_total_invested:,.2f}")
        print(f"Sum of Asset Snapshots Current: ₹{snapshot_total_current:,.2f}")
        print(f"Portfolio Snapshot Invested: ₹{snapshot.total_invested:,.2f}")
        print(f"Portfolio Snapshot Current: ₹{snapshot.total_current_value:,.2f}")
        
        # Check discrepancies
        invested_diff = abs(portfolio_total_invested - snapshot.total_invested)
        current_diff = abs(portfolio_total_current - snapshot.total_current_value)
        
        print(f"\n--- Discrepancy Check ---")
        if invested_diff > 0.01:
            print(f"⚠️  INVESTED DISCREPANCY: ₹{invested_diff:,.2f}")
            print(f"   Expected: ₹{portfolio_total_invested:,.2f}")
            print(f"   Snapshot: ₹{snapshot.total_invested:,.2f}")
        else:
            print(f"✅ Invested amounts match")
        
        if current_diff > 0.01:
            print(f"⚠️  CURRENT VALUE DISCREPANCY: ₹{current_diff:,.2f}")
            print(f"   Expected: ₹{portfolio_total_current:,.2f}")
            print(f"   Snapshot: ₹{snapshot.total_current_value:,.2f}")
        else:
            print(f"✅ Current values match")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_snapshot()

# Made with Bob
