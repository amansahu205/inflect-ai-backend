"""Paper trade execution (pricing + slippage)."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.finnhub_service import get_price_finnhub

logger = logging.getLogger(__name__)
_VALID_SIDES = frozenset({"buy", "sell"})


class TradeAgent(BaseAgent):
    name = "trade"

    async def run(self, input: dict) -> dict:
        try:
            ticker = str(input["ticker"]).upper().strip()
            side = str(input["side"]).lower().strip()
            quantity = float(input["quantity"])
        except (KeyError, TypeError, ValueError) as e:
            return {"error": f"Invalid input: {e}", "status": "failed"}

        if not ticker:
            return {"error": "Ticker must not be empty", "status": "failed"}
        if side not in _VALID_SIDES:
            return {
                "error": f"side must be buy or sell, got {side!r}",
                "status": "failed",
            }
        if quantity <= 0:
            return {
                "error": f"Quantity must be positive, got {quantity}",
                "status": "failed",
            }

        try:
            price = await asyncio.to_thread(get_price_finnhub, ticker)
        except Exception as e:
            logger.error("TradeAgent Finnhub %s: %s", ticker, e)
            return {"error": str(e), "status": "failed"}

        if price <= 0:
            return {
                "error": (
                    "Finnhub returned no current price "
                    "(check FINNHUB_KEY_1 and symbol)"
                ),
                "status": "failed",
            }

        slippage = price * 0.0005
        fill_price = price + slippage if side == "buy" else price - slippage
        total_value = round(fill_price * quantity, 2)
        logger.info(
            "TradeAgent %s %s qty=%s @ %s", side, ticker, quantity, fill_price
        )

        return {
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "fill_price": round(fill_price, 2),
            "total_value": total_value,
            "status": "filled",
            "filled_at": datetime.now().isoformat(),
            "order_id": f"ORD-{random.randint(10000, 99999)}",
        }
