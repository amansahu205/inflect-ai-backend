"""Finnhub REST helpers — data only."""

from __future__ import annotations

import os

import httpx


def get_price_finnhub(ticker: str) -> float:
    key = os.getenv("FINNHUB_KEY_1", "")
    r = httpx.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": ticker, "token": key},
        timeout=10,
    )
    return float(r.json().get("c", 0) or 0)
