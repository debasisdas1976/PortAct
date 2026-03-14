"""
Market data proxy — fetches live prices from Yahoo Finance & CoinGecko
server-side to avoid browser CORS restrictions.

Also serves macro-economic indicators (RBI repo rate, India CPI, US CPI,
US Unemployment) via get_macro_indicators(), with US data live from BLS.

Indian index data sources (real-time, no 15-min delay):
  - NIFTY 50 (^NSEI) : NSE allIndices API — real-time, no delay
  - SENSEX   (^BSESN): BSE SensexData API — real-time, no delay
  Both fall back to Yahoo Finance if the primary source fails.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import httpx
import asyncio
import logging

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.macro_data_service import get_macro_indicators
from app.services.mmi_service import get_mmi, get_btc_fng, get_us_fng
from app.services.reference_rates_service import get_reference_rates
from app.services.financial_events_service import get_upcoming_financial_events, get_cached_global_financial_news
from app.services.nse_holidays_service import get_nse_holidays

logger = logging.getLogger(__name__)

router = APIRouter()

_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

_INDIA_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


async def _fetch_yahoo_quote(client: httpx.AsyncClient, symbol: str) -> dict:
    """Fetch a single quote from Yahoo Finance v8 chart API."""
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        "?interval=1d&range=1d&includePrePost=false"
    )
    try:
        r = await client.get(url, headers=_YF_HEADERS, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        price: float = meta["regularMarketPrice"]
        prev = (
            meta.get("chartPreviousClose")
            or meta.get("previousClose")
            or meta.get("regularMarketPreviousClose")
        )
        change_pct = ((price - prev) / prev * 100) if prev else 0.0
        return {
            "symbol": symbol,
            "price": round(price, 4),
            "change_pct": round(change_pct, 4),
            "currency": meta.get("currency", "USD"),
            "ok": True,
        }
    except Exception as exc:
        return {"symbol": symbol, "price": None, "change_pct": None, "currency": None, "ok": False, "error": str(exc)}


async def _fetch_nse_nifty(client: httpx.AsyncClient) -> Optional[dict]:
    """
    Fetch NIFTY 50 in real-time from NSE's allIndices API (no 15-min delay).
    Establishes an NSE session by visiting the homepage first to obtain cookies.
    Returns None on any failure so the caller can fall back to Yahoo Finance.
    """
    try:
        await client.get(
            "https://www.nseindia.com",
            headers={**_INDIA_BROWSER_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"},
            timeout=_TIMEOUT,
        )
        await asyncio.sleep(0.3)
        r = await client.get(
            "https://www.nseindia.com/api/allIndices",
            headers={**_INDIA_BROWSER_HEADERS, "Accept": "application/json, text/plain, */*", "Referer": "https://www.nseindia.com/"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        for item in r.json().get("data", []):
            if item.get("indexSymbol") == "NIFTY 50":
                price = float(item["last"])
                change_pct = float(item.get("percentChange", 0))
                return {
                    "symbol": "^NSEI",
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 4),
                    "currency": "INR",
                    "ok": True,
                }
    except Exception as exc:
        logger.warning("NSE NIFTY 50 real-time fetch failed, will fall back to Yahoo: %s", exc)
    return None


async def _fetch_bse_sensex(client: httpx.AsyncClient) -> Optional[dict]:
    """
    Fetch SENSEX in real-time from BSE's SensexData API (no 15-min delay).
    Returns None on any failure so the caller can fall back to Yahoo Finance.
    """
    try:
        r = await client.get(
            "https://api.bseindia.com/BseIndiaAPI/api/SensexData/w",
            headers={**_INDIA_BROWSER_HEADERS, "Accept": "application/json, text/plain, */*", "Referer": "https://www.bseindia.com/"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        # Response: {"CurrVal":"81234.56","Change":"432.39","PcChange":"0.54",...}
        curr_val = float(str(data["CurrVal"]).replace(",", ""))
        change_pct = float(str(data.get("PcChange", "0")).replace(",", "").replace("%", "").strip())
        return {
            "symbol": "^BSESN",
            "price": round(curr_val, 2),
            "change_pct": round(change_pct, 4),
            "currency": "INR",
            "ok": True,
        }
    except Exception as exc:
        logger.warning("BSE SENSEX real-time fetch failed, will fall back to Yahoo: %s", exc)
    return None


async def _fetch_bitcoin(client: httpx.AsyncClient) -> dict:
    """Fetch Bitcoin price from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
    try:
        r = await client.get(url, timeout=_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        btc = data["bitcoin"]
        return {
            "symbol": "BTC-USD",
            "price": btc["usd"],
            "change_pct": round(btc.get("usd_24h_change", 0), 4),
            "currency": "USD",
            "ok": True,
        }
    except Exception as exc:
        return {"symbol": "BTC-USD", "price": None, "change_pct": None, "currency": "USD", "ok": False, "error": str(exc)}


async def _fetch_quote_for_symbol(client: httpx.AsyncClient, symbol: str) -> dict:
    """
    Route a symbol to the best real-time source, falling back to Yahoo Finance.
    - ^NSEI  (NIFTY 50): NSE allIndices API → Yahoo fallback
    - ^BSESN (SENSEX)  : BSE SensexData API → Yahoo fallback
    - All others       : Yahoo Finance v8 chart API
    """
    if symbol == "^NSEI":
        result = await _fetch_nse_nifty(client)
        if result is not None:
            return result
        logger.info("^NSEI falling back to Yahoo Finance")
    elif symbol == "^BSESN":
        result = await _fetch_bse_sensex(client)
        if result is not None:
            return result
        logger.info("^BSESN falling back to Yahoo Finance")
    return await _fetch_yahoo_quote(client, symbol)


@router.get("/quotes")
async def get_market_quotes(
    symbols: str = Query(..., description="Comma-separated Yahoo Finance symbols, e.g. ^NSEI,GC=F"),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Proxy endpoint that fetches live market quotes server-side (avoids CORS).
    NIFTY 50 and SENSEX use their respective exchange APIs for real-time data
    (no 15-minute delay); all other symbols use Yahoo Finance.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_quote_for_symbol(client, sym) for sym in symbol_list]
        results = await asyncio.gather(*tasks)

    return {"quotes": list(results)}


@router.get("/bitcoin")
async def get_bitcoin_price(
    _current_user: User = Depends(get_current_active_user),
):
    """Proxy endpoint for Bitcoin price from CoinGecko."""
    async with httpx.AsyncClient() as client:
        result = await _fetch_bitcoin(client)
    return result


@router.get("/mmi")
async def get_market_mood_index(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return today's India Market Mood Index (MMI).
    Checks DB first — if today's value is already cached, returns it instantly.
    Otherwise scrapes Tickertape's SSR page, stores the result, then returns it.
    Falls back gracefully — frontend uses computed estimate when source == "error".
    """
    return await asyncio.to_thread(get_mmi, db)


@router.get("/btc-fng")
async def get_btc_fear_greed(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return today's Bitcoin Fear & Greed Index from Alternative.me.
    Checks DB first; fetches and caches on miss.
    Response: { "value": float|None, "sentiment": str|None, "source": str, "date": str }
    """
    return await asyncio.to_thread(get_btc_fng, db)


@router.get("/us-fng")
async def get_us_fear_greed(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return today's US Fear & Greed Index from CNN.
    Checks DB first; fetches and caches on miss.
    Response: { "value": float|None, "sentiment": str|None, "source": str, "date": str }
    """
    return await asyncio.to_thread(get_us_fng, db)


@router.get("/macro-indicators")
async def get_macro_indicator_data(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return macro-economic indicator data from the database:
    - rbi_repo_rate  : RBI repo rate history
    - india_cpi      : India CPI YoY %
    - us_cpi         : US CPI YoY %
    - us_unemployment: US Unemployment rate %
    Data is refreshed daily by the macro_data_refresh scheduler job.
    """
    return get_macro_indicators(db)


@router.get("/reference-rates")
async def get_reference_rate_data(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return current bank FD and government savings scheme rates from the DB.
    - bank_fd      : highest FD rate per bank (general public)
    - govt_schemes : government small savings scheme rates
    Refreshed monthly (bank FD) and quarterly (govt schemes) by the scheduler.
    """
    return get_reference_rates(db)


@router.get("/upcoming-events")
async def get_upcoming_events(
    _current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Return upcoming financial calendar events (India + Global), top global
    financial news headlines, and Indian market (NSE) trading holidays.
    - calendar_events  : list of upcoming scheduled events sorted by date
    - global_news      : top 5 current financial news from Yahoo Finance
    - market_holidays  : NSE trading holidays from DB (current + next year)
    """
    from datetime import date as _date
    today = _date.today()
    # Always return current year; include next year so the calendar shows it
    # when navigating 1–2 months ahead (especially in November–December).
    years = [today.year, today.year + 1]

    calendar_events, global_news = await asyncio.gather(
        asyncio.to_thread(get_upcoming_financial_events, 25),
        get_cached_global_financial_news(count=8),
    )
    market_holidays = get_nse_holidays(db, years)
    return {
        "calendar_events": calendar_events,
        "global_news": global_news,
        "market_holidays": market_holidays,
    }
