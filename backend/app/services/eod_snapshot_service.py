"""
End of Day (EOD) Snapshot Service
Captures portfolio and asset snapshots for historical tracking
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
from typing import Optional
import logging

from app.models.user import User
from app.models.asset import Asset
from app.models.bank_account import BankAccount
from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
from app.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EODSnapshotService:
    """Service for managing end-of-day portfolio snapshots"""
    
    @staticmethod
    def capture_snapshot(db: Session, user_id: int, snapshot_date: Optional[date] = None) -> PortfolioSnapshot:
        """
        Capture a snapshot of the user's portfolio for a specific date.
        
        Args:
            db: Database session
            user_id: User ID
            snapshot_date: Date for the snapshot (defaults to today)
            
        Returns:
            PortfolioSnapshot object
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        logger.info(f"Capturing snapshot for user {user_id} on {snapshot_date}")
        
        # Check if snapshot already exists for this date
        existing_snapshot = db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.snapshot_date == snapshot_date
        ).first()
        
        if existing_snapshot:
            logger.info(f"Snapshot already exists for user {user_id} on {snapshot_date}, updating...")
            # Delete existing asset snapshots
            db.query(AssetSnapshot).filter(
                AssetSnapshot.portfolio_snapshot_id == existing_snapshot.id
            ).delete()
            db.flush()  # Ensure deletion is persisted
            portfolio_snapshot = existing_snapshot
        else:
            # Create new portfolio snapshot
            portfolio_snapshot = PortfolioSnapshot(
                user_id=user_id,
                snapshot_date=snapshot_date
            )
            db.add(portfolio_snapshot)
            db.flush()  # Get the ID
        
        # Get all active assets for the user
        assets = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.is_active == True
        ).all()
        
        # Get all active bank accounts for the user
        bank_accounts = db.query(BankAccount).filter(
            BankAccount.user_id == user_id,
            BankAccount.is_active == True
        ).all()
        
        # Calculate metrics for each asset
        total_invested = 0.0
        total_current_value = 0.0
        
        for asset in assets:
            # Ensure metrics are calculated
            asset.calculate_metrics()
            
            # Create asset snapshot
            asset_snapshot = AssetSnapshot(
                portfolio_snapshot_id=portfolio_snapshot.id,
                asset_id=asset.id,
                snapshot_date=snapshot_date,
                asset_type=asset.asset_type.value,
                asset_name=asset.name,
                asset_symbol=asset.symbol,
                quantity=asset.quantity,
                purchase_price=asset.purchase_price,
                current_price=asset.current_price,
                total_invested=asset.total_invested,
                current_value=asset.current_value,
                profit_loss=asset.profit_loss,
                profit_loss_percentage=asset.profit_loss_percentage
            )
            db.add(asset_snapshot)
            
            total_invested += asset.total_invested
            total_current_value += asset.current_value
        
        # Add bank accounts to the snapshot
        # Bank accounts are treated as cash with no profit/loss
        for bank_account in bank_accounts:
            # Create asset snapshot for bank account
            asset_snapshot = AssetSnapshot(
                portfolio_snapshot_id=portfolio_snapshot.id,
                asset_id=None,  # Bank accounts don't have asset_id
                snapshot_date=snapshot_date,
                asset_type='bank_account',
                asset_name=f"{bank_account.bank_name.value} - {bank_account.account_type.value}",
                asset_symbol=bank_account.account_number[-4:] if bank_account.account_number else 'N/A',
                quantity=1.0,
                purchase_price=bank_account.current_balance,
                current_price=bank_account.current_balance,
                total_invested=bank_account.current_balance,
                current_value=bank_account.current_balance,
                profit_loss=0.0,
                profit_loss_percentage=0.0
            )
            db.add(asset_snapshot)
            
            # Bank accounts: invested = current value (no profit/loss)
            total_invested += bank_account.current_balance
            total_current_value += bank_account.current_balance
        
        # Update portfolio snapshot with totals
        total_profit_loss = total_current_value - total_invested
        total_profit_loss_percentage = (
            (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
        )
        
        portfolio_snapshot.total_invested = total_invested
        portfolio_snapshot.total_current_value = total_current_value
        portfolio_snapshot.total_profit_loss = total_profit_loss
        portfolio_snapshot.total_profit_loss_percentage = total_profit_loss_percentage
        portfolio_snapshot.total_assets_count = len(assets) + len(bank_accounts)
        
        db.commit()
        db.refresh(portfolio_snapshot)
        
        logger.info(
            f"Snapshot captured for user {user_id}: "
            f"{len(assets)} assets, {len(bank_accounts)} bank accounts, "
            f"Total Value: {total_current_value:.2f}, "
            f"P/L: {total_profit_loss:.2f} ({total_profit_loss_percentage:.2f}%)"
        )
        
        return portfolio_snapshot
    
    @staticmethod
    def capture_all_users_snapshots(snapshot_date: Optional[date] = None):
        """
        Capture snapshots for all users.
        This is the main EOD process that runs daily.
        
        Args:
            snapshot_date: Date for the snapshot (defaults to today)
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        logger.info(f"Starting EOD snapshot process for {snapshot_date}")
        
        db = SessionLocal()
        try:
            # Get all active users
            users = db.query(User).filter(User.is_active == True).all()
            
            success_count = 0
            error_count = 0
            
            for user in users:
                try:
                    EODSnapshotService.capture_snapshot(db, user.id, snapshot_date)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error capturing snapshot for user {user.id}: {str(e)}")
            
            logger.info(
                f"EOD snapshot process completed: "
                f"{success_count} successful, {error_count} errors"
            )
            
        except Exception as e:
            logger.error(f"Error in EOD snapshot process: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def check_and_run_missed_snapshots():
        """
        Check if any snapshots were missed and run them.
        This runs when the application starts up.
        """
        logger.info("Checking for missed EOD snapshots...")
        
        db = SessionLocal()
        try:
            # Get all active users
            users = db.query(User).filter(User.is_active == True).all()
            
            for user in users:
                # Get the last snapshot date for this user
                last_snapshot = db.query(PortfolioSnapshot).filter(
                    PortfolioSnapshot.user_id == user.id
                ).order_by(PortfolioSnapshot.snapshot_date.desc()).first()
                
                if last_snapshot:
                    last_date = last_snapshot.snapshot_date
                else:
                    # If no snapshots exist, check if user has any assets
                    has_assets = db.query(Asset).filter(
                        Asset.user_id == user.id,
                        Asset.is_active == True
                    ).first()
                    
                    if not has_assets:
                        continue  # Skip users with no assets
                    
                    # Start from yesterday if no snapshots exist
                    last_date = date.today() - timedelta(days=1)
                
                # Check for missing dates between last snapshot and yesterday
                yesterday = date.today() - timedelta(days=1)
                current_date = last_date + timedelta(days=1)
                
                missed_dates = []
                while current_date <= yesterday:
                    # Check if snapshot exists for this date
                    exists = db.query(PortfolioSnapshot).filter(
                        PortfolioSnapshot.user_id == user.id,
                        PortfolioSnapshot.snapshot_date == current_date
                    ).first()
                    
                    if not exists:
                        missed_dates.append(current_date)
                    
                    current_date += timedelta(days=1)
                
                # Capture missed snapshots
                for missed_date in missed_dates:
                    try:
                        logger.info(f"Capturing missed snapshot for user {user.id} on {missed_date}")
                        EODSnapshotService.capture_snapshot(db, user.id, missed_date)
                    except Exception as e:
                        logger.error(
                            f"Error capturing missed snapshot for user {user.id} "
                            f"on {missed_date}: {str(e)}"
                        )
            
            logger.info("Missed snapshot check completed")
            
        except Exception as e:
            logger.error(f"Error checking missed snapshots: {str(e)}")
        finally:
            db.close()

# Made with Bob