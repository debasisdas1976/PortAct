"""
SIP Transaction Creator service.
Generates SIP (Systematic Investment Plan) BUY transactions for mutual fund
assets using historical NAV data from mfapi.in.
"""
import logging
import requests
from datetime import date, datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.services.amfi_cache import AMFICache
from app.schemas.sip import (
    SIPPeriod, SIPPeriodicity, SIPTopup, TopupType,
    SIPTransactionPreview, SIPPreviewResponse,
)

logger = logging.getLogger(__name__)

MFAPI_BASE_URL = "https://api.mfapi.in/mf"

MF_ASSET_TYPES = {"equity_mutual_fund", "hybrid_mutual_fund", "debt_mutual_fund"}


def _apply_topup(current_amount: float, topup: SIPTopup) -> float:
    if topup.topup_type == TopupType.PERCENTAGE:
        return round(current_amount * (1 + topup.topup_value / 100), 2)
    return round(current_amount + topup.topup_value, 2)


class SIPTransactionService:

    @staticmethod
    def get_scheme_code(asset: Asset) -> Optional[str]:
        """Resolve AMFI scheme_code from asset ISIN via AMFICache."""
        if not asset.isin:
            return None
        scheme = AMFICache.get_by_isin(asset.isin)
        if scheme:
            return scheme.scheme_code
        # Fallback: direct AMFI text parse
        from app.services.mutual_fund_holdings_service import MutualFundHoldingsService
        return MutualFundHoldingsService.get_scheme_code_from_isin(asset.isin)

    @staticmethod
    def fetch_historical_navs(scheme_code: str) -> Dict[date, float]:
        """Fetch full NAV history from mfapi.in. Returns {date: nav_value}."""
        url = f"{MFAPI_BASE_URL}/{scheme_code}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch NAV history for {scheme_code}: {e}")
            raise ValueError(f"Failed to fetch NAV history from mfapi.in: {e}")

        nav_map: Dict[date, float] = {}
        for entry in data.get("data", []):
            try:
                d = datetime.strptime(entry["date"], "%d-%m-%Y").date()
                nav = float(entry["nav"])
                if nav > 0:
                    nav_map[d] = nav
            except (ValueError, KeyError):
                continue

        if not nav_map:
            raise ValueError("No NAV history available for this fund")
        return nav_map

    @staticmethod
    def generate_sip_dates(period: SIPPeriod) -> List[Tuple[date, float]]:
        """Generate (sip_date, sip_amount) tuples for a SIP period.
        Handles periodicity, day-clamping, annual topup, and skips future dates."""
        dates_amounts: List[Tuple[date, float]] = []
        current_amount = period.sip_amount
        today = date.today()

        if period.periodicity == SIPPeriodicity.WEEKLY:
            current = period.start_date
            anniversary = period.start_date + relativedelta(years=1)
            while current <= period.end_date:
                if current <= today:
                    dates_amounts.append((current, current_amount))
                current += timedelta(days=7)
                if period.topup and current >= anniversary:
                    current_amount = _apply_topup(current_amount, period.topup)
                    anniversary += relativedelta(years=1)
        else:
            # Monthly or Quarterly
            months_step = 1 if period.periodicity == SIPPeriodicity.MONTHLY else 3
            sip_day = period.start_date.day
            current = period.start_date
            anniversary = period.start_date + relativedelta(years=1)

            while current <= period.end_date:
                if current <= today:
                    dates_amounts.append((current, current_amount))
                next_dt = current + relativedelta(months=months_step)
                _, max_day = monthrange(next_dt.year, next_dt.month)
                current = next_dt.replace(day=min(sip_day, max_day))
                if period.topup and current >= anniversary:
                    current_amount = _apply_topup(current_amount, period.topup)
                    anniversary += relativedelta(years=1)

        return dates_amounts

    @staticmethod
    def find_nav_for_date(
        target_date: date,
        nav_map: Dict[date, float],
        max_lookback_days: int = 7,
    ) -> Tuple[Optional[float], date, str]:
        """Find NAV for target_date. Falls back to previous 7 trading days."""
        if target_date in nav_map:
            return nav_map[target_date], target_date, "exact"
        for offset in range(1, max_lookback_days + 1):
            check = target_date - timedelta(days=offset)
            if check in nav_map:
                return nav_map[check], check, "previous_trading_day"
        return None, target_date, "not_found"

    @staticmethod
    def validate_non_overlapping(periods: List[SIPPeriod]) -> Optional[str]:
        """Returns error message if any periods overlap, else None."""
        sorted_periods = sorted(periods, key=lambda p: p.start_date)
        for i in range(len(sorted_periods) - 1):
            if sorted_periods[i].end_date >= sorted_periods[i + 1].start_date:
                return (
                    f"SIP periods overlap: period ending {sorted_periods[i].end_date} "
                    f"overlaps with period starting {sorted_periods[i + 1].start_date}"
                )
        return None

    @staticmethod
    def preview_sip_transactions(
        asset: Asset,
        periods: List[SIPPeriod],
        scheme_code: str,
    ) -> SIPPreviewResponse:
        """Generate preview without persisting. Fetches NAV from mfapi.in."""
        nav_map = SIPTransactionService.fetch_historical_navs(scheme_code)

        all_previews: List[SIPTransactionPreview] = []
        warnings: List[str] = []
        total_amount = 0.0
        total_units = 0.0
        nav_not_found_count = 0

        for period_idx, period in enumerate(periods):
            sip_dates_amounts = SIPTransactionService.generate_sip_dates(period)
            total_in_period = len(sip_dates_amounts)

            for sip_num, (sip_date, sip_amount) in enumerate(sip_dates_amounts, 1):
                nav, nav_date, source = SIPTransactionService.find_nav_for_date(
                    sip_date, nav_map
                )
                if nav is None:
                    nav_not_found_count += 1
                    warnings.append(f"NAV not found for {sip_date} (skipped)")
                    continue

                units = round(sip_amount / nav, 4)
                total_amount += sip_amount
                total_units += units

                all_previews.append(SIPTransactionPreview(
                    sip_number=sip_num,
                    total_sips_in_period=total_in_period,
                    period_index=period_idx,
                    transaction_date=sip_date,
                    nav_date=nav_date,
                    sip_amount=sip_amount,
                    nav=nav,
                    units=units,
                    description=f"SIP #{sip_num} of {total_in_period} | Amount: Rs.{sip_amount:,.0f}",
                    nav_source=source,
                ))

        if nav_not_found_count > 0:
            warnings.insert(
                0,
                f"NAV not found for {nav_not_found_count} date(s) — those installments were skipped",
            )

        avg_nav = round(total_amount / total_units, 4) if total_units > 0 else 0.0

        return SIPPreviewResponse(
            asset_id=asset.id,
            asset_name=asset.name,
            scheme_code=scheme_code,
            total_transactions=len(all_previews),
            total_amount=round(total_amount, 2),
            total_units=round(total_units, 4),
            average_nav=avg_nav,
            transactions=all_previews,
            warnings=warnings,
        )

    @staticmethod
    def create_sip_transactions(
        db: Session,
        asset: Asset,
        periods: List[SIPPeriod],
        scheme_code: str,
        update_asset_metrics: bool = True,
    ) -> SIPPreviewResponse:
        """Create all SIP BUY transactions in bulk. Returns preview-style response."""
        preview = SIPTransactionService.preview_sip_transactions(
            asset, periods, scheme_code
        )

        for txn in preview.transactions:
            transaction = Transaction(
                asset_id=asset.id,
                transaction_type=TransactionType.BUY,
                transaction_date=datetime.combine(
                    txn.transaction_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc),
                quantity=txn.units,
                price_per_unit=txn.nav,
                total_amount=txn.sip_amount,
                fees=0.0,
                taxes=0.0,
                description=txn.description,
                notes=f"Auto-generated SIP | NAV date: {txn.nav_date} ({txn.nav_source})",
            )
            db.add(transaction)

        if update_asset_metrics:
            from app.api.v1.endpoints.transactions import _recalculate_asset_from_transactions
            _recalculate_asset_from_transactions(asset, db)

        db.commit()
        db.refresh(asset)
        return preview
