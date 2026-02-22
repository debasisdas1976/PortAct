"""
One-time script to assign the default portfolio to all bank accounts,
demat accounts, and assets that don't have a portfolio_id set.

Usage: cd backend && python fix_portfolio_assignment.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.portfolio import Portfolio
from app.models.asset import Asset
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount

def fix_portfolio_assignments():
    db: Session = SessionLocal()
    try:
        # Get all default portfolios (one per user)
        default_portfolios = db.query(Portfolio).filter(Portfolio.is_default == True).all()

        if not default_portfolios:
            print("No default portfolios found. Nothing to do.")
            return

        for portfolio in default_portfolios:
            user_id = portfolio.user_id
            pid = portfolio.id
            print(f"\nUser {user_id} — Default portfolio: id={pid} name='{portfolio.name}'")

            # Fix bank accounts
            updated = db.query(BankAccount).filter(
                BankAccount.user_id == user_id,
                BankAccount.portfolio_id == None
            ).update({"portfolio_id": pid}, synchronize_session=False)
            print(f"  Bank accounts updated: {updated}")

            # Fix demat accounts
            updated = db.query(DematAccount).filter(
                DematAccount.user_id == user_id,
                DematAccount.portfolio_id == None
            ).update({"portfolio_id": pid}, synchronize_session=False)
            print(f"  Demat accounts updated: {updated}")

            # Fix assets
            updated = db.query(Asset).filter(
                Asset.user_id == user_id,
                Asset.portfolio_id == None
            ).update({"portfolio_id": pid}, synchronize_session=False)
            print(f"  Assets updated: {updated}")

        db.commit()
        print("\nDone. All records without a portfolio now belong to the default portfolio.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_portfolio_assignments()
