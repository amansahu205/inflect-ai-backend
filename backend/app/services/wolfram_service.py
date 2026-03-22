"""Wolfram Alpha short-answer API."""

from __future__ import annotations

import os

import httpx


async def fetch_wolfram_result(query: str) -> str | None:
    app_id = os.getenv("WOLFRAM_APP_ID")
    if not app_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.get(
                "https://api.wolframalpha.com/v1/result",
                params={"appid": app_id, "i": query},
            )
            if r.status_code == 200:
                return r.text.strip()
    except Exception:
        pass
    return None
