"""Shared request models (avoid circular imports with API routers)."""

from pydantic import BaseModel


class TradeRequest(BaseModel):
    ticker: str
    side: str
    quantity: float
    order_type: str = "market"
    user_id: str = ""
