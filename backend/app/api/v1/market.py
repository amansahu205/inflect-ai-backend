from fastapi import APIRouter
import httpx
import os
from datetime import datetime

router = APIRouter()

FINNHUB_KEY = os.getenv("FINNHUB_KEY_1", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

TICKER_LIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "AMD", "INTC",
    "JPM", "GS", "BAC", "V", "MA",
    "WMT", "COST", "MCD", "NKE", "SBUX",
    "JNJ", "UNH", "PFE", "ABBV", "MRK",
    "XOM", "CVX", "CAT", "BA", "RTX",
]


def get_stock_quote(ticker: str) -> dict:
    try:
        url = f"{FINNHUB_BASE}/quote"
        params = {
            "symbol": ticker.upper(),
            "token": FINNHUB_KEY
        }
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params)
            data = response.json()

        price = float(data.get("c", 0) or 0)
        prev = float(data.get("pc", 0) or 0)
        change = float(data.get("dp", 0) or 0)
        high = float(data.get("h", 0) or 0)
        low = float(data.get("l", 0) or 0)

        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "change_percent": round(change, 2),
            "change": round(change, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "prev_close": round(prev, 2),
            "volume": 0,
            "direction": "up" if change >= 0 else "down",
            "timestamp": datetime.now().isoformat(),
            "market_open": True,
        }
    except Exception as e:
        return _yfinance_fallback(ticker, str(e))


def _yfinance_fallback(ticker: str, error: str) -> dict:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if hist is not None and not hist.empty:
            price = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else price
            change = ((price - prev) / prev * 100) if prev else 0.0
            return {
                "ticker": ticker.upper(),
                "price": round(price, 2),
                "change_percent": round(change, 2),
                "change": round(change, 2),
                "volume": int(hist['Volume'].iloc[-1]),
                "direction": "up" if change >= 0 else "down",
                "timestamp": datetime.now().isoformat(),
                "market_open": True,
                "source": "yfinance_fallback"
            }
    except Exception:
        pass
    return {
        "ticker": ticker.upper(),
        "price": 0.0,
        "change_percent": 0.0,
        "change": 0.0,
        "volume": 0,
        "direction": "up",
        "timestamp": datetime.now().isoformat(),
        "error": error,
    }


def quote_to_ticker_bar_row(q: dict) -> dict:
    return {
        "ticker": q["ticker"],
        "price": q["price"],
        "change": q.get("change_percent", 0.0),
        "direction": q.get("direction", "up"),
    }


@router.get("/quote")
async def get_quote(ticker: str):
    return get_stock_quote(ticker.upper())


@router.get("/tickers")
async def get_ticker_bar():
    return [quote_to_ticker_bar_row(get_stock_quote(t)) for t in TICKER_LIST]


@router.get("/batch")
async def get_batch_quotes():
    results = [get_stock_quote(t) for t in TICKER_LIST]
    return {
        "quotes": results,
        "timestamp": datetime.now().isoformat(),
        "count": len(results),
    }