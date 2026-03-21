from fastapi import APIRouter
import yfinance as yf
from datetime import datetime
import asyncio

router = APIRouter()

TICKER_LIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "AMD", "INTC",
    "JPM", "GS", "BAC", "V", "MA",
    "WMT", "COST", "MCD", "NKE", "SBUX",
    "JNJ", "UNH", "PFE", "ABBV", "MRK",
    "XOM", "CVX", "CAT", "BA", "RTX"
]

def get_stock_quote(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info

        price = float(info.last_price or 0)
        prev = float(info.previous_close or price)
        change = ((price - prev) / prev * 100) \
                 if prev else 0

        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "change_percent": round(change, 2),
            "direction": "up" if change >= 0 
                        else "down",
            "timestamp": datetime.now().isoformat(),
            "market_open": True
        }
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "price": 0,
            "change_percent": 0,
            "direction": "up",
            "error": str(e)
        }

@router.get("/quote")
async def get_quote(ticker: str):
    return get_stock_quote(ticker.upper())

@router.get("/batch")
async def get_batch_quotes():
    """Returns all 30 tickers in one call"""
    results = []
    for ticker in TICKER_LIST:
        quote = get_stock_quote(ticker)
        results.append(quote)

    return {
        "quotes": results,
        "timestamp": datetime.now().isoformat(),
        "count": len(results)
    }