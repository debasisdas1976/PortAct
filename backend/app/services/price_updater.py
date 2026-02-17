"""
Price updater service for fetching current prices from various free APIs
"""
import requests
import re
from sqlalchemy.orm import Session
from app.models.asset import Asset, AssetType
from app.core.database import SessionLocal
from datetime import datetime
import logging
from app.services.currency_converter import get_usd_to_inr_rate, convert_usd_to_inr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_stock_price_nse(symbol: str) -> float:
    """
    Get stock price from NSE India (free API)
    """
    try:
        # NSE India API endpoint
        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('priceInfo', {}).get('lastPrice')
            if price:
                return float(price)
    except Exception as e:
        logger.error(f"Error fetching NSE price for {symbol}: {str(e)}")
    
    return None


def get_mutual_fund_price(identifier: str) -> tuple:
    """
    Get mutual fund NAV and ISIN from AMFI India (free API)
    Format: Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
    identifier can be either ISIN or fund name
    
    For Direct Plans, prioritizes Growth plans over IDCW/Dividend plans
    
    Returns: (nav, isin) tuple or (None, None) if not found
    """
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
        
        # AMFI India NAV API
        url = "https://www.amfiindia.com/spages/NAVAll.txt"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            lines = response.text.split('\n')
            
            # Check if identifier looks like an ISIN (starts with INF or INE)
            is_isin = identifier.startswith('INF') or identifier.startswith('INE')
            
            # Clean up fund name for better matching
            if not is_isin:
                # Remove common suffixes that might not match exactly
                search_name = identifier.upper()
                search_name = search_name.replace('-E', '').replace(' - E', '')  # Remove -E suffix
                search_name = search_name.replace(' - DIRECT PLAN', '').replace(' -DIRECT PLAN', '')
                search_name = search_name.replace(' - REGULAR PLAN', '').replace(' -REGULAR PLAN', '')
                search_name = search_name.strip()
                # Normalize whitespace - replace multiple spaces with single space
                import re
                search_name = re.sub(r'\s+', ' ', search_name)
            else:
                search_name = identifier
            
            # Collect all matching funds, then prioritize Growth plans
            matching_funds = []
            
            for line in lines:
                # Normalize the line for comparison
                normalized_line = re.sub(r'\s+', ' ', line.upper()) if not is_isin else line.upper()
                
                # Check if identifier is in the line
                if search_name.upper() in normalized_line:
                    parts = line.split(';')
                    # Format: Scheme Code;ISIN1;ISIN2;Scheme Name;NAV;Date
                    if len(parts) >= 6:
                        # If it's an ISIN, check columns 1 and 2
                        if is_isin:
                            if identifier in parts[1] or identifier in parts[2]:
                                nav_str = parts[4].strip()
                                try:
                                    nav = float(nav_str)
                                    if nav > 0:
                                        matching_funds.append({
                                            'name': parts[3],
                                            'nav': nav,
                                            'isin': parts[1] if parts[1] else parts[2],
                                            'is_growth': 'GROWTH' in parts[3].upper()
                                        })
                                except ValueError:
                                    continue
                        else:
                            # If it's a name, check column 3 (scheme name)
                            # Normalize scheme name for comparison
                            scheme_name_normalized = re.sub(r'\s+', ' ', parts[3].upper())
                            if search_name.upper() in scheme_name_normalized:
                                nav_str = parts[4].strip()
                                try:
                                    nav = float(nav_str)
                                    if nav > 0:
                                        matching_funds.append({
                                            'name': parts[3],
                                            'nav': nav,
                                            'isin': parts[1] if parts[1] else parts[2],
                                            'is_growth': 'GROWTH' in parts[3].upper()
                                        })
                                except ValueError:
                                    continue
            
            # If we found matches, prioritize Growth plans
            if matching_funds:
                # First try to find a Growth plan
                growth_funds = [f for f in matching_funds if f['is_growth']]
                if growth_funds:
                    # Return the first Growth plan found
                    fund = growth_funds[0]
                    logger.info(f"Found NAV for '{identifier}' (searched as '{search_name}'): ₹{fund['nav']} ({fund['name'][:60]}) ISIN: {fund['isin']}")
                    return (fund['nav'], fund['isin'])
                else:
                    # If no Growth plan, return the first match
                    fund = matching_funds[0]
                    logger.info(f"Found NAV for '{identifier}' (searched as '{search_name}'): ₹{fund['nav']} ({fund['name'][:60]}) ISIN: {fund['isin']}")
                    return (fund['nav'], fund['isin'])
                    
    except Exception as e:
        logger.error(f"Error fetching MF NAV for {identifier}: {str(e)}")
    
    return (None, None)


def get_gold_price() -> float:
    """
    Get gold price in INR per gram from free API
    """
    try:
        # Gold price API (returns price in USD per ounce)
        url = "https://api.metals.live/v1/spot/gold"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price_usd_per_oz = data[0].get('price')
            
            if price_usd_per_oz:
                # Convert to INR per gram
                # 1 ounce = 31.1035 grams
                # Assuming 1 USD = 83 INR (approximate)
                usd_to_inr = 83
                price_inr_per_gram = (float(price_usd_per_oz) * usd_to_inr) / 31.1035
                return price_inr_per_gram
    except Exception as e:
        logger.error(f"Error fetching gold price: {str(e)}")
    


def get_us_stock_price(symbol: str) -> float:
    """
    Get US stock price from free APIs
    Uses Yahoo Finance alternative APIs
    """
    try:
        # Try using financialmodelingprep API (free tier)
        url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey=demo"
        response = requests.get(url, timeout=10)
        
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

    return None


def get_crypto_price(symbol: str, coin_id: str = None) -> float:
    """
    Get cryptocurrency price in USD from CoinGecko API
    """
    try:
        from app.services.crypto_price_service import get_crypto_price as get_price_from_coingecko, get_coin_id_by_symbol
        
        # If we have coin_id, use it directly
        if coin_id:
            price_data = get_price_from_coingecko(coin_id)
            if price_data:
                return price_data['price']
        
        # Otherwise, try to get coin_id from symbol
        if symbol:
            coin_id = get_coin_id_by_symbol(symbol)
            if coin_id:
                price_data = get_price_from_coingecko(coin_id)
                if price_data:
                    return price_data['price']
                    
    except Exception as e:
        logger.error(f"Error fetching crypto price for {symbol}: {str(e)}")
    
    return None


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
            # Try to get stock price from NSE
            new_price = get_stock_price_nse(lookup_symbol)
            if not new_price:
                error_message = f"Failed to fetch NSE price for {lookup_symbol}"
            
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
                asset.details['last_updated'] = datetime.utcnow().isoformat()
                
                logger.info(f"Updated US stock {asset.symbol}: ${us_price_usd} (₹{new_price:.2f} at rate {usd_to_inr})")
            else:
                error_message = f"Failed to fetch US stock price for {lookup_symbol}"
        
        elif asset.asset_type in [AssetType.EQUITY_MUTUAL_FUND, AssetType.DEBT_MUTUAL_FUND]:
            # Prioritize ISIN if available, then api_symbol, then symbol
            search_identifier = asset.isin if asset.isin else lookup_symbol
            
            # Get mutual fund NAV and ISIN
            result = get_mutual_fund_price(search_identifier)
            if result and result[0]:
                new_price, fetched_isin = result
                # Update ISIN if we don't have it yet
                if not asset.isin and fetched_isin:
                    asset.isin = fetched_isin
                    logger.info(f"Populated ISIN for {asset.symbol}: {fetched_isin}")
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
            # For cash assets (USD cash balances), update the INR value based on current exchange rate
            if asset.details and 'balance_usd' in asset.details:
                usd_balance = asset.details['balance_usd']
                usd_to_inr = get_usd_to_inr_rate()
                new_price = usd_to_inr  # Price per unit (1 USD)
                
                # Update details
                asset.details['usd_to_inr_rate'] = usd_to_inr
                asset.details['last_updated'] = datetime.utcnow().isoformat()
                
                logger.info(f"Updated cash balance: ${usd_balance} at rate {usd_to_inr}")
        
        elif asset.asset_type == AssetType.CRYPTO:
            # Get crypto price in USD and convert to INR
            coin_id = None
            if asset.details and 'coin_id' in asset.details:
                coin_id = asset.details['coin_id']
            
            crypto_price_usd = get_crypto_price(lookup_symbol, coin_id)
            if crypto_price_usd:
                # Convert USD to INR
                usd_to_inr = get_usd_to_inr_rate()
                new_price = crypto_price_usd * usd_to_inr
                
                # Update the details JSON with USD price and exchange rate
                if asset.details is None:
                    asset.details = {}
                asset.details['price_usd'] = crypto_price_usd
                asset.details['usd_to_inr_rate'] = usd_to_inr
                asset.details['last_updated'] = datetime.utcnow().isoformat()
                
                logger.info(f"Updated crypto {asset.symbol}: ${crypto_price_usd} (₹{new_price:.2f} at rate {usd_to_inr})")
            else:
                error_message = f"Failed to fetch crypto price for {lookup_symbol}"
        
        if new_price and new_price > 0:
            asset.current_price = new_price
            asset.current_value = asset.quantity * new_price
            asset.calculate_metrics()
            
            # Mark price update as successful
            asset.price_update_failed = False
            asset.last_price_update = datetime.utcnow()
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
        except:
            db.rollback()
        
        return False


def update_all_prices():
    """
    Update prices for all active assets
    """
    db = SessionLocal()
    try:
        logger.info("Starting price update for all assets...")
        
        # Get all active assets
        assets = db.query(Asset).filter(Asset.is_active == True).all()
        
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
