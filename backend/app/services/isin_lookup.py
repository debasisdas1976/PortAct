"""
ISIN Lookup Service
Fetches ISIN codes for stocks, mutual funds, and commodities from various APIs
"""
import logging
import requests
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_isin_from_nse(symbol: str) -> Optional[str]:
    """
    Get ISIN for a stock from NSE
    """
    try:
        # NSE API to get stock info
        url = f"{settings.NSE_API_BASE}/quote-equity?symbol={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            isin = data.get('info', {}).get('isin')
            if isin:
                logger.info(f"Found ISIN for {symbol} from NSE: {isin}")
                return isin
    except Exception as e:
        logger.debug(f"Could not fetch ISIN from NSE for {symbol}: {str(e)}")
    
    return None


def get_isin_from_amfi(fund_name: str) -> Optional[Tuple[str, str]]:
    """
    Get ISIN and exact fund name from AMFI for a mutual fund
    Returns: (isin, exact_fund_name) or (None, None)
    """
    try:
        url = settings.AMFI_NAV_URL
        response = requests.get(url, timeout=settings.API_TIMEOUT)
        
        if response.status_code == 200:
            lines = response.text.split('\n')
            
            # Normalize search term
            search_term = fund_name.upper().strip()
            search_term = search_term.replace(' - DIRECT PLAN', '').replace(' -DIRECT PLAN', '')
            search_term = search_term.replace(' - REGULAR PLAN', '').replace(' -REGULAR PLAN', '')
            search_term = search_term.replace(' - GROWTH', '').replace(' -GROWTH', '')
            search_term = search_term.replace('-E', '').replace(' - E', '')
            
            # Collect matching funds
            matches = []
            
            for line in lines:
                if search_term in line.upper():
                    parts = line.split(';')
                    if len(parts) >= 6:
                        isin = parts[1] if parts[1] else parts[2]
                        scheme_name = parts[3]
                        
                        if isin:
                            is_growth = 'GROWTH' in scheme_name.upper()
                            is_direct = 'DIRECT' in scheme_name.upper()
                            matches.append({
                                'isin': isin,
                                'name': scheme_name,
                                'is_growth': is_growth,
                                'is_direct': is_direct,
                                'score': (2 if is_direct else 0) + (1 if is_growth else 0)
                            })
            
            if matches:
                # Sort by score (Direct Growth > Direct IDCW > Regular Growth > Regular IDCW)
                matches.sort(key=lambda x: x['score'], reverse=True)
                best_match = matches[0]
                logger.info(f"Found ISIN for '{fund_name}' from AMFI: {best_match['isin']} ({best_match['name'][:60]})")
                return (best_match['isin'], best_match['name'])
                
    except Exception as e:
        logger.debug(f"Could not fetch ISIN from AMFI for {fund_name}: {str(e)}")
    
    return (None, None)


def lookup_isin_for_asset(asset_type: str, symbol: str, name: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Lookup ISIN for an asset based on its type
    ISIN is only applicable for Indian Stocks and Mutual Funds
    
    Args:
        asset_type: Type of asset (stock, equity_mutual_fund, etc.)
        symbol: Symbol/ticker of the asset
        name: Name of the asset
    
    Returns:
        (isin, api_symbol) tuple or (None, None) if not found
        api_symbol is the exact name to use for API calls (for mutual funds)
    """
    asset_type_lower = asset_type.lower()
    
    # ISIN is only for Indian Stocks (not commodities, not US stocks)
    if asset_type_lower == 'stock':
        isin = get_isin_from_nse(symbol)
        if isin:
            return (isin, symbol)  # api_symbol is same as symbol for stocks
    
    # ISIN is only for Indian Mutual Funds
    elif asset_type_lower in ['equity_mutual_fund', 'debt_mutual_fund']:
        # Try with symbol first, then name
        isin, exact_name = get_isin_from_amfi(symbol)
        if not isin:
            isin, exact_name = get_isin_from_amfi(name)
        
        if isin:
            # Extract base fund name for api_symbol (before first hyphen)
            api_symbol = exact_name.split(' - ')[0].strip() if exact_name else None
            return (isin, api_symbol)
    
    return (None, None)

# Made with Bob
