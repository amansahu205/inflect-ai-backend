"""Price history series for chart UI (yfinance)."""

from __future__ import annotations

from datetime import datetime, timedelta

import yfinance as yf

from app.agents.base_agent import BaseAgent


def _chart_series(
    ticker: str,
    metric: str | None = None,
    timeframe: str | None = None,
) -> dict:
    t = ticker.upper().strip()
    try:
        stock = yf.Ticker(t)
        period = "1y"
        if timeframe and "5" in timeframe:
            period = "5y"
        hist = stock.history(period=period, interval="1mo")
        if hist is None or hist.empty:
            hist = stock.history(period="6mo", interval="1wk")

        x: list[str] = []
        y: list[float] = []
        for idx, row in hist.iterrows():
            if hasattr(idx, "strftime"):
                x.append(idx.strftime("%Y-%m-%d"))
            else:
                x.append(str(idx)[:10])
            y.append(round(float(row["Close"]), 4))

        filing_dates: list[str] = []
        if len(x) >= 4:
            filing_dates = [x[len(x) // 4], x[3 * len(x) // 4]]

        return {"x": x, "y": y, "filingDates": filing_dates}
    except Exception as e:
        now = datetime.utcnow()
        x = [(now - timedelta(days=30 * i)).strftime("%Y-%m-%d") for i in range(11, -1, -1)]
        y_list = [100.0 + i * 0.5 for i in range(12)]
        return {"x": x, "y": y_list, "filingDates": [x[3], x[8]], "error": str(e)}


class ChartAgent(BaseAgent):
    name = "chart"

    async def run(self, input: dict) -> dict:
        ticker = input.get("ticker") or ""
        return _chart_series(
            ticker,
            input.get("metric"),
            input.get("timeframe"),
        )
