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
    Get ISIN and exact fund name from AMFI for a mutual fund.
    Uses cached AMFI data for performance.
    Returns: (isin, exact_fund_name) or (None, None)
    """
    from app.services.amfi_cache import AMFICache

    try:
        schemes = AMFICache.get_schemes()

        # Normalize search term
        search_term = fund_name.upper().strip()
        search_term = search_term.replace(' - DIRECT PLAN', '').replace(' -DIRECT PLAN', '')
        search_term = search_term.replace(' - REGULAR PLAN', '').replace(' -REGULAR PLAN', '')
        search_term = search_term.replace(' - GROWTH', '').replace(' -GROWTH', '')
        search_term = search_term.replace('-E', '').replace(' - E', '')

        # Collect matching funds via substring search
        matches = []

        for scheme in schemes:
            if search_term in scheme.name_upper:
                isin = scheme.isin
                if isin:
                    score = (2 if scheme.is_direct else 0) + (1 if scheme.is_growth else 0)
                    matches.append({
                        'isin': isin,
                        'name': scheme.scheme_name,
                        'is_growth': scheme.is_growth,
                        'is_direct': scheme.is_direct,
                        'score': score,
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
        # Step 1: Try exact substring match (fast, high confidence)
        isin, exact_name = get_isin_from_amfi(symbol)
        if not isin:
            isin, exact_name = get_isin_from_amfi(name)

        # Step 2: Fuzzy match fallback — broker naming often differs from AMFI
        # (e.g. Groww "...Direct Growth" vs AMFI "...Direct Plan - Growth")
        if not isin:
            try:
                from app.services.amfi_fuzzy_match import fuzzy_search_amfi
                results = fuzzy_search_amfi(name, top_n=1)
                if results and results[0]['score'] >= 0.80:
                    isin = results[0]['isin']
                    exact_name = results[0]['scheme_name']
                    logger.info(
                        f"Fuzzy-matched ISIN for '{name[:50]}': "
                        f"{isin} ({exact_name[:50]}) score={results[0]['score']}"
                    )
            except Exception as e:
                logger.debug(f"Fuzzy AMFI match failed for '{name[:50]}': {e}")

        if isin:
            # Extract base fund name for api_symbol (before first hyphen)
            api_symbol = exact_name.split(' - ')[0].strip() if exact_name else None
            return (isin, api_symbol)

    return (None, None)

# Made with Bob
