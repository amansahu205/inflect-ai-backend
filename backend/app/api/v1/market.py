import asyncio
import os
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.schemas.widgets import MarketHistoryResponse, MetricCardResponse
from app.services.market_widgets_service import build_metric_card, fetch_market_history
from app.services.snowflake_rag_service import (
    get_latest_closes_for_tickers,
    snowflake_configured,
)

router = APIRouter()

FINNHUB_KEY = (os.getenv("FINNHUB_KEY") or os.getenv("FINNHUB_KEY_1", "")).strip()
FINNHUB_BASE = "https://finnhub.io/api/v1"
# Yahoo often blocks / rate-limits server IPs; never enable on Cloud Run unless you accept slow requests.
_YF_VOL_BACKFILL = os.getenv("YFINANCE_VOLUME_BACKFILL", "").lower() in ("1", "true", "yes")
_QUOTE_HTTP_TIMEOUT = 5.0
_FINNHUB_CONCURRENCY = 10
_quote_sem: asyncio.Semaphore | None = None

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
        with httpx.Client(timeout=_QUOTE_HTTP_TIMEOUT) as client:
            response = client.get(url, params=params)
            data = response.json()

        price = float(data.get("c", 0) or 0)
        prev = float(data.get("pc", 0) or 0)
        change = float(data.get("dp", 0) or 0)
        high = float(data.get("h", 0) or 0)
        low = float(data.get("l", 0) or 0)

        vol = int(data.get("v", 0) or 0)
        if vol <= 0 and _YF_VOL_BACKFILL:
            vol = _yfinance_latest_volume(ticker)

        return {
            "ticker": ticker.upper(),
            "price": round(price, 2),
            "change_percent": round(change, 2),
            "change": round(change, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "prev_close": round(prev, 2),
            "volume": vol,
            "direction": "up" if change >= 0 else "down",
            "timestamp": datetime.now().isoformat(),
            "market_open": True,
        }
    except Exception as e:
        return _yfinance_fallback(ticker, str(e))


def _yfinance_latest_volume(ticker: str) -> int:
    try:
        import yfinance as yf

        hist = yf.Ticker(ticker).history(period="5d")
        if hist is not None and not hist.empty and "Volume" in hist.columns:
            return int(hist["Volume"].iloc[-1])
    except Exception:
        pass
    return 0


def _snowflake_quote_dict(ticker: str, close: float, prev: float) -> dict:
    pct = ((close - prev) / prev * 100) if prev else 0.0
    return {
        "ticker": ticker.upper(),
        "price": round(close, 2),
        "change_percent": round(pct, 2),
        "change": round(pct, 2),
        "high": round(close, 2),
        "low": round(close, 2),
        "prev_close": round(prev, 2),
        "volume": 0,
        "direction": "up" if pct >= 0 else "down",
        "timestamp": datetime.now().isoformat(),
        "market_open": True,
        "source": "snowflake_prices",
    }


def _merge_snowflake_into_quotes(quotes: list[dict]) -> None:
    """Fill zero-price rows from PRICES (one batch query)."""
    if not snowflake_configured():
        return
    need = [q["ticker"] for q in quotes if float(q.get("price") or 0) <= 0]
    if not need:
        return
    sf = get_latest_closes_for_tickers(need)
    for q in quotes:
        if float(q.get("price") or 0) > 0:
            continue
        pair = sf.get(q["ticker"].upper())
        if not pair:
            continue
        close, prev = pair
        merged = _snowflake_quote_dict(q["ticker"], close, prev)
        q.clear()
        q.update(merged)


def _yfinance_fallback(ticker: str, error: str) -> dict:
    if snowflake_configured():
        sf = get_latest_closes_for_tickers([ticker.upper()])
        pair = sf.get(ticker.upper())
        if pair:
            close, prev = pair
            return _snowflake_quote_dict(ticker, close, prev)
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


async def _quote_with_cap(ticker: str) -> dict:
    global _quote_sem
    if _quote_sem is None:
        _quote_sem = asyncio.Semaphore(_FINNHUB_CONCURRENCY)
    async with _quote_sem:
        return await asyncio.to_thread(get_stock_quote, ticker)


@router.get("/tickers")
async def get_ticker_bar():
    quotes = await asyncio.gather(*(_quote_with_cap(t) for t in TICKER_LIST))
    await asyncio.to_thread(_merge_snowflake_into_quotes, list(quotes))
    return [quote_to_ticker_bar_row(q) for q in quotes]


@router.get("/batch")
async def get_batch_quotes():
    results = list(await asyncio.gather(*(_quote_with_cap(t) for t in TICKER_LIST)))
    await asyncio.to_thread(_merge_snowflake_into_quotes, results)
    return {
        "quotes": results,
        "timestamp": datetime.now().isoformat(),
        "count": len(results),
    }


@router.get("/history", response_model=MarketHistoryResponse)
async def get_market_history(
    ticker: str = Query(..., min_length=1),
    range_key: str = Query("30d", alias="range"),
):
    rk = range_key.lower().strip()
    if rk not in ("7d", "30d", "90d"):
        raise HTTPException(status_code=400, detail="range must be 7d, 30d, or 90d")
    raw = await asyncio.to_thread(fetch_market_history, ticker.upper().strip(), rk)
    return MarketHistoryResponse.model_validate(raw)


@router.get("/metric", response_model=MetricCardResponse)
async def get_metric_card(
    ticker: str = Query(..., min_length=1),
    metric: str = Query(..., min_length=1, description="Metric name or key, e.g. gross_margin, revenue"),
):
    raw = await asyncio.to_thread(build_metric_card, ticker.upper().strip(), metric.strip())
    return MetricCardResponse.model_validate(raw)