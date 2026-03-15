"""
Service for executing MF Systematic Plans (SIP / STP / SWP).

Called by the daily scheduler to process all due plans and create the
appropriate transactions automatically.
"""
import logging
import requests
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.models.mf_systematic_plan import MFSystematicPlan
from app.core.enums import SystematicPlanType, SystematicFrequency

logger = logging.getLogger(__name__)

MFAPI_BASE_URL = "https://api.mfapi.in/mf"
MF_ASSET_TYPES = {"equity_mutual_fund", "hybrid_mutual_fund", "debt_mutual_fund"}


def _fetch_latest_nav(scheme_code: str) -> Optional[float]:
    """Fetch the latest available NAV from mfapi.in."""
    try:
        resp = requests.get(f"{MFAPI_BASE_URL}/{scheme_code}", timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return float(data[0]["nav"])
    except Exception as e:
        logger.error(f"Failed to fetch latest NAV for scheme {scheme_code}: {e}")
    return None


def _get_scheme_code(asset: Asset) -> Optional[str]:
    """Resolve AMFI scheme_code from asset ISIN."""
    if not asset.isin:
        return None
    from app.services.amfi_cache import AMFICache
    scheme = AMFICache.get_by_isin(asset.isin)
    if scheme:
        return scheme.scheme_code
    from app.services.mutual_fund_holdings_service import MutualFundHoldingsService
    return MutualFundHoldingsService.get_scheme_code_from_isin(asset.isin)


def _recalc_asset(asset: Asset, db: Session):
    """Recalculate asset metrics after adding transactions."""
    from app.api.v1.endpoints.transactions import _recalculate_asset_from_transactions
    _recalculate_asset_from_transactions(asset, db)


def _is_plan_due_today(plan: MFSystematicPlan, today: date) -> bool:
    """Check if a plan should execute today based on its frequency."""
    # Not yet started or already past end
    if today < plan.start_date:
        return False
    if plan.end_date and today > plan.end_date:
        return False
    # Already executed today
    if plan.last_executed_date == today:
        return False

    freq = plan.frequency

    if freq == SystematicFrequency.DAILY:
        return True

    if freq == SystematicFrequency.WEEKLY:
        # execution_day: 0=Mon..6=Sun
        return today.weekday() == plan.execution_day

    if freq == SystematicFrequency.FORTNIGHTLY:
        # Every 14 days from start_date
        delta = (today - plan.start_date).days
        return delta >= 0 and delta % 14 == 0

    if freq == SystematicFrequency.MONTHLY:
        # Execute on execution_day of each month (clamped to month length)
        target_day = plan.execution_day
        # For months shorter than target_day, execute on last day
        import calendar
        _, max_day = calendar.monthrange(today.year, today.month)
        effective_day = min(target_day, max_day)
        return today.day == effective_day

    return False


def _execute_sip(plan: MFSystematicPlan, nav: float, db: Session):
    """Create a BUY transaction for a SIP plan."""
    units = round(plan.amount / nav, 4)
    txn = Transaction(
        asset_id=plan.asset_id,
        transaction_type=TransactionType.BUY,
        transaction_date=datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc),
        quantity=units,
        price_per_unit=nav,
        total_amount=plan.amount,
        fees=0.0,
        taxes=0.0,
        description=f"Auto SIP | {plan.amount:,.0f} INR",
        notes=f"Auto-executed SIP plan #{plan.id}",
    )
    db.add(txn)
    _recalc_asset(plan.asset, db)


def _execute_stp(plan: MFSystematicPlan, source_nav: float, target_nav: float, db: Session):
    """Create SELL on source + BUY on target for an STP plan."""
    today_dt = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    sell_units = round(plan.amount / source_nav, 4)

    # SELL from source
    db.add(Transaction(
        asset_id=plan.asset_id,
        transaction_type=TransactionType.SELL,
        transaction_date=today_dt,
        quantity=sell_units,
        price_per_unit=source_nav,
        total_amount=plan.amount,
        fees=0.0,
        taxes=0.0,
        description=f"Auto STP OUT | {plan.amount:,.0f} INR",
        notes=f"Auto-executed STP plan #{plan.id} (source)",
    ))

    # BUY into target
    buy_units = round(plan.amount / target_nav, 4)
    db.add(Transaction(
        asset_id=plan.target_asset_id,
        transaction_type=TransactionType.BUY,
        transaction_date=today_dt,
        quantity=buy_units,
        price_per_unit=target_nav,
        total_amount=plan.amount,
        fees=0.0,
        taxes=0.0,
        description=f"Auto STP IN | {plan.amount:,.0f} INR",
        notes=f"Auto-executed STP plan #{plan.id} (target)",
    ))

    _recalc_asset(plan.asset, db)
    _recalc_asset(plan.target_asset, db)


def _execute_swp(plan: MFSystematicPlan, nav: float, db: Session):
    """Create a SELL transaction for a SWP plan."""
    units = round(plan.amount / nav, 4)
    txn = Transaction(
        asset_id=plan.asset_id,
        transaction_type=TransactionType.SELL,
        transaction_date=datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc),
        quantity=units,
        price_per_unit=nav,
        total_amount=plan.amount,
        fees=0.0,
        taxes=0.0,
        description=f"Auto SWP | {plan.amount:,.0f} INR",
        notes=f"Auto-executed SWP plan #{plan.id}",
    )
    db.add(txn)
    _recalc_asset(plan.asset, db)


def process_due_plans():
    """Main entry point called by the scheduler. Processes all due plans for all users."""
    from app.core.database import SessionLocal
    db: Session = SessionLocal()
    today = date.today()

    try:
        # Fetch all active plans
        plans = db.query(MFSystematicPlan).filter(
            MFSystematicPlan.is_active == True,
        ).all()

        processed = 0
        errors = 0

        for plan in plans:
            # Auto-deactivate expired plans
            if plan.end_date and today > plan.end_date:
                plan.is_active = False
                db.commit()
                logger.info(f"Plan #{plan.id} auto-deactivated (past end_date {plan.end_date})")
                continue

            if not _is_plan_due_today(plan, today):
                continue

            try:
                asset = plan.asset
                asset_type_val = asset.asset_type if isinstance(asset.asset_type, str) else asset.asset_type.value
                if asset_type_val not in MF_ASSET_TYPES:
                    logger.warning(f"Plan #{plan.id}: asset {asset.id} is not a mutual fund, skipping")
                    continue

                scheme_code = _get_scheme_code(asset)
                if not scheme_code:
                    logger.warning(f"Plan #{plan.id}: could not resolve scheme code for asset {asset.id}")
                    continue

                nav = _fetch_latest_nav(scheme_code)
                if not nav:
                    logger.warning(f"Plan #{plan.id}: could not fetch NAV for scheme {scheme_code}")
                    continue

                if plan.plan_type == SystematicPlanType.SIP:
                    _execute_sip(plan, nav, db)

                elif plan.plan_type == SystematicPlanType.STP:
                    target_asset = plan.target_asset
                    if not target_asset:
                        logger.warning(f"Plan #{plan.id}: STP target asset not found")
                        continue
                    target_scheme = _get_scheme_code(target_asset)
                    if not target_scheme:
                        logger.warning(f"Plan #{plan.id}: could not resolve target scheme code")
                        continue
                    target_nav = _fetch_latest_nav(target_scheme)
                    if not target_nav:
                        logger.warning(f"Plan #{plan.id}: could not fetch target NAV")
                        continue
                    _execute_stp(plan, nav, target_nav, db)

                elif plan.plan_type == SystematicPlanType.SWP:
                    _execute_swp(plan, nav, db)

                plan.last_executed_date = today
                db.commit()
                processed += 1
                logger.info(f"Plan #{plan.id} ({plan.plan_type.value}) executed successfully")

            except Exception as exc:
                db.rollback()
                errors += 1
                logger.error(f"Plan #{plan.id} execution failed: {exc}")

        logger.info(f"MF systematic plans: processed={processed}, errors={errors}, total_active={len(plans)}")

    except Exception as exc:
        logger.error(f"MF systematic plan processing failed: {exc}")
    finally:
        db.close()
