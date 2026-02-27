"""
Modular foreign currency value refresh service.

Single entry point to refresh INR values for ALL non-INR denominated assets
and account cash balances, without re-fetching market prices.

Scheduled daily and also called immediately before EOD snapshot.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.asset import Asset, AssetType
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.core.database import SessionLocal
from app.services.currency_converter import (
    get_usd_to_inr_rate,
    get_rate_to_inr,
    get_all_rates_to_inr,
    CurrencyConverter,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing sets — add new foreign-currency asset types to the relevant set
# ---------------------------------------------------------------------------

# Assets where details.price_usd stores the USD market price
_USD_PRICED_TYPES = {
    AssetType.CRYPTO,
    AssetType.US_STOCK,
}

# Assets that may be USD-denominated based on details.currency
_CONDITIONALLY_USD_TYPES = {
    AssetType.ESOP,
    AssetType.RSU,
}

# Assets with details.currency + details.original_amount (any currency)
_MULTI_CURRENCY_TYPES = {
    AssetType.CASH,
}

# All candidate types (union)
_ALL_FOREX_TYPES = list(_USD_PRICED_TYPES | _CONDITIONALLY_USD_TYPES | _MULTI_CURRENCY_TYPES)


def refresh_foreign_currency_values():
    """
    Top-level scheduled job: refresh INR values for every non-INR
    asset and account cash balance using latest exchange rates.

    Does NOT re-fetch market prices — relies on details.price_usd or
    details.original_amount already stored by the price updater.

    Safe to call multiple times (idempotent).
    """
    db = SessionLocal()
    try:
        # Clear cache so we get truly fresh rates
        CurrencyConverter.clear_cache()

        usd_to_inr = get_usd_to_inr_rate()
        logger.info(f"Forex refresh starting. USD/INR = {usd_to_inr:.4f}")

        # Refresh assets
        stats = _refresh_asset_forex(db, usd_to_inr)

        # Refresh demat account USD cash balances
        demat_stats = _refresh_demat_cash_usd(db, usd_to_inr)

        # Refresh crypto account USD cash balances
        crypto_stats = _refresh_crypto_cash_usd(db, usd_to_inr)

        db.commit()

        logger.info(
            f"Forex refresh complete. "
            f"Assets — updated: {stats['updated']}, skipped: {stats['skipped']}, "
            f"failed: {stats['failed']}. "
            f"Demat cash: {demat_stats['updated']}. "
            f"Crypto cash: {crypto_stats['updated']}."
        )

    except Exception as e:
        logger.error(f"Forex refresh failed: {e}")
        db.rollback()
    finally:
        db.close()


def _refresh_asset_forex(db: Session, usd_to_inr: float) -> dict:
    """Refresh INR values for all active assets with foreign currency exposure."""
    stats = {"updated": 0, "skipped": 0, "failed": 0}

    assets = db.query(Asset).filter(
        Asset.is_active == True,
        Asset.asset_type.in_(_ALL_FOREX_TYPES),
    ).all()

    # Collect unique non-USD currencies for batch rate fetch
    non_usd_currencies = set()
    for asset in assets:
        currency = (asset.details or {}).get("currency", "INR")
        if currency not in ("INR", "USD"):
            non_usd_currencies.add(currency)

    other_rates = {}
    if non_usd_currencies:
        other_rates = get_all_rates_to_inr(list(non_usd_currencies))

    now_iso = datetime.now(timezone.utc).isoformat()

    for asset in assets:
        try:
            details = asset.details or {}

            # Route 1: details.price_usd (crypto, us_stock)
            if asset.asset_type in _USD_PRICED_TYPES:
                price_usd = details.get("price_usd")
                if not price_usd or float(price_usd) <= 0:
                    stats["skipped"] += 1
                    continue
                new_price = float(price_usd) * usd_to_inr
                _apply_usd_price(asset, new_price, details, usd_to_inr, now_iso)
                stats["updated"] += 1
                continue

            # Route 2: ESOP/RSU with details.currency == "USD"
            if asset.asset_type in _CONDITIONALLY_USD_TYPES:
                currency = details.get("currency", "INR")
                if currency != "USD":
                    stats["skipped"] += 1
                    continue
                price_usd = details.get("price_usd")
                if not price_usd or float(price_usd) <= 0:
                    stats["skipped"] += 1
                    continue
                new_price = float(price_usd) * usd_to_inr
                _apply_usd_price(asset, new_price, details, usd_to_inr, now_iso)
                stats["updated"] += 1
                continue

            # Route 3: CASH with non-INR currency
            if asset.asset_type in _MULTI_CURRENCY_TYPES:
                currency = details.get("currency", asset.symbol or "INR")
                original_amount = details.get("original_amount")
                if currency == "INR" or not original_amount:
                    stats["skipped"] += 1
                    continue

                rate = usd_to_inr if currency == "USD" else other_rates.get(currency, 0.0)
                if not rate or rate <= 0:
                    logger.warning(f"No rate for {currency} (asset {asset.id} '{asset.name}')")
                    stats["failed"] += 1
                    continue

                inr_value = float(original_amount) * rate
                asset.current_price = inr_value
                asset.current_value = asset.quantity * inr_value
                asset.total_invested = inr_value
                asset.purchase_price = inr_value
                asset.calculate_metrics()
                asset.last_price_update = datetime.now(timezone.utc)
                asset.price_update_failed = False
                asset.price_update_error = None
                details["exchange_rate"] = rate
                details["last_rate_update"] = now_iso
                asset.details = details
                flag_modified(asset, "details")
                stats["updated"] += 1
                logger.info(
                    f"Forex: cash '{asset.name}' {currency} {original_amount}"
                    f" -> INR {inr_value:.2f} (rate {rate:.4f})"
                )
                continue

            stats["skipped"] += 1

        except Exception as e:
            logger.error(f"Forex refresh error for asset {asset.id}: {e}")
            stats["failed"] += 1

    return stats


def _apply_usd_price(
    asset: Asset,
    new_price_inr: float,
    details: dict,
    usd_to_inr: float,
    now_iso: str,
):
    """Apply a new INR price to an asset that has a USD source price."""
    asset.current_price = new_price_inr
    asset.current_value = asset.quantity * new_price_inr
    asset.calculate_metrics()
    asset.last_price_update = datetime.now(timezone.utc)
    asset.price_update_failed = False
    asset.price_update_error = None

    details["usd_to_inr_rate"] = usd_to_inr
    details["last_rate_update"] = now_iso
    asset.details = details
    flag_modified(asset, "details")

    logger.info(
        f"Forex: {asset.asset_type.value} '{asset.symbol}' "
        f"${details.get('price_usd')} * {usd_to_inr:.2f} = INR {new_price_inr:.2f}"
    )


def _refresh_demat_cash_usd(db: Session, usd_to_inr: float) -> dict:
    """Refresh cash_balance (INR) for demat accounts that hold USD cash."""
    stats = {"updated": 0}

    demat_accounts = db.query(DematAccount).filter(
        DematAccount.is_active == True,
        DematAccount.currency == "USD",
        DematAccount.cash_balance_usd > 0,
    ).all()

    for acct in demat_accounts:
        acct.cash_balance = acct.cash_balance_usd * usd_to_inr
        stats["updated"] += 1
        logger.info(
            f"Forex: demat '{acct.broker_name}' #{acct.account_id} "
            f"${acct.cash_balance_usd} -> INR {acct.cash_balance:.2f}"
        )

    return stats


def _refresh_crypto_cash_usd(db: Session, usd_to_inr: float) -> dict:
    """Refresh cash_balance_inr for crypto accounts with USD cash."""
    stats = {"updated": 0}

    crypto_accounts = db.query(CryptoAccount).filter(
        CryptoAccount.is_active == True,
        CryptoAccount.cash_balance_usd > 0,
    ).all()

    for acct in crypto_accounts:
        acct.cash_balance_inr = acct.cash_balance_usd * usd_to_inr
        stats["updated"] += 1
        logger.info(
            f"Forex: crypto '{acct.exchange_name}' "
            f"${acct.cash_balance_usd} -> INR {acct.cash_balance_inr:.2f}"
        )

    return stats
