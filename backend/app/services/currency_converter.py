"""
Currency conversion service for fetching real-time exchange rates
"""
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Service to fetch and cache currency conversion rates"""

    # Cache for exchange rates (in-memory, could be moved to Redis for production)
    _rate_cache = {}
    _cache_duration = timedelta(hours=1)  # Cache rates for 1 hour

    @classmethod
    def _get_all_usd_rates(cls) -> Dict[str, float]:
        """
        Get all exchange rates relative to USD (cached for 1 hour).

        Returns:
            dict: Currency code -> rate relative to USD (e.g. {"INR": 85.2, "EUR": 0.92})
        """
        cache_key = "ALL_RATES"

        if cache_key in cls._rate_cache:
            cached_data = cls._rate_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < cls._cache_duration:
                return cached_data['rates']

        rates = cls._fetch_all_rates_from_api()
        if rates:
            cls._rate_cache[cache_key] = {
                'rates': rates,
                'timestamp': datetime.now()
            }
            return rates

        # Fallback with approximate rates
        return {"INR": 83.0, "USD": 1.0}

    @classmethod
    def _fetch_all_rates_from_api(cls) -> Optional[Dict[str, float]]:
        """Fetch all exchange rates from API (base USD)."""
        for url in [settings.EXCHANGE_RATE_API, settings.EXCHANGE_RATE_FALLBACK_API]:
            try:
                response = requests.get(url, timeout=settings.API_TIMEOUT_SHORT)
                response.raise_for_status()
                rates = response.json().get('rates', {})
                if rates:
                    logger.info(f"Fetched {len(rates)} exchange rates from {url}")
                    return {k: float(v) for k, v in rates.items()}
            except Exception as e:
                logger.error(f"Exchange rate API failed ({url}): {str(e)}")
        return None

    @classmethod
    def get_usd_to_inr_rate(cls) -> float:
        """
        Get current USD to INR exchange rate.

        Returns:
            float: Current USD to INR exchange rate
        """
        rates = cls._get_all_usd_rates()
        rate = rates.get('INR', 83.0)
        logger.info(f"USD to INR rate: {rate}")
        return rate

    @classmethod
    def get_rate_to_inr(cls, currency: str) -> float:
        """
        Get conversion rate from any currency to INR.

        Args:
            currency: Source currency code (e.g. "USD", "EUR", "GBP")

        Returns:
            float: How many INR per 1 unit of the source currency
        """
        if currency == "INR":
            return 1.0

        rates = cls._get_all_usd_rates()
        inr_rate = rates.get('INR', 83.0)

        if currency == "USD":
            return inr_rate

        currency_rate = rates.get(currency)
        if not currency_rate:
            logger.warning(f"No rate found for {currency}, returning 0")
            return 0.0

        # Cross-rate: (INR per USD) / (currency per USD) = INR per currency
        return inr_rate / currency_rate

    @classmethod
    def get_all_rates_to_inr(cls, currencies: list[str]) -> Dict[str, float]:
        """
        Get conversion rates to INR for a list of currencies.

        Args:
            currencies: List of currency codes

        Returns:
            dict: Currency code -> INR rate (e.g. {"USD": 85.2, "EUR": 92.1})
        """
        return {c: cls.get_rate_to_inr(c) for c in currencies}

    @classmethod
    def convert_usd_to_inr(cls, usd_amount: float) -> float:
        """
        Convert USD amount to INR

        Args:
            usd_amount: Amount in USD

        Returns:
            float: Amount in INR
        """
        rate = cls.get_usd_to_inr_rate()
        return usd_amount * rate

    @classmethod
    def clear_cache(cls):
        """Clear the exchange rate cache"""
        cls._rate_cache.clear()
        logger.info("Currency rate cache cleared")


# Convenience functions for easy import
def get_usd_to_inr_rate() -> float:
    """Get current USD to INR exchange rate"""
    return CurrencyConverter.get_usd_to_inr_rate()


def convert_usd_to_inr(usd_amount: float) -> float:
    """Convert USD amount to INR"""
    return CurrencyConverter.convert_usd_to_inr(usd_amount)


def get_rate_to_inr(currency: str) -> float:
    """Get conversion rate from any currency to INR"""
    return CurrencyConverter.get_rate_to_inr(currency)


def get_all_rates_to_inr(currencies: list[str]) -> dict:
    """Get conversion rates to INR for a list of currencies"""
    return CurrencyConverter.get_all_rates_to_inr(currencies)


# Made with Bob