"""
Market data proxy — fetches live prices from Yahoo Finance & CoinGecko
server-side to avoid browser CORS restrictions.

Also serves macro-economic indicators (RBI repo rate, India CPI, US CPI,
US Unemployment) via get_macro_indicators(), with US data live from BLS.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
import httpx
import asyncio

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.macro_data_service import get_macro_indicators
from app.services.reference_rates_service import get_reference_rates
from app.services.financial_events_service import get_upcoming_financial_events, get_global_financial_news
from app.services.nse_holidays_service import get_nse_holidays

router = APIRouter()

_YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


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


@router.get("/quotes")
async def get_market_quotes(
    symbols: str = Query(..., description="Comma-separated Yahoo Finance symbols, e.g. ^NSEI,GC=F"),
    _current_user: User = Depends(get_current_active_user),
):
    """
    Proxy endpoint that fetches live market quotes from Yahoo Finance.
    Avoids browser CORS restrictions by fetching server-side.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_yahoo_quote(client, sym) for sym in symbol_list]
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
        get_global_financial_news(count=8),
    )
    market_holidays = get_nse_holidays(db, years)
    return {
        "calendar_events": calendar_events,
        "global_news": global_news,
        "market_holidays": market_holidays,
    }
