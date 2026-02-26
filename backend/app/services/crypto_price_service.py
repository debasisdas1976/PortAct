"""
Crypto Price Service using CoinGecko API
Provides cryptocurrency price data and symbol search/autocomplete
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from app.core.config import settings
from app.models.asset import AssetType

logger = logging.getLogger(__name__)

# Cache for coin list (to avoid repeated API calls)
_coin_list_cache = None
_coin_list_cache_time = None
CACHE_DURATION = timedelta(hours=24)


def get_coin_list() -> List[Dict]:
    """
    Get list of all supported cryptocurrencies from CoinGecko
    Returns: List of dicts with id, symbol, and name
    """
    global _coin_list_cache, _coin_list_cache_time
    
    # Check if cache is valid
    if _coin_list_cache and _coin_list_cache_time:
        if datetime.now() - _coin_list_cache_time < CACHE_DURATION:
            return _coin_list_cache
    
    try:
        response = requests.get(
            f"{settings.COINGECKO_API_BASE}/coins/list",
            timeout=settings.API_TIMEOUT
        )
        response.raise_for_status()
        
        _coin_list_cache = response.json()
        _coin_list_cache_time = datetime.now()
        
        return _coin_list_cache
    except Exception as e:
        logger.error(f"Error fetching coin list from CoinGecko: {e}")
        return _coin_list_cache if _coin_list_cache else []


def search_crypto(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for cryptocurrencies by symbol or name
    Args:
        query: Search query (symbol or name)
        limit: Maximum number of results to return
    Returns: List of matching cryptocurrencies with id, symbol, and name
    """
    if not query or len(query) < 1:
        return []
    
    query_lower = query.lower()
    coin_list = get_coin_list()
    
    # Search by symbol first (exact match)
    exact_matches = [
        coin for coin in coin_list
        if coin['symbol'].lower() == query_lower
    ]
    
    # Then search by symbol prefix
    symbol_matches = [
        coin for coin in coin_list
        if coin['symbol'].lower().startswith(query_lower) and coin not in exact_matches
    ]
    
    # Then search by name
    name_matches = [
        coin for coin in coin_list
        if query_lower in coin['name'].lower() and coin not in exact_matches and coin not in symbol_matches
    ]
    
    # Combine results
    results = exact_matches + symbol_matches + name_matches
    
    return results[:limit]


def get_crypto_price(coin_id: str, vs_currency: str = "usd") -> Optional[Dict]:
    """
    Get current price and market data for a cryptocurrency
    Args:
        coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum')
        vs_currency: Currency to get price in (default: 'usd')
    Returns: Dict with price and market data, or None if error
    """
    try:
        response = requests.get(
            f"{settings.COINGECKO_API_BASE}/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": vs_currency,
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true"
            },
            timeout=settings.API_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        if coin_id in data:
            return {
                "price": data[coin_id].get(vs_currency, 0),
                "market_cap": data[coin_id].get(f"{vs_currency}_market_cap", 0),
                "volume_24h": data[coin_id].get(f"{vs_currency}_24h_vol", 0),
                "change_24h": data[coin_id].get(f"{vs_currency}_24h_change", 0),
                "last_updated": datetime.now().isoformat()
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching price for {coin_id}: {e}")
        return None


def get_multiple_crypto_prices(coin_ids: List[str], vs_currency: str = "usd") -> Dict[str, Dict]:
    """
    Get current prices for multiple cryptocurrencies
    Args:
        coin_ids: List of CoinGecko coin IDs
        vs_currency: Currency to get prices in (default: 'usd')
    Returns: Dict mapping coin_id to price data
    """
    if not coin_ids:
        return {}
    
    try:
        # CoinGecko allows up to 250 IDs per request
        ids_str = ",".join(coin_ids[:250])
        
        response = requests.get(
            f"{settings.COINGECKO_API_BASE}/simple/price",
            params={
                "ids": ids_str,
                "vs_currencies": vs_currency,
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true"
            },
            timeout=settings.API_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        result = {}
        
        for coin_id, coin_data in data.items():
            result[coin_id] = {
                "price": coin_data.get(vs_currency, 0),
                "market_cap": coin_data.get(f"{vs_currency}_market_cap", 0),
                "volume_24h": coin_data.get(f"{vs_currency}_24h_vol", 0),
                "change_24h": coin_data.get(f"{vs_currency}_24h_change", 0),
                "last_updated": datetime.now().isoformat()
            }
        
        return result
    except Exception as e:
        logger.error(f"Error fetching multiple prices: {e}")
        return {}


def get_coin_id_by_symbol(symbol: str) -> Optional[str]:
    """
    Get CoinGecko coin ID from symbol
    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
    Returns: CoinGecko coin ID or None if not found
    """
    coin_list = get_coin_list()
    symbol_lower = symbol.lower()
    
    # Try exact match first
    for coin in coin_list:
        if coin['symbol'].lower() == symbol_lower:
            return coin['id']
    
    return None


def update_crypto_asset_price(asset, db_session):
    """
    Update the current price of a crypto asset
    Args:
        asset: Asset model instance
        db_session: Database session
    """
    if asset.asset_type != AssetType.CRYPTO:
        return False
    
    # Get coin ID from symbol or details
    coin_id = None
    if asset.details and 'coin_id' in asset.details:
        coin_id = asset.details['coin_id']
    elif asset.symbol:
        coin_id = get_coin_id_by_symbol(asset.symbol)
    
    if not coin_id:
        logger.warning(f"Could not find coin ID for asset {asset.id} with symbol {asset.symbol}")
        return False
    
    # Get current price
    price_data = get_crypto_price(coin_id)
    if price_data:
        asset.current_price = price_data['price']
        asset.calculate_metrics()
        
        # Update details with additional market data
        if not asset.details:
            asset.details = {}
        asset.details.update({
            'coin_id': coin_id,
            'market_cap': price_data.get('market_cap'),
            'volume_24h': price_data.get('volume_24h'),
            'change_24h': price_data.get('change_24h'),
            'last_price_update': price_data.get('last_updated')
        })
        
        db_session.commit()
        return True
    
    return False

# Made with Bob