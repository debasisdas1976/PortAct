"""
Price update endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.scheduler import run_price_update_now
from app.services.crypto_price_service import search_crypto, get_crypto_price, get_coin_id_by_symbol

router = APIRouter()


@router.post("/update")
async def trigger_price_update(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger price update for all assets
    """
    # Run price update in background
    background_tasks.add_task(run_price_update_now)
    
    return {
        "message": "Price update triggered successfully",
        "status": "processing"
    }


@router.get("/status")
async def get_price_update_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get status of price update service
    """
    from app.services.scheduler import scheduler
    
    jobs = scheduler.get_jobs()
    job_info = []
    
    for job in jobs:
        job_info.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": job_info
    }


@router.get("/crypto/search")
async def search_cryptocurrencies(
    query: str = Query(..., min_length=1, description="Search query for cryptocurrency symbol or name"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    current_user: User = Depends(get_current_user)
):
    """
    Search for cryptocurrencies by symbol or name (autocomplete)
    Returns list of matching cryptocurrencies with id, symbol, and name
    """
    results = search_crypto(query, limit)
    return {
        "query": query,
        "results": results,
        "count": len(results)
    }


@router.get("/crypto/{symbol}")
async def get_cryptocurrency_price(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current price and market data for a cryptocurrency by symbol
    """
    # Get coin ID from symbol
    coin_id = get_coin_id_by_symbol(symbol)
    
    if not coin_id:
        return {
            "error": f"Cryptocurrency with symbol '{symbol}' not found",
            "symbol": symbol
        }
    
    # Get price data
    price_data = get_crypto_price(coin_id)
    
    if not price_data:
        return {
            "error": f"Could not fetch price data for '{symbol}'",
            "symbol": symbol,
            "coin_id": coin_id
        }
    
    return {
        "symbol": symbol.upper(),
        "coin_id": coin_id,
        **price_data
    }


@router.get("/crypto/id/{coin_id}")
async def get_cryptocurrency_price_by_id(
    coin_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current price and market data for a cryptocurrency by CoinGecko ID
    """
    price_data = get_crypto_price(coin_id)
    
    if not price_data:
        return {
            "error": f"Could not fetch price data for coin ID '{coin_id}'",
            "coin_id": coin_id
        }
    
    return {
        "coin_id": coin_id,
        **price_data
    }

# Made with Bob
