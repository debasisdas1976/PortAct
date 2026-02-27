"""
Price updater service for fetching current prices from various free APIs
"""
import requests
import re
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.asset import Asset, AssetType
from app.core.database import SessionLocal
from datetime import datetime, timezone
import logging
from app.services.currency_converter import get_usd_to_inr_rate, convert_usd_to_inr, get_rate_to_inr
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_isin(identifier: str) -> bool:
    """Check if a string looks like an ISIN (e.g., INE002A01018 for stocks, INF... for MFs)."""
    return bool(identifier and len(identifier) == 12 and identifier[:2].isalpha() and identifier[2:].isalnum())


def _normalize_nse_symbol(symbol: str) -> str:
    """Normalize a ticker symbol to Yahoo Finance NSE format (.NS suffix).
    Converts .BSE → .NS, adds .NS if no suffix, leaves ISINs and .BO as-is."""
    if _is_isin(symbol):
        return symbol
    if symbol.upper().endswith('.BSE'):
        return symbol[:-4] + '.NS'
    if '.' not in symbol:
        return f"{symbol}.NS"
    return symbol


def get_stock_price_yahoo_chart(symbol: str) -> float:
    """
    Get stock price via Yahoo Finance chart API directly (no yfinance dependency).
    More reliable than yfinance library when it has version-specific bugs.
    Only works with ticker symbols, not ISINs.
    """
    if _is_isin(symbol):
        return None
    yf_symbol = _normalize_nse_symbol(symbol)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('chart', {}).get('result', [{}])[0].get('meta', {}).get('regularMarketPrice')
            if price and float(price) > 0:
                logger.info(f"Yahoo chart price for {yf_symbol}: ₹{float(price):.2f}")
                return float(price)
    except Exception as e:
        logger.warning(f"Yahoo chart API failed for {yf_symbol}: {e}")
    return None


def get_stock_price_yfinance(symbol: str) -> float:
    """
    Get stock price using yfinance library.
    Handles NSE session management internally.
    Supports both ticker symbols (appends '.NS') and ISIN codes (passed as-is).
    """
    try:
        import yfinance as yf

        yf_symbol = _normalize_nse_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        info = ticker.fast_info
        price = getattr(info, 'last_price', None)
        if price and price > 0:
            logger.info(f"yfinance price for {yf_symbol}: ₹{price:.2f}")
            return float(price)
    except Exception as e:
        logger.warning(f"yfinance failed for {symbol}: {e}")
    return None


def get_stock_price_nse(symbol: str) -> float:
    """
    Get stock price from NSE India.
    Primary: yfinance library.
    Fallback 1: Yahoo Finance chart API (direct HTTP, no yfinance dependency).
    Fallback 2: direct NSE API.
    """
    # Primary — yfinance (reliable when working)
    price = get_stock_price_yfinance(symbol)
    if price:
        return price

    # Fallback 1 — Yahoo Finance chart API (direct HTTP call)
    price = get_stock_price_yahoo_chart(symbol)
    if price:
        return price

    # Fallback 2 — direct NSE API (often blocked without cookies)
    nse_symbol = symbol.rsplit('.', 1)[0] if '.' in symbol else symbol
    try:
        session = requests.Session()
        session.get(
            "https://www.nseindia.com",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
            },
            timeout=settings.API_TIMEOUT,
        )
        url = f"{settings.NSE_API_BASE}/quote-equity?symbol={nse_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nseindia.com',
        }
        response = session.get(url, headers=headers, timeout=settings.API_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            price = data.get('priceInfo', {}).get('lastPrice')
            if price:
                return float(price)
    except Exception as e:
        logger.error(f"NSE fallback failed for {nse_symbol}: {e}")

    return None


def get_mutual_fund_price(identifier: str) -> tuple:
    """
    Get mutual fund NAV and ISIN from AMFI India (cached data).
    identifier can be either ISIN or fund name.

    For Direct Plans, prioritizes Growth plans over IDCW/Dividend plans.

    Returns: (nav, isin) tuple or (None, None) if not found
    """
    from app.services.amfi_cache import AMFICache

    try:
        # Special mappings for common ETFs that have different names
        name_mappings = {
            'GOLDBEES': 'GOLD BEES',
            'SILVERBEES': 'SILVER BEES',
            'NIFTYBEES': 'NIFTY BEES',
            'BANKBEES': 'BANK BEES',
            'JUNIORBEES': 'JUNIOR BEES',
        }

        # Check if identifier matches any special mapping
        identifier_upper = identifier.upper().replace('-E', '').replace(' ', '')
        for key, value in name_mappings.items():
            if key in identifier_upper:
                identifier = value
                break

        # Check if identifier looks like an ISIN (starts with INF or INE)
        is_isin = identifier.startswith('INF') or identifier.startswith('INE')

        if is_isin:
            # O(1) lookup by ISIN
            scheme = AMFICache.get_by_isin(identifier)
            if scheme and scheme.nav > 0:
                logger.info(f"Found NAV for ISIN '{identifier}': ₹{scheme.nav} ({scheme.scheme_name[:60]})")
                return (scheme.nav, scheme.isin)
        else:
            # Name-based search against cached schemes
            search_name = identifier.upper()
            search_name = search_name.replace('-E', '').replace(' - E', '')
            search_name = search_name.replace(' - DIRECT PLAN', '').replace(' -DIRECT PLAN', '')
            search_name = search_name.replace(' - REGULAR PLAN', '').replace(' -REGULAR PLAN', '')
            search_name = search_name.strip()
            search_name = re.sub(r'\s+', ' ', search_name)

            matching_funds = []
            for scheme in AMFICache.get_schemes():
                # Normalize scheme name for comparison
                scheme_name_normalized = re.sub(r'\s+', ' ', scheme.name_upper)
                if search_name in scheme_name_normalized:
                    if scheme.nav > 0:
                        matching_funds.append(scheme)

            if matching_funds:
                # Prioritize Growth plans
                growth_funds = [f for f in matching_funds if f.is_growth]
                fund = growth_funds[0] if growth_funds else matching_funds[0]
                logger.info(
                    f"Found NAV for '{identifier}' (searched as '{search_name}'): "
                    f"₹{fund.nav} ({fund.scheme_name[:60]}) ISIN: {fund.isin}"
                )
                return (fund.nav, fund.isin)

    except Exception as e:
        logger.error(f"Error fetching MF NAV for {identifier}: {str(e)}")

    return (None, None)


def get_gold_price() -> float:
    """
    Get gold price in INR per gram from free API.
    """
    try:
        url = settings.GOLD_PRICE_API
        response = requests.get(url, timeout=settings.API_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            price_usd_per_oz = data[0].get('price')

            if price_usd_per_oz:
                # 1 troy ounce = 31.1035 grams
                usd_to_inr = get_usd_to_inr_rate()
                price_inr_per_gram = (float(price_usd_per_oz) * usd_to_inr) / 31.1035
                return price_inr_per_gram
    except Exception as e:
        logger.error(f"Error fetching gold price: {e}")

    return None


def get_us_stock_price(symbol: str) -> float:
    """
    Get US stock price from free APIs
    Uses Yahoo Finance alternative APIs
    """
    try:
        # Try using financialmodelingprep API (free tier)
        url = f"{settings.FMP_API_BASE}/quote-short/{symbol}?apikey={settings.FMP_API_KEY}"
        response = requests.get(url, timeout=settings.API_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                price = data[0].get('price')
                if price:
                    logger.info(f"Fetched US stock price for {symbol}: ${price}")
                    return float(price)
        
        # Fallback to alternative API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price = data.get('chart', {}).get('result', [{}])[0].get('meta', {}).get('regularMarketPrice')
            if price:
                logger.info(f"Fetched US stock price for {symbol}: ${price}")
                return float(price)
                
    except Exception as e:
        logger.error(f"Error fetching US stock price for {symbol}: {str(e)}")

    return None


def get_crypto_price(symbol: str, coin_id: str = None) -> tuple:
    """
    Get cryptocurrency price in USD from CoinGecko API.
    Returns (price_usd, resolved_coin_id) so the caller can persist the coin_id.
    """
    try:
        from app.services.crypto_price_service import get_crypto_price as get_price_from_coingecko, get_coin_id_by_symbol

        # If we have coin_id, use it directly
        if coin_id:
            price_data = get_price_from_coingecko(coin_id)
            if price_data:
                return price_data['price'], coin_id

        # Otherwise, try to get coin_id from symbol
        if symbol:
            resolved_id = get_coin_id_by_symbol(symbol)
            if resolved_id:
                price_data = get_price_from_coingecko(resolved_id)
                if price_data:
                    return price_data['price'], resolved_id

    except Exception as e:
        logger.error(f"Error fetching crypto price for {symbol}: {str(e)}")

    return None, None


def update_asset_price(asset: Asset, db: Session) -> bool:
    """
    Update price for a single asset based on its type
    Returns True if price was successfully updated, False otherwise
    Uses api_symbol if available, otherwise falls back to symbol
    """
    try:
        new_price = None
        error_message = None
        
        # Use api_symbol if available, otherwise use symbol
        lookup_symbol = asset.api_symbol if asset.api_symbol else asset.symbol
        
        if asset.asset_type == AssetType.STOCK:
            # Prioritize ISIN for price lookup, fall back to api_symbol/symbol
            if asset.isin:
                new_price = get_stock_price_yfinance(asset.isin)
                if new_price:
                    logger.info(f"Fetched stock price via ISIN {asset.isin} for {asset.symbol}")
            if not new_price:
                new_price = get_stock_price_nse(lookup_symbol)
            if not new_price:
                error_message = f"Failed to fetch NSE price for {asset.isin or lookup_symbol}"
            
        elif asset.asset_type == AssetType.US_STOCK:
            # Get US stock price and convert to INR
            us_price_usd = get_us_stock_price(lookup_symbol)
            if us_price_usd:
                # Convert USD to INR
                usd_to_inr = get_usd_to_inr_rate()
                new_price = us_price_usd * usd_to_inr
                
                # Update the details JSON with USD price and exchange rate
                if asset.details is None:
                    asset.details = {}
                asset.details['price_usd'] = us_price_usd
                asset.details['usd_to_inr_rate'] = usd_to_inr
                asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                logger.info(f"Updated US stock {asset.symbol}: ${us_price_usd} (₹{new_price:.2f} at rate {usd_to_inr})")
            else:
                error_message = f"Failed to fetch US stock price for {lookup_symbol}"
        
        elif asset.asset_type in [AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND, AssetType.HYBRID_MUTUAL_FUND]:
            # Prioritize ISIN if available, then api_symbol, then symbol
            search_identifier = asset.isin if asset.isin else lookup_symbol

            # Get mutual fund NAV and ISIN
            result = get_mutual_fund_price(search_identifier)

            # If ISIN lookup failed, fall back to name-based search (handles stale ISINs)
            if (not result or not result[0]) and asset.isin and asset.name:
                logger.info(f"ISIN {asset.isin} not found in AMFI, trying name: {asset.name}")
                result = get_mutual_fund_price(asset.name)

            if result and result[0]:
                new_price, fetched_isin = result
                # Update ISIN if we don't have one or if the stored one is stale
                if fetched_isin and fetched_isin != asset.isin:
                    old_isin = asset.isin
                    asset.isin = fetched_isin
                    logger.info(f"Updated ISIN for {asset.name}: {old_isin} → {fetched_isin}")
            else:
                error_message = f"Failed to fetch NAV for {search_identifier}"
        
        elif asset.asset_type == AssetType.COMMODITY:
            # For commodity ETFs, try to fetch as stock first if api_symbol is provided
            if lookup_symbol and lookup_symbol != asset.symbol:
                # api_symbol is different, likely a stock symbol for an ETF
                new_price = get_stock_price_nse(lookup_symbol)
                if not new_price:
                    error_message = f"Failed to fetch stock price for commodity ETF {lookup_symbol}"
            # For gold ETFs/funds, get gold price
            elif 'GOLD' in asset.name.upper():
                gold_price = get_gold_price()
                if gold_price:
                    # For gold ETFs, the price is usually per unit
                    # We'll use the gold price as reference
                    new_price = gold_price
                else:
                    error_message = f"Failed to fetch gold price for {asset.name}"
        
        elif asset.asset_type == AssetType.CASH:
            # For cash holdings, update INR value based on current exchange rate
            currency = (asset.details or {}).get('currency', asset.symbol or 'INR')
            original_amount = (asset.details or {}).get('original_amount')

            if currency == 'INR' or not original_amount:
                # INR cash or missing amount — nothing to update
                pass
            else:
                rate = get_rate_to_inr(currency)
                if rate and rate > 0:
                    inr_value = float(original_amount) * rate
                    new_price = inr_value  # quantity is 1, so current_value = new_price
                    if asset.details is None:
                        asset.details = {}
                    asset.details['exchange_rate'] = rate
                    asset.details['last_rate_update'] = datetime.now(timezone.utc).isoformat()
                    flag_modified(asset, 'details')
                    logger.info(f"Updated cash {currency} {original_amount} → ₹{inr_value:.2f} (rate {rate:.4f})")
                else:
                    error_message = f"Failed to fetch exchange rate for {currency}"
        
        elif asset.asset_type == AssetType.CRYPTO:
            # Get crypto price in USD and convert to INR.
            # Resolve coin_id: details > api_symbol (often stores CoinGecko ID) > symbol lookup
            coin_id = (asset.details or {}).get('coin_id') or asset.api_symbol or None

            crypto_price_usd, resolved_coin_id = get_crypto_price(asset.symbol, coin_id)
            if crypto_price_usd:
                # Convert USD to INR
                usd_to_inr = get_usd_to_inr_rate()
                new_price = crypto_price_usd * usd_to_inr

                # Update the details JSON with USD price, exchange rate, and resolved coin_id
                if asset.details is None:
                    asset.details = {}
                asset.details['price_usd'] = crypto_price_usd
                asset.details['usd_to_inr_rate'] = usd_to_inr
                asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                if resolved_coin_id and not asset.details.get('coin_id'):
                    asset.details['coin_id'] = resolved_coin_id
                flag_modified(asset, 'details')

                logger.info(f"Updated crypto {asset.symbol}: ${crypto_price_usd} (₹{new_price:.2f} at rate {usd_to_inr})")
            else:
                error_message = f"Failed to fetch crypto price for {lookup_symbol}"

        elif asset.asset_type in [AssetType.REIT, AssetType.INVIT, AssetType.SOVEREIGN_GOLD_BOND]:
            # REITs, InvITs, and SGBs are listed on NSE — fetch like stocks
            # Prioritize ISIN for price lookup, fall back to api_symbol/symbol
            if asset.isin:
                new_price = get_stock_price_yfinance(asset.isin)
                if new_price:
                    logger.info(f"Fetched {asset.asset_type.value} price via ISIN {asset.isin} for {asset.symbol}")
            if not new_price:
                new_price = get_stock_price_nse(lookup_symbol)
            if not new_price:
                error_message = f"Failed to fetch price for {asset.isin or lookup_symbol} ({asset.asset_type.value})"

        elif asset.asset_type in [AssetType.ESOP, AssetType.RSU]:
            # Route based on currency: USD → US stock API, INR → NSE
            currency = (asset.details or {}).get('currency', 'INR')
            if currency == 'USD':
                us_price_usd = get_us_stock_price(lookup_symbol)
                if us_price_usd:
                    usd_to_inr = get_usd_to_inr_rate()
                    new_price = us_price_usd * usd_to_inr
                    if asset.details is None:
                        asset.details = {}
                    asset.details['price_usd'] = us_price_usd
                    asset.details['usd_to_inr_rate'] = usd_to_inr
                    asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"Updated {asset.asset_type.value} {asset.symbol}: ${us_price_usd} (₹{new_price:.2f})")
                else:
                    error_message = f"Failed to fetch US price for {lookup_symbol} ({asset.asset_type.value})"
            else:
                if asset.isin:
                    new_price = get_stock_price_yfinance(asset.isin)
                if not new_price:
                    new_price = get_stock_price_nse(lookup_symbol)
                if not new_price:
                    error_message = f"Failed to fetch price for {asset.isin or lookup_symbol} ({asset.asset_type.value})"

        if new_price and new_price > 0:
            asset.current_price = new_price
            asset.current_value = asset.quantity * new_price
            asset.calculate_metrics()
            
            # Mark price update as successful
            asset.price_update_failed = False
            asset.last_price_update = datetime.now(timezone.utc)
            asset.price_update_error = None
            
            db.commit()
            logger.info(f"Updated price for {asset.symbol}: ₹{new_price:.2f}")
            return True
        else:
            # Mark price update as failed
            asset.price_update_failed = True
            asset.price_update_error = error_message or f"Could not fetch price for {lookup_symbol} ({asset.asset_type.value})"
            db.commit()
            
            logger.warning(f"Could not fetch price for {lookup_symbol} ({asset.asset_type}): {asset.price_update_error}")
            return False
            
    except Exception as e:
        lookup_symbol = asset.api_symbol if asset.api_symbol else asset.symbol
        error_msg = f"Error updating price for {lookup_symbol}: {str(e)}"
        logger.error(error_msg)
        
        # Mark price update as failed with error
        try:
            asset.price_update_failed = True
            asset.price_update_error = error_msg
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist price update error for {lookup_symbol}: {e}")
            db.rollback()
        
        return False


# Asset types that have market prices to fetch
PRICE_UPDATABLE_TYPES = [
    AssetType.STOCK,
    AssetType.US_STOCK,
    AssetType.EQUITY_MUTUAL_FUND,
    AssetType.HYBRID_MUTUAL_FUND,
    AssetType.DEBT_MUTUAL_FUND,
    AssetType.COMMODITY,
    AssetType.CRYPTO,
    # CASH excluded — updated daily by update_cash_exchange_rates()
    AssetType.REIT,
    AssetType.INVIT,
    AssetType.SOVEREIGN_GOLD_BOND,
    AssetType.ESOP,
    AssetType.RSU,
]


def update_all_prices():
    """
    Update prices for all active market-priced assets.
    Skips non-market assets (PPF, PF, NPS, FD, RD, Insurance, etc.).
    """
    db = SessionLocal()
    try:
        logger.info("Starting price update for market-priced assets...")

        # Only fetch assets that have market price sources
        assets = db.query(Asset).filter(
            Asset.is_active == True,
            Asset.asset_type.in_(PRICE_UPDATABLE_TYPES),
        ).all()
        
        updated_count = 0
        failed_count = 0
        
        for asset in assets:
            if update_asset_price(asset, db):
                updated_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Price update complete. Updated: {updated_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Error in update_all_prices: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    # For testing
    update_all_prices()

# Made with Bob
