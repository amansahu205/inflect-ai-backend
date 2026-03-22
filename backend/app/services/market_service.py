"""Quote snapshots for orchestrator — Finnhub-first via market.get_stock_quote (Cloud Run–safe)."""

from __future__ import annotations

import yfinance as yf


def get_quote_snapshot(ticker: str) -> dict:
    """
    Returns numeric quote fields for orchestrator to format.
    Keys: ticker, price, previous_close, change_percent, volume, direction
    """
    from app.api.v1.market import get_stock_quote

    q = get_stock_quote(ticker)
    price = float(q.get("price") or 0)
    prev = float(q.get("prev_close") or q.get("previous_close") or price)
    chg = float(q.get("change_percent") or 0)
    vol = int(q.get("volume") or 0)
    return {
        "ticker": q.get("ticker") or ticker.upper().strip(),
        "price": price,
        "previous_close": prev,
        "change_percent": chg,
        "volume": vol,
        "direction": q.get("direction") or ("up" if chg >= 0 else "down"),
    }


def yfinance_last_price(ticker: str) -> float:
    stock = yf.Ticker(ticker.upper())
    info = stock.fast_info
    return float(info.last_price or info.previous_close or 100)
