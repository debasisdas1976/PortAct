"""
Currency conversion service for fetching real-time exchange rates
"""
import requests
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CurrencyConverter:
    """Service to fetch and cache currency conversion rates"""
    
    # Cache for exchange rates (in-memory, could be moved to Redis for production)
    _rate_cache = {}
    _cache_duration = timedelta(hours=1)  # Cache rates for 1 hour
    
    @classmethod
    def get_usd_to_inr_rate(cls) -> float:
        """
        Get current USD to INR exchange rate
        Uses free API from exchangerate-api.com or falls back to a default rate
        
        Returns:
            float: Current USD to INR exchange rate
        """
        cache_key = "USD_INR"
        
        # Check cache first
        if cache_key in cls._rate_cache:
            cached_data = cls._rate_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < cls._cache_duration:
                logger.info(f"Using cached USD to INR rate: {cached_data['rate']}")
                return cached_data['rate']
        
        # Try to fetch from API
        try:
            rate = cls._fetch_rate_from_api()
            if rate:
                cls._rate_cache[cache_key] = {
                    'rate': rate,
                    'timestamp': datetime.now()
                }
                logger.info(f"Fetched fresh USD to INR rate: {rate}")
                return rate
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {str(e)}")
        
        # Fallback to default rate if API fails
        default_rate = 83.0  # Approximate USD to INR rate
        logger.warning(f"Using default USD to INR rate: {default_rate}")
        return default_rate
    
    @classmethod
    def _fetch_rate_from_api(cls) -> Optional[float]:
        """
        Fetch exchange rate from free API
        
        Returns:
            Optional[float]: Exchange rate or None if fetch fails
        """
        try:
            # Using exchangerate-api.com free tier (no API key required for basic usage)
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = data.get('rates', {}).get('INR')
            
            if rate:
                return float(rate)
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing API response: {str(e)}")
        
        # Try alternative API
        try:
            # Using fixer.io alternative (open.er-api.com)
            url = "https://open.er-api.com/v6/latest/USD"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            rate = data.get('rates', {}).get('INR')
            
            if rate:
                return float(rate)
                
        except Exception as e:
            logger.error(f"Alternative API also failed: {str(e)}")
        
        return None
    
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


# Convenience function for easy import
def get_usd_to_inr_rate() -> float:
    """Get current USD to INR exchange rate"""
    return CurrencyConverter.get_usd_to_inr_rate()


def convert_usd_to_inr(usd_amount: float) -> float:
    """Convert USD amount to INR"""
    return CurrencyConverter.convert_usd_to_inr(usd_amount)


# Made with Bob