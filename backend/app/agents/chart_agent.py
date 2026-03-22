"""Price history series for chart UI (yfinance)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import yfinance as yf

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


def _chart_series(
    ticker: str,
    metric: str | None = None,
    timeframe: str | None = None,
) -> dict:
    t = ticker.upper().strip()

    try:
        stock = yf.Ticker(t)
        period = "5y" if (timeframe and "5" in timeframe) else "1y"
        hist = stock.history(period=period, interval="1mo")

        if hist is None or hist.empty:
            hist = stock.history(period="6mo", interval="1wk")

        if hist is None or hist.empty:
            raise ValueError(f"yfinance returned no history for {t}")

        x: list[str] = []
        y: list[float] = []
        for idx, row in hist.iterrows():
            x.append(
                idx.strftime("%Y-%m-%d")
                if hasattr(idx, "strftime")
                else str(idx)[:10]
            )
            y.append(round(float(row["Close"]), 4))

        approx_filing_markers: list[str] = []
        if len(x) >= 4:
            approx_filing_markers = [x[len(x) // 4], x[3 * len(x) // 4]]

        return {
            "x": x,
            "y": y,
            "filingDates": approx_filing_markers,
            "approxFilingMarkers": approx_filing_markers,
            "isPlaceholder": False,
        }

    except Exception as e:
        logger.warning(
            "ChartAgent: yfinance failed for %s, placeholder: %s", t, e
        )
        now = datetime.utcnow()
        x = [
            (now - timedelta(days=30 * i)).strftime("%Y-%m-%d")
            for i in range(11, -1, -1)
        ]
        y_vals = [100.0 + i * 0.5 for i in range(12)]

        return {
            "x": x,
            "y": y_vals,
            "filingDates": [x[3], x[8]],
            "approxFilingMarkers": [x[3], x[8]],
            "isPlaceholder": True,
            "error": str(e),
        }


class ChartAgent(BaseAgent):
    name = "chart"

    async def run(self, input: dict) -> dict:
        ticker = input.get("ticker") or ""
        return await asyncio.to_thread(
            _chart_series,
            ticker,
            input.get("metric"),
            input.get("timeframe"),
        )
