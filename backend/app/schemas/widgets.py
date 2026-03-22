"""API shapes for MetricCard and price sparklines."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HistoryPoint(BaseModel):
    date: str
    close: float


class MarketHistoryResponse(BaseModel):
    ticker: str
    range: Literal["7d", "30d", "90d"]
    points: list[HistoryPoint]
    sparkline: list[dict[str, float]] = Field(default_factory=list)


class MetricCardResponse(BaseModel):
    metric_key: str
    metric: str
    value: str
    period: str = "TTM"
    change: str | None = None
    change_direction: Literal["up", "down"] | None = None
    source: Literal["SNOWFLAKE", "YFINANCE", "UNAVAILABLE"] = "UNAVAILABLE"
    citation: str | None = None
