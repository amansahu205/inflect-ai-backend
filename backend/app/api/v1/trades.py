"""Paper trades — delegates to trade agent."""

from fastapi import APIRouter

from app.agents.trade_agent import TradeAgent
from app.schemas.trade import TradeRequest

router = APIRouter()


@router.post("/execute")
async def execute_trade(order: TradeRequest):
    return await TradeAgent().run(order.model_dump())
