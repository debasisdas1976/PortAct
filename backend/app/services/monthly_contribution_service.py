"""
Monthly Contribution Service

Runs on the 1st of each month to:
1. Add Employee + Employer PF contributions for the previous month
2. Recompute and update Gratuity current value

Skips users without required salary/PF data or with is_employed=False.
"""
import calendar
import math
from datetime import date, datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType

_GRATUITY_CAP = 2_000_000.0  # ₹20 lakh


def _month_label(d: date) -> str:
    """Return 'Mon YYYY' string for a given date, e.g. 'Feb 2026'."""
    return d.strftime("%b %Y")


def _last_day_of_month(d: date) -> date:
    """Return the last calendar day of the month for *d*."""
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def _compute_gratuity(basic_pay: float, date_of_joining: date) -> dict:
    """Gratuity = (basic_pay × 15 × completed_years) / 26, capped at ₹20 lakh."""
    today = date.today()
    days = (today - date_of_joining).days
    years_of_service = days / 365.25
    completed_years = math.floor(years_of_service)
    raw_gratuity = (basic_pay * 15 * completed_years) / 26
    is_capped = raw_gratuity > _GRATUITY_CAP
    gratuity_amount = min(raw_gratuity, _GRATUITY_CAP)
    return {
        "years_of_service": round(years_of_service, 2),
        "completed_years": completed_years,
        "gratuity_amount": gratuity_amount,
        "is_eligible": completed_years >= 5,
        "is_capped": is_capped,
    }


class MonthlyContributionService:
    """Handles automatic PF contributions and Gratuity revaluation."""

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    @staticmethod
    def process_all_users(target_month: date | None = None):
        """
        Main entry point called by the scheduler on day 1 of each month.

        *target_month* defaults to the previous calendar month.  For example,
        when called on 1 Mar 2026 it processes Feb 2026.
        """
        if target_month is None:
            today = date.today()
            target_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        label = _month_label(target_month)
        logger.info(f"Monthly contribution job started for {label}")

        db: Session = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()  # noqa: E712

            pf_ok = pf_skip = pf_err = 0
            gr_ok = gr_skip = gr_err = 0

            for user in users:
                # --- PF ---
                try:
                    done = MonthlyContributionService._process_pf_for_user(
                        db, user, target_month,
                    )
                    if done:
                        pf_ok += 1
                    else:
                        pf_skip += 1
                except Exception as exc:
                    pf_err += 1
                    logger.error(
                        f"PF contribution error for user {user.id} ({label}): {exc}"
                    )

                # --- Gratuity ---
                try:
                    done = MonthlyContributionService._process_gratuity_for_user(
                        db, user,
                    )
                    if done:
                        gr_ok += 1
                    else:
                        gr_skip += 1
                except Exception as exc:
                    gr_err += 1
                    logger.error(
                        f"Gratuity update error for user {user.id}: {exc}"
                    )

            logger.info(
                f"Monthly contribution job completed for {label}. "
                f"PF: {pf_ok} processed, {pf_skip} skipped, {pf_err} errors. "
                f"Gratuity: {gr_ok} updated, {gr_skip} skipped, {gr_err} errors."
            )

        except Exception as exc:
            logger.error(f"Monthly contribution job failed: {exc}")
        finally:
            db.close()

    @staticmethod
    def check_and_run_missed_contributions():
        """
        Called at startup.  For each eligible user, look back up to 12 months
        and create any missing PF contributions.  Also refreshes Gratuity.
        """
        logger.info("Checking for missed monthly contributions…")

        db: Session = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()  # noqa: E712

            for user in users:
                if not MonthlyContributionService._user_eligible_for_pf(user):
                    continue

                pf_assets = db.query(Asset).filter(
                    Asset.user_id == user.id,
                    Asset.asset_type == AssetType.PF,
                    Asset.is_active == True,  # noqa: E712
                ).all()

                if not pf_assets:
                    continue

                # Determine the earliest month to check: max(12 months ago, date_of_joining)
                today = date.today()
                twelve_months_ago = (today.replace(day=1) - timedelta(days=1))
                twelve_months_ago = (twelve_months_ago - relativedelta(months=11)).replace(day=1)

                start_month = twelve_months_ago
                if user.date_of_joining and user.date_of_joining.replace(day=1) > start_month:
                    start_month = user.date_of_joining.replace(day=1)

                # Walk through each month up to (but not including) the current month
                current_month = start_month
                end_month = today.replace(day=1)  # 1st of current month

                while current_month < end_month:
                    try:
                        MonthlyContributionService._process_pf_for_user(
                            db, user, current_month,
                        )
                    except Exception as exc:
                        logger.error(
                            f"Missed PF catch-up error user={user.id} "
                            f"month={_month_label(current_month)}: {exc}"
                        )
                    current_month += relativedelta(months=1)

                # Also refresh gratuity
                try:
                    MonthlyContributionService._process_gratuity_for_user(db, user)
                except Exception as exc:
                    logger.error(f"Gratuity refresh error user={user.id}: {exc}")

            logger.info("Missed monthly contributions check completed.")
        except Exception as exc:
            logger.error(f"Error checking missed contributions: {exc}")
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _user_eligible_for_pf(user: User) -> bool:
        return (
            user.is_employed is True
            and user.basic_salary is not None
            and user.basic_salary > 0
        )

    @staticmethod
    def _process_pf_for_user(
        db: Session, user: User, target_month: date,
    ) -> bool:
        """
        Create PF contribution transactions for *target_month*.

        Returns True if transactions were created (or already existed),
        False if the user was skipped.
        """
        if not MonthlyContributionService._user_eligible_for_pf(user):
            return False

        pf_assets = db.query(Asset).filter(
            Asset.user_id == user.id,
            Asset.asset_type == AssetType.PF,
            Asset.is_active == True,  # noqa: E712
        ).all()

        if not pf_assets:
            return False

        label = _month_label(target_month)
        emp_desc = f"Employee PF contribution - {label}"
        er_desc = f"Employer PF contribution - {label}"

        employee_pct = user.pf_employee_pct if user.pf_employee_pct is not None else 12.0
        employer_pct = user.pf_employer_pct if user.pf_employer_pct is not None else 12.0
        employee_amount = round(user.basic_salary * employee_pct / 100, 2)
        employer_amount = round(user.basic_salary * employer_pct / 100, 2)
        txn_date = datetime.combine(
            _last_day_of_month(target_month),
            datetime.min.time(),
        ).replace(tzinfo=timezone.utc)

        created_any = False

        for asset in pf_assets:
            # Idempotency: check if employee contribution already exists
            existing = db.query(Transaction).filter(
                Transaction.asset_id == asset.id,
                Transaction.description == emp_desc,
            ).first()

            if existing:
                logger.debug(
                    f"PF contribution already exists for asset {asset.id} - {label}"
                )
                continue

            # Employee contribution (DEPOSIT)
            db.add(Transaction(
                asset_id=asset.id,
                transaction_type=TransactionType.DEPOSIT,
                transaction_date=txn_date,
                quantity=0,
                price_per_unit=0,
                total_amount=employee_amount,
                description=emp_desc,
            ))

            # Employer contribution (TRANSFER_IN)
            db.add(Transaction(
                asset_id=asset.id,
                transaction_type=TransactionType.TRANSFER_IN,
                transaction_date=txn_date,
                quantity=0,
                price_per_unit=0,
                total_amount=employer_amount,
                description=er_desc,
            ))

            # Update asset totals
            total_contribution = employee_amount + employer_amount
            asset.total_invested = (asset.total_invested or 0) + total_contribution
            asset.current_value = (asset.current_value or 0) + total_contribution
            asset.current_price = asset.current_value  # PF: price tracks balance
            asset.last_updated = datetime.now(timezone.utc)

            created_any = True
            logger.info(
                f"PF contribution added for user {user.id}, asset {asset.id}, "
                f"{label}: employee ₹{employee_amount}, employer ₹{employer_amount}"
            )

        if created_any:
            db.commit()

        return True

    @staticmethod
    def _process_gratuity_for_user(db: Session, user: User) -> bool:
        """
        Recompute gratuity for all active Gratuity assets of the user.

        Returns True if any asset was updated, False if skipped.
        """
        if not user.is_employed:
            return False
        if not user.basic_salary or user.basic_salary <= 0:
            return False
        if not user.date_of_joining:
            return False

        assets = db.query(Asset).filter(
            Asset.user_id == user.id,
            Asset.asset_type == AssetType.GRATUITY,
            Asset.is_active == True,  # noqa: E712
        ).all()

        if not assets:
            return False

        updated = False
        for asset in assets:
            details = dict(asset.details or {})
            doj = user.date_of_joining

            # Use asset-specific date_of_joining if available, else fall back to user profile
            if "date_of_joining" in details:
                try:
                    doj = date.fromisoformat(details["date_of_joining"])
                except (ValueError, TypeError):
                    pass

            basic_pay = user.basic_salary
            da_pct = user.da_percentage or 0
            effective_basic = basic_pay * (1 + da_pct / 100)

            computed = _compute_gratuity(effective_basic, doj)

            asset.current_price = computed["gratuity_amount"]
            asset.current_value = computed["gratuity_amount"]

            # Keep asset details in sync with latest profile values
            details["basic_pay"] = basic_pay
            details["da_percentage"] = da_pct
            asset.details = details

            asset.last_updated = datetime.now(timezone.utc)
            updated = True

            logger.info(
                f"Gratuity updated for user {user.id}, asset {asset.id}: "
                f"₹{computed['gratuity_amount']:.2f} "
                f"({computed['completed_years']} years, "
                f"{'eligible' if computed['is_eligible'] else 'not yet eligible'})"
            )

        if updated:
            db.commit()

        return True
