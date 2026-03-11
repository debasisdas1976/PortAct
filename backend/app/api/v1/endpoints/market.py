"""
Market data proxy — fetches live prices from Yahoo Finance & CoinGecko
server-side to avoid browser CORS restrictions.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List
import httpx
import asyncio

from app.api.dependencies import get_current_active_user
from app.models.user import User

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
