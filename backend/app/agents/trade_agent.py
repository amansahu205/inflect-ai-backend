"""Paper trade execution (pricing + slippage)."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.finnhub_service import get_price_finnhub


class TradeAgent(BaseAgent):
    name = "trade"

    async def run(self, input: dict) -> dict:
        try:
            ticker = str(input["ticker"]).upper()
            side = str(input["side"])
            quantity = float(input["quantity"])
        except (KeyError, TypeError, ValueError) as e:
            return {"error": str(e), "status": "failed"}

        try:
            price = await asyncio.to_thread(get_price_finnhub, ticker)
            if price <= 0:
                return {
                    "error": "Finnhub returned no current price (check FINNHUB_KEY_1 and symbol)",
                    "status": "failed",
                }

            slippage = price * 0.0005
            fill_price = (
                price + slippage if side == "buy" else price - slippage
            )
            total_value = round(fill_price * quantity, 2)

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
        except Exception as e:
            return {"error": str(e), "status": "failed"}
