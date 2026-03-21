from fastapi import APIRouter
from pydantic import BaseModel
import yfinance as yf
from datetime import datetime
import random

router = APIRouter()

class TradeRequest(BaseModel):
    ticker: str
    side: str
    quantity: float
    order_type: str = "market"
    user_id: str = ""

@router.post("/execute")
async def execute_trade(order: TradeRequest):
    try:
        stock = yf.Ticker(order.ticker.upper())
        info = stock.fast_info
        price = float(info.last_price or 
                      info.previous_close or 100)

        slippage = price * 0.0005
        fill_price = (
            price + slippage
            if order.side == "buy"
            else price - slippage
        )
        total_value = round(
            fill_price * order.quantity, 2)

        return {
            "ticker": order.ticker.upper(),
            "side": order.side,
            "quantity": order.quantity,
            "fill_price": round(fill_price, 2),
            "total_value": total_value,
            "status": "filled",
            "filled_at": datetime.now().isoformat(),
            "order_id": f"ORD-{random.randint(10000,99999)}"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }
```

---

## FILE 8 — `requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
groq==0.9.0
yfinance==1.2.0
pandas==2.3.2
httpx==0.27.0
python-dotenv==1.0.1
finnhub-python==2.4.20
pinecone-client==6.0.0
python-multipart==0.0.9
pydantic==2.7.0