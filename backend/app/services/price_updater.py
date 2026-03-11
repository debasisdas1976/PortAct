"""
Price updater service for fetching current prices from various free APIs
"""
import requests
import re
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.asset import Asset, AssetType
from app.core.database import SessionLocal
from datetime import datetime, timezone, date, timedelta
import logging
from app.services.currency_converter import get_usd_to_inr_rate, convert_usd_to_inr, get_rate_to_inr
from app.models.transaction import Transaction, TransactionType
from app.services.xirr_service import calculate_asset_xirr, clamp_xirr
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


def get_stock_price_yahoo_chart(symbol: str) -> tuple:
    """
    Get stock price via Yahoo Finance chart API directly (no yfinance dependency).
    More reliable than yfinance library when it has version-specific bugs.
    Only works with ticker symbols, not ISINs.
    Returns (price, previous_close) tuple or (None, None).
    """
    if _is_isin(symbol):
        return None, None
    yf_symbol = _normalize_nse_symbol(symbol)
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
            price = meta.get('regularMarketPrice')
            previous_close = meta.get('chartPreviousClose') or meta.get('previousClose')
            if price and float(price) > 0:
                logger.info(f"Yahoo chart price for {yf_symbol}: ₹{float(price):.2f}")
                prev = float(previous_close) if previous_close and float(previous_close) > 0 else None
                return float(price), prev
    except Exception as e:
        logger.warning(f"Yahoo chart API failed for {yf_symbol}: {e}")
    return None, None


_yfinance_consecutive_failures = 0
_YFINANCE_CIRCUIT_BREAKER_THRESHOLD = 3  # Skip yfinance after 3 consecutive failures


def get_stock_price_yfinance(symbol: str) -> float:
    """
    Get stock price using yfinance library.
    Handles NSE session management internally.
    Supports both ticker symbols (appends '.NS') and ISIN codes (passed as-is).
    Circuit breaker: skips yfinance after repeated consecutive failures (library-level issue).
    """
    global _yfinance_consecutive_failures
    if _yfinance_consecutive_failures >= _YFINANCE_CIRCUIT_BREAKER_THRESHOLD:
        return None
    try:
        import yfinance as yf

        yf_symbol = _normalize_nse_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)
        info = ticker.fast_info
        price = getattr(info, 'last_price', None)
        if price and price > 0:
            _yfinance_consecutive_failures = 0  # Reset on success
            logger.info(f"yfinance price for {yf_symbol}: ₹{price:.2f}")
            return float(price)
    except Exception as e:
        _yfinance_consecutive_failures += 1
        if _yfinance_consecutive_failures == _YFINANCE_CIRCUIT_BREAKER_THRESHOLD:
            logger.warning(f"yfinance circuit breaker tripped after {_YFINANCE_CIRCUIT_BREAKER_THRESHOLD} failures — skipping for remaining assets")
        else:
            logger.warning(f"yfinance failed for {symbol}: {e}")
    return None


_nse_api_consecutive_failures = 0
_NSE_API_CIRCUIT_BREAKER_THRESHOLD = 2  # Skip NSE direct API after 2 consecutive failures


def get_stock_price_nse(symbol: str) -> tuple:
    """
    Get stock price from NSE India.
    Primary: yfinance library (with circuit breaker).
    Fallback 1: Yahoo Finance chart API (direct HTTP, no yfinance dependency).
    Fallback 2: direct NSE API (with circuit breaker).
    Returns (price, previous_close) tuple or (None, None).
    """
    global _nse_api_consecutive_failures

    # Primary — yfinance (reliable when working)
    price = get_stock_price_yfinance(symbol)
    if price:
        return price, None  # yfinance doesn't give previous_close via fast_info

    # Fallback 1 — Yahoo Finance chart API (direct HTTP call)
    price, previous_close = get_stock_price_yahoo_chart(symbol)
    if price:
        _nse_api_consecutive_failures = 0
        return price, previous_close

    # Fallback 2 — direct NSE API (often blocked without cookies)
    if _nse_api_consecutive_failures >= _NSE_API_CIRCUIT_BREAKER_THRESHOLD:
        return None, None
    nse_symbol = symbol.rsplit('.', 1)[0] if '.' in symbol else symbol
    try:
        session = requests.Session()
        session.get(
            "https://www.nseindia.com",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
            },
            timeout=settings.API_TIMEOUT_SHORT,
        )
        url = f"{settings.NSE_API_BASE}/quote-equity?symbol={nse_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nseindia.com',
        }
        response = session.get(url, headers=headers, timeout=settings.API_TIMEOUT_SHORT)
        if response.status_code == 200:
            data = response.json()
            price = data.get('priceInfo', {}).get('lastPrice')
            prev_close = data.get('priceInfo', {}).get('previousClose')
            if price:
                _nse_api_consecutive_failures = 0
                prev = float(prev_close) if prev_close else None
                return float(price), prev
        _nse_api_consecutive_failures += 1
    except Exception as e:
        _nse_api_consecutive_failures += 1
        if _nse_api_consecutive_failures == _NSE_API_CIRCUIT_BREAKER_THRESHOLD:
            logger.warning(f"NSE API circuit breaker tripped after {_NSE_API_CIRCUIT_BREAKER_THRESHOLD} failures")
        else:
            logger.error(f"NSE fallback failed for {nse_symbol}: {e}")

    return None, None


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
            # Name-based search using token matching for robustness.
            # Tokenization strips noise words (DIRECT/REGULAR PLAN, GROWTH,
            # OPTION, etc.) and stop words (FUND, MUTUAL, SCHEME) so both
            # the search term and scheme names are compared on significant
            # tokens only (e.g. "NIPPON INDIA GILT").
            from app.services.amfi_cache import _tokenize
            search_tokens = _tokenize(identifier)
            want_direct = 'DIRECT' in identifier.upper()
            want_growth = 'GROWTH' in identifier.upper()

            matching_funds = []
            for scheme in AMFICache.get_schemes():
                if scheme.nav <= 0:
                    continue
                # All search tokens must appear in the scheme's tokens
                if search_tokens and search_tokens.issubset(scheme.name_tokens):
                    matching_funds.append(scheme)

            if matching_funds:
                # Prefer Direct over Regular when the search explicitly has "Direct"
                if want_direct:
                    direct = [f for f in matching_funds if f.is_direct]
                    if direct:
                        matching_funds = direct

                # Prefer Growth plans
                if want_growth:
                    growth = [f for f in matching_funds if f.is_growth]
                    if growth:
                        matching_funds = growth

                fund = matching_funds[0]
                logger.info(
                    f"Found NAV for '{identifier}' (token match): "
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


def get_us_stock_price(symbol: str) -> tuple:
    """
    Get US stock price from free APIs
    Uses Yahoo Finance alternative APIs
    Returns (price_usd, previous_close_usd) tuple or (None, None).
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
                    # FMP quote-short doesn't return previousClose; fall through to Yahoo for it
                    # Try Yahoo chart to get previous_close
                    prev_close = None
                    try:
                        yurl = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                        yheaders = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        yresp = requests.get(yurl, headers=yheaders, timeout=10)
                        if yresp.status_code == 200:
                            meta = yresp.json().get('chart', {}).get('result', [{}])[0].get('meta', {})
                            pc = meta.get('chartPreviousClose') or meta.get('previousClose')
                            if pc and float(pc) > 0:
                                prev_close = float(pc)
                    except Exception:
                        pass
                    return float(price), prev_close

        # Fallback to alternative API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
            price = meta.get('regularMarketPrice')
            previous_close = meta.get('chartPreviousClose') or meta.get('previousClose')
            if price:
                logger.info(f"Fetched US stock price for {symbol}: ${price}")
                prev = float(previous_close) if previous_close and float(previous_close) > 0 else None
                return float(price), prev

    except Exception as e:
        logger.error(f"Error fetching US stock price for {symbol}: {str(e)}")

    return None, None


def _batch_fetch_yahoo_spark_prices(symbols: list) -> dict:
    """
    Batch-fetch prices via Yahoo Finance spark API.
    Works for both NSE (.NS suffix) and US ticker symbols.
    Returns {symbol: {"price": float, "previous_close": float|None}} dict.
    Uses range=5d to derive previous trading day's close.
    Chunks into groups of 20 (spark API limit).
    """
    if not symbols:
        return {}
    CHUNK_SIZE = 20
    all_prices = {}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    for i in range(0, len(symbols), CHUNK_SIZE):
        chunk = symbols[i:i + CHUNK_SIZE]
        try:
            symbols_str = ",".join(chunk)
            url = f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={symbols_str}&range=5d&interval=1d"
            response = requests.get(url, headers=headers, timeout=settings.API_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                for sym, info in data.items():
                    close_prices = info.get("close", [])
                    # Filter out None values
                    valid_closes = [c for c in close_prices if c is not None and float(c) > 0]
                    if valid_closes:
                        current = float(valid_closes[-1])
                        previous = float(valid_closes[-2]) if len(valid_closes) >= 2 else None
                        all_prices[sym] = {"price": current, "previous_close": previous}
            else:
                logger.warning(f"Yahoo spark batch returned status {response.status_code} for chunk {i // CHUNK_SIZE + 1}")
        except Exception as e:
            logger.error(f"Yahoo spark batch chunk {i // CHUNK_SIZE + 1} failed: {e}")
    logger.info(f"Yahoo spark batch: fetched {len(all_prices)}/{len(symbols)} prices in {(len(symbols) - 1) // CHUNK_SIZE + 1} chunk(s)")
    return all_prices


def get_crypto_price(symbol: str, coin_id: str = None) -> tuple:
    """
    Get cryptocurrency price in USD from CoinGecko API.
    Returns (price_usd, resolved_coin_id, change_24h) tuple.
    """
    try:
        from app.services.crypto_price_service import get_crypto_price as get_price_from_coingecko, get_coin_id_by_symbol

        # If we have coin_id, use it directly
        if coin_id:
            price_data = get_price_from_coingecko(coin_id)
            if price_data:
                return price_data['price'], coin_id, price_data.get('change_24h')

        # Otherwise, try to get coin_id from symbol
        if symbol:
            resolved_id = get_coin_id_by_symbol(symbol)
            if resolved_id:
                price_data = get_price_from_coingecko(resolved_id)
                if price_data:
                    return price_data['price'], resolved_id, price_data.get('change_24h')

    except Exception as e:
        logger.error(f"Error fetching crypto price for {symbol}: {str(e)}")

    return None, None, None


def _store_day_change(asset: Asset, previous_close: float = None, day_change_pct: float = None):
    """Store day change % in asset.details JSON. Computes from previous_close if day_change_pct not given."""
    if asset.details is None:
        asset.details = {}
    if day_change_pct is not None:
        asset.details['day_change_pct'] = round(day_change_pct, 2)
        flag_modified(asset, 'details')
    elif previous_close and previous_close > 0 and asset.current_price and asset.current_price > 0:
        pct = ((asset.current_price - previous_close) / previous_close) * 100
        asset.details['day_change_pct'] = round(pct, 2)
        asset.details['previous_close'] = round(previous_close, 4)
        flag_modified(asset, 'details')


def _extract_batch_price(cache_entry) -> tuple:
    """Extract (price, previous_close) from batch cache entry (new dict format or legacy float)."""
    if cache_entry is None:
        return None, None
    if isinstance(cache_entry, dict):
        return cache_entry.get("price"), cache_entry.get("previous_close")
    # Legacy float format
    return float(cache_entry), None


def _get_previous_close_from_snapshot(asset_id: int, db: Session) -> float:
    """
    Get the most recent snapshot price for an asset (up to 7 days back).
    Used as fallback for day change when the price API doesn't return previousClose
    (e.g. mutual funds via AMFI, some commodities).
    """
    from app.models.portfolio_snapshot import AssetSnapshot
    try:
        cutoff = date.today() - timedelta(days=7)
        snap = db.query(AssetSnapshot.current_price).filter(
            AssetSnapshot.asset_id == asset_id,
            AssetSnapshot.snapshot_source == "asset",
            AssetSnapshot.snapshot_date >= cutoff,
            AssetSnapshot.snapshot_date < date.today(),
        ).order_by(AssetSnapshot.snapshot_date.desc()).first()
        if snap and snap.current_price and float(snap.current_price) > 0:
            return float(snap.current_price)
    except Exception as e:
        logger.debug(f"Snapshot lookup failed for asset {asset_id}: {e}")
    return None


def update_asset_price(asset: Asset, db: Session, price_cache: dict = None) -> bool:
    """
    Update price for a single asset based on its type
    Returns True if price was successfully updated, False otherwise
    Uses api_symbol if available, otherwise falls back to symbol.
    price_cache: optional pre-fetched prices {"yfinance": {sym: price}, "fmp": {sym: price_usd}}
    """
    yf_cache = (price_cache or {}).get("yfinance", {})
    fmp_cache = (price_cache or {}).get("fmp", {})

    try:
        new_price = None
        previous_close = None
        day_change_pct = None
        error_message = None

        # Use api_symbol if available, otherwise use symbol
        lookup_symbol = asset.api_symbol if asset.api_symbol else asset.symbol

        if asset.asset_type == AssetType.STOCK:
            # Check batch cache first (ISIN key, then normalized symbol key)
            if asset.isin and asset.isin in yf_cache:
                new_price, previous_close = _extract_batch_price(yf_cache[asset.isin])
                if new_price:
                    logger.info(f"Batch cache hit for {asset.symbol} (ISIN {asset.isin}): ₹{new_price:.2f}")
            if not new_price:
                nse_sym = _normalize_nse_symbol(lookup_symbol)
                if nse_sym in yf_cache:
                    new_price, previous_close = _extract_batch_price(yf_cache[nse_sym])
                    if new_price:
                        logger.info(f"Batch cache hit for {asset.symbol} ({nse_sym}): ₹{new_price:.2f}")
            # Fallback to individual API calls
            if not new_price and asset.isin:
                new_price = get_stock_price_yfinance(asset.isin)
                if new_price:
                    logger.info(f"Fetched stock price via ISIN {asset.isin} for {asset.symbol}")
            if not new_price:
                new_price, prev = get_stock_price_nse(lookup_symbol)
                if prev and not previous_close:
                    previous_close = prev
            if not new_price:
                error_message = f"Failed to fetch NSE price for {asset.isin or lookup_symbol}"
            
        elif asset.asset_type == AssetType.US_STOCK:
            # Check batch cache first, then individual API
            us_price_usd = None
            if lookup_symbol in fmp_cache:
                us_price_usd, previous_close = _extract_batch_price(fmp_cache[lookup_symbol])
                if us_price_usd:
                    logger.info(f"Batch cache hit for US stock {lookup_symbol}: ${us_price_usd}")
            if not us_price_usd:
                us_price_usd, prev_usd = get_us_stock_price(lookup_symbol)
                if prev_usd and not previous_close:
                    previous_close = prev_usd
            if us_price_usd:
                # Convert USD to INR
                usd_to_inr = get_usd_to_inr_rate()
                new_price = us_price_usd * usd_to_inr
                if previous_close:
                    previous_close = previous_close * usd_to_inr  # Convert prev close to INR too

                # Update the details JSON with USD price and exchange rate
                if asset.details is None:
                    asset.details = {}
                asset.details['price_usd'] = us_price_usd
                asset.details['usd_to_inr_rate'] = usd_to_inr
                asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                flag_modified(asset, 'details')

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
                if fetched_isin and len(fetched_isin) > 3 and fetched_isin != asset.isin:
                    old_isin = asset.isin
                    asset.isin = fetched_isin
                    logger.info(f"Updated ISIN for {asset.name}: {old_isin} → {fetched_isin}")
            else:
                error_message = f"Failed to fetch NAV for {search_identifier}"
        
        elif asset.asset_type == AssetType.COMMODITY:
            # Commodity ETFs — check fast sources first (caches, AMFI), then slow fallbacks.
            # 1. Batch cache (Yahoo spark)
            if asset.isin and asset.isin in yf_cache:
                new_price, previous_close = _extract_batch_price(yf_cache[asset.isin])
                if new_price:
                    logger.info(f"Batch cache hit for commodity {asset.symbol} (ISIN {asset.isin}): ₹{new_price:.2f}")
            if not new_price:
                nse_sym = _normalize_nse_symbol(lookup_symbol)
                if nse_sym in yf_cache:
                    new_price, previous_close = _extract_batch_price(yf_cache[nse_sym])
                    if new_price:
                        logger.info(f"Batch cache hit for commodity {asset.symbol} ({nse_sym}): ₹{new_price:.2f}")
            # 2. AMFI NAV (instant cached lookup for INF* ISINs — before slow yfinance)
            if not new_price and asset.isin and asset.isin.startswith('INF'):
                result = get_mutual_fund_price(asset.isin)
                if result and result[0]:
                    new_price = result[0]
                    logger.info(f"Fetched commodity price via MF NAV for {asset.symbol} (ISIN: {asset.isin})")
            # 3. FMP/US batch cache, then individual US stock API (for US-listed commodities)
            if not new_price:
                usd_price, prev_usd = None, None
                if lookup_symbol in fmp_cache:
                    usd_price, prev_usd = _extract_batch_price(fmp_cache[lookup_symbol])
                if not usd_price:
                    usd_price, prev_usd = get_us_stock_price(lookup_symbol)
                if usd_price:
                    usd_to_inr = get_usd_to_inr_rate()
                    new_price = usd_price * usd_to_inr
                    if prev_usd:
                        previous_close = prev_usd * usd_to_inr
                    if asset.details is None:
                        asset.details = {}
                    asset.details['price_usd'] = usd_price
                    asset.details['usd_to_inr_rate'] = usd_to_inr
                    asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                    flag_modified(asset, 'details')
                    logger.info(f"Fetched commodity price via US API for {lookup_symbol}: ${usd_price} (₹{new_price:.2f})")
            # 4. Slow fallbacks: yfinance/NSE (only if all fast paths failed)
            if not new_price and asset.isin:
                new_price = get_stock_price_yfinance(asset.isin)
                if new_price:
                    logger.info(f"Fetched commodity price via ISIN {asset.isin} for {asset.symbol}")
            if not new_price:
                new_price, prev = get_stock_price_nse(lookup_symbol)
                if prev and not previous_close:
                    previous_close = prev
            if not new_price:
                error_message = f"Failed to fetch price for commodity {asset.isin or lookup_symbol}"
        
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

            crypto_price_usd, resolved_coin_id, crypto_change_24h = get_crypto_price(asset.symbol, coin_id)
            if crypto_change_24h is not None:
                day_change_pct = crypto_change_24h
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
            # REITs, InvITs, and SGBs are listed on NSE — check batch cache first
            if asset.isin and asset.isin in yf_cache:
                new_price, previous_close = _extract_batch_price(yf_cache[asset.isin])
                if new_price:
                    logger.info(f"Batch cache hit for {asset.asset_type.value} {asset.symbol} (ISIN {asset.isin}): ₹{new_price:.2f}")
            if not new_price:
                nse_sym = _normalize_nse_symbol(lookup_symbol)
                if nse_sym in yf_cache:
                    new_price, previous_close = _extract_batch_price(yf_cache[nse_sym])
                    if new_price:
                        logger.info(f"Batch cache hit for {asset.asset_type.value} {asset.symbol} ({nse_sym}): ₹{new_price:.2f}")
            # Individual fallbacks
            if not new_price and asset.isin:
                new_price = get_stock_price_yfinance(asset.isin)
                if new_price:
                    logger.info(f"Fetched {asset.asset_type.value} price via ISIN {asset.isin} for {asset.symbol}")
            if not new_price:
                new_price, prev = get_stock_price_nse(lookup_symbol)
                if prev and not previous_close:
                    previous_close = prev
            if not new_price:
                error_message = f"Failed to fetch price for {asset.isin or lookup_symbol} ({asset.asset_type.value})"

        elif asset.asset_type in [AssetType.ESOP, AssetType.RSU]:
            # Route based on currency: USD → US stock API, INR → NSE
            currency = (asset.details or {}).get('currency', 'INR')
            if currency == 'USD':
                # Check FMP cache first, then individual API
                us_price_usd = None
                if lookup_symbol in fmp_cache:
                    us_price_usd, previous_close = _extract_batch_price(fmp_cache[lookup_symbol])
                    if us_price_usd:
                        logger.info(f"Batch cache hit for {asset.asset_type.value} {lookup_symbol}: ${us_price_usd}")
                if not us_price_usd:
                    us_price_usd, prev_usd = get_us_stock_price(lookup_symbol)
                    if prev_usd and not previous_close:
                        previous_close = prev_usd
                if us_price_usd:
                    usd_to_inr = get_usd_to_inr_rate()
                    new_price = us_price_usd * usd_to_inr
                    if previous_close:
                        previous_close = previous_close * usd_to_inr
                    if asset.details is None:
                        asset.details = {}
                    asset.details['price_usd'] = us_price_usd
                    asset.details['usd_to_inr_rate'] = usd_to_inr
                    asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                    flag_modified(asset, 'details')
                    logger.info(f"Updated {asset.asset_type.value} {asset.symbol}: ${us_price_usd} (₹{new_price:.2f})")
                else:
                    error_message = f"Failed to fetch US price for {lookup_symbol} ({asset.asset_type.value})"
            else:
                # INR ESOP/RSU — check yfinance cache, then individual
                if asset.isin and asset.isin in yf_cache:
                    new_price, previous_close = _extract_batch_price(yf_cache[asset.isin])
                    if new_price:
                        logger.info(f"Batch cache hit for {asset.asset_type.value} {asset.symbol} (ISIN {asset.isin}): ₹{new_price:.2f}")
                if not new_price:
                    nse_sym = _normalize_nse_symbol(lookup_symbol)
                    if nse_sym in yf_cache:
                        new_price, previous_close = _extract_batch_price(yf_cache[nse_sym])
                        if new_price:
                            logger.info(f"Batch cache hit for {asset.asset_type.value} {asset.symbol} ({nse_sym}): ₹{new_price:.2f}")
                if not new_price and asset.isin:
                    new_price = get_stock_price_yfinance(asset.isin)
                if not new_price:
                    new_price, prev = get_stock_price_nse(lookup_symbol)
                    if prev and not previous_close:
                        previous_close = prev
                if not new_price:
                    error_message = f"Failed to fetch price for {asset.isin or lookup_symbol} ({asset.asset_type.value})"

        if new_price and new_price > 0:
            asset.current_price = new_price
            asset.current_value = asset.quantity * new_price
            asset.calculate_metrics()

            # Store day change % in details JSON
            # Fallback to most recent snapshot price if API didn't provide previousClose
            if not previous_close and day_change_pct is None:
                previous_close = _get_previous_close_from_snapshot(asset.id, db)
            if previous_close:
                _store_day_change(asset, previous_close=previous_close)
            elif day_change_pct is not None:
                _store_day_change(asset, day_change_pct=day_change_pct)

            # Recalculate XIRR if asset has transactions that tally (skip if manually set)
            if not asset.xirr_manual:
                transactions = db.query(Transaction).filter(
                    Transaction.asset_id == asset.id
                ).order_by(Transaction.transaction_date).all()
                if transactions:
                    buy_qty = sum(t.quantity or 0 for t in transactions if t.transaction_type == TransactionType.BUY)
                    sell_qty = sum(t.quantity or 0 for t in transactions if t.transaction_type == TransactionType.SELL)
                    if abs((buy_qty - sell_qty) - (asset.quantity or 0)) < 0.0001:
                        asset.xirr = calculate_asset_xirr(transactions, asset.current_value or 0)
                    else:
                        asset.xirr = None

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


def _update_crypto_assets_batch(crypto_assets: list, db: Session) -> tuple:
    """
    Update all crypto assets in a single batched CoinGecko API call
    to avoid rate-limiting. Returns (updated_count, failed_count).
    """
    from app.services.crypto_price_service import get_multiple_crypto_prices, get_coin_id_by_symbol

    if not crypto_assets:
        return 0, 0

    # Step 1: Resolve coin_id for each asset
    asset_coin_map = {}  # coin_id -> list of assets
    unresolved = []
    for asset in crypto_assets:
        coin_id = (asset.details or {}).get('coin_id') or asset.api_symbol or None
        if not coin_id:
            resolved = get_coin_id_by_symbol(asset.symbol)
            if resolved:
                coin_id = resolved
        if coin_id:
            asset_coin_map.setdefault(coin_id, []).append(asset)
        else:
            unresolved.append(asset)

    # Step 2: Fetch all prices in one API call
    all_coin_ids = list(asset_coin_map.keys())
    prices = get_multiple_crypto_prices(all_coin_ids) if all_coin_ids else {}
    usd_to_inr = get_usd_to_inr_rate()

    updated = 0
    failed = 0

    # Step 3: Apply prices to each asset
    for coin_id, assets_for_coin in asset_coin_map.items():
        price_data = prices.get(coin_id)
        for asset in assets_for_coin:
            try:
                if price_data and price_data['price'] > 0:
                    crypto_price_usd = price_data['price']
                    new_price = crypto_price_usd * usd_to_inr

                    if asset.details is None:
                        asset.details = {}
                    asset.details['price_usd'] = crypto_price_usd
                    asset.details['usd_to_inr_rate'] = usd_to_inr
                    asset.details['last_updated'] = datetime.now(timezone.utc).isoformat()
                    if not asset.details.get('coin_id'):
                        asset.details['coin_id'] = coin_id
                    # Store 24h change from CoinGecko
                    change_24h = price_data.get('change_24h')
                    if change_24h is not None:
                        asset.details['day_change_pct'] = round(change_24h, 2)
                    flag_modified(asset, 'details')

                    asset.current_price = new_price
                    asset.current_value = asset.quantity * new_price
                    asset.calculate_metrics()

                    if not asset.xirr_manual:
                        transactions = db.query(Transaction).filter(
                            Transaction.asset_id == asset.id
                        ).order_by(Transaction.transaction_date).all()
                        if transactions:
                            buy_qty = sum(t.quantity or 0 for t in transactions if t.transaction_type == TransactionType.BUY)
                            sell_qty = sum(t.quantity or 0 for t in transactions if t.transaction_type == TransactionType.SELL)
                            if abs((buy_qty - sell_qty) - (asset.quantity or 0)) < 0.0001:
                                asset.xirr = calculate_asset_xirr(transactions, asset.current_value or 0)
                            else:
                                asset.xirr = None

                    asset.price_update_failed = False
                    asset.last_price_update = datetime.now(timezone.utc)
                    asset.price_update_error = None
                    db.commit()
                    logger.info(f"Updated crypto {asset.symbol}: ${crypto_price_usd} (₹{new_price:.2f} at rate {usd_to_inr})")
                    updated += 1
                else:
                    asset.price_update_failed = True
                    asset.price_update_error = f"Failed to fetch crypto price for {asset.symbol} (coin_id={coin_id})"
                    db.commit()
                    logger.warning(f"No price data for crypto {asset.symbol} (coin_id={coin_id})")
                    failed += 1
            except Exception as e:
                logger.error(f"Error updating crypto {asset.symbol}: {e}")
                try:
                    asset.price_update_failed = True
                    asset.price_update_error = str(e)
                    db.commit()
                except Exception:
                    db.rollback()
                failed += 1

    # Step 4: Mark unresolved assets as failed
    for asset in unresolved:
        try:
            asset.price_update_failed = True
            asset.price_update_error = f"Could not resolve CoinGecko coin_id for symbol {asset.symbol}"
            db.commit()
            logger.warning(f"Could not resolve coin_id for crypto {asset.symbol}")
        except Exception:
            db.rollback()
        failed += 1

    logger.info(f"Crypto batch update: {updated} updated, {failed} failed ({len(all_coin_ids)} unique coins)")
    return updated, failed


def _build_price_cache(assets: list) -> dict:
    """
    Pre-fetch prices in batch via Yahoo Finance spark API.
    Returns {"yfinance": {symbol: price_inr}, "fmp": {symbol: price_usd}}.
    Keys use .NS-suffixed symbols for NSE, raw tickers for US.
    ISINs are excluded (spark API doesn't support them; individual fallbacks handle them).
    """
    # Collect NSE symbols: STOCK, REIT, INVIT, SGB, COMMODITY, ESOP/RSU (INR)
    nse_types = {AssetType.STOCK, AssetType.REIT, AssetType.INVIT,
                 AssetType.SOVEREIGN_GOLD_BOND, AssetType.COMMODITY}
    nse_symbols = set()
    for a in assets:
        if a.asset_type in nse_types:
            lookup = a.api_symbol or a.symbol
            nse_symbols.add(_normalize_nse_symbol(lookup))
        elif a.asset_type in (AssetType.ESOP, AssetType.RSU):
            currency = (a.details or {}).get('currency', 'INR')
            if currency != 'USD':
                lookup = a.api_symbol or a.symbol
                nse_symbols.add(_normalize_nse_symbol(lookup))

    # Collect US symbols: US_STOCK, ESOP/RSU (USD), COMMODITY (non-INF* as fallback)
    us_symbols = set()
    for a in assets:
        if a.asset_type == AssetType.US_STOCK:
            us_symbols.add(a.api_symbol or a.symbol)
        elif a.asset_type == AssetType.COMMODITY:
            # Include commodity symbols as US tickers (handles SLV, GOLD, etc.)
            if not (a.isin and a.isin.startswith('INF')):
                us_symbols.add(a.api_symbol or a.symbol)
        elif a.asset_type in (AssetType.ESOP, AssetType.RSU):
            currency = (a.details or {}).get('currency', 'INR')
            if currency == 'USD':
                us_symbols.add(a.api_symbol or a.symbol)

    # Batch fetch all via Yahoo spark (single API call for NSE, single for US)
    nse_prices = _batch_fetch_yahoo_spark_prices(list(nse_symbols)) if nse_symbols else {}
    us_prices = _batch_fetch_yahoo_spark_prices(list(us_symbols)) if us_symbols else {}

    return {"yfinance": nse_prices, "fmp": us_prices}


def reset_yfinance_circuit_breaker():
    """Reset circuit breakers at the start of a new update session."""
    global _yfinance_consecutive_failures, _nse_api_consecutive_failures
    _yfinance_consecutive_failures = 0
    _nse_api_consecutive_failures = 0


def update_all_prices():
    """
    Update prices for all active market-priced assets.
    Skips non-market assets (PPF, PF, NPS, FD, RD, Insurance, etc.).
    Uses batch API calls where supported: CoinGecko (crypto), yfinance (NSE),
    FMP (US stocks). Individual fallbacks for any batch misses.
    """
    reset_yfinance_circuit_breaker()
    db = SessionLocal()
    try:
        logger.info("Starting price update for market-priced assets...")

        # Only fetch assets that have market price sources
        assets = db.query(Asset).filter(
            Asset.is_active == True,
            Asset.asset_type.in_(PRICE_UPDATABLE_TYPES),
        ).all()

        # Separate crypto assets for batch processing
        crypto_assets = [a for a in assets if a.asset_type == AssetType.CRYPTO]
        other_assets = [a for a in assets if a.asset_type != AssetType.CRYPTO]

        updated_count = 0
        failed_count = 0

        # Batch update crypto (single CoinGecko API call)
        if crypto_assets:
            cu, cf = _update_crypto_assets_batch(crypto_assets, db)
            updated_count += cu
            failed_count += cf

        # Pre-fetch NSE + US prices in batch via Yahoo spark API (2 API calls total)
        price_cache = _build_price_cache(other_assets)

        # Update non-crypto assets (using batch cache with individual fallbacks)
        for asset in other_assets:
            if update_asset_price(asset, db, price_cache):
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
