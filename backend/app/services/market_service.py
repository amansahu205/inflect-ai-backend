"""yfinance quote snapshots — data only (no LLM, no user-facing copy)."""

from __future__ import annotations

import yfinance as yf


def get_quote_snapshot(ticker: str) -> dict:
    """
    Returns numeric quote fields for orchestrator to format.
    Keys: ticker, price, previous_close, change_percent, volume, direction
    """
    t = ticker.upper().strip()
    stock = yf.Ticker(t)
    info = stock.fast_info
    price = float(info.last_price or 0)
    prev = float(info.previous_close or price)
    chg = ((price - prev) / prev * 100) if prev else 0.0
    vol = getattr(info, "last_volume", None) or 0
    try:
        vol = int(vol) if vol else 0
    except (TypeError, ValueError):
        vol = 0
    return {
        "ticker": t,
        "price": price,
        "previous_close": prev,
        "change_percent": chg,
        "volume": vol,
        "direction": "up" if chg >= 0 else "down",
    }


def yfinance_last_price(ticker: str) -> float:
    stock = yf.Ticker(ticker.upper())
    info = stock.fast_info
    return float(info.last_price or info.previous_close or 100)
