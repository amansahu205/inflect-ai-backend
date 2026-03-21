from fastapi import APIRouter
from groq import Groq
import yfinance as yf
import os, json

router = APIRouter()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

THESIS_PROMPT = """Generate a trade thesis for {ticker}.
Return ONLY valid JSON, no other text:
{{
  "fundamental": {{
    "signal": "BULLISH|NEUTRAL|BEARISH",
    "reason": "one sentence based on financials",
    "citation": "SEC Filing or Financial Data"
  }},
  "technical": {{
    "signal": "BULLISH|NEUTRAL|BEARISH",
    "reason": "RSI and trend description",
    "rsi": 50
  }},
  "sentiment": {{
    "signal": "POSITIVE|NEUTRAL|NEGATIVE",
    "reason": "recent news and analyst sentiment",
    "score": 0.0
  }},
  "verdict": "HOLD|WATCH|AVOID",
  "confidence": "HIGH|MEDIUM|LOW"
}}
NEVER output BUY or SELL.
Base verdict on real publicly known data."""

def calculate_rsi(ticker: str) -> float:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="14d")
        if len(hist) < 14:
            return 50.0
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).mean()
        loss = -delta.clip(upper=0).mean()
        rs = gain / loss if loss != 0 else 100
        return round(100 - (100 / (1 + rs)), 1)
    except:
        return 50.0

@router.post("/generate")
async def generate_thesis(payload: dict):
    ticker = payload.get("ticker", "").upper()
    if not ticker:
        return {"error": "Ticker required"}

    # Get real market context
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        pe = info.get("trailingPE", "N/A")
        margin = info.get("profitMargins", "N/A")
        revenue_growth = info.get(
            "revenueGrowth", "N/A")
        rsi = calculate_rsi(ticker)
        context = (
            f"P/E: {pe}, "
            f"Profit Margin: {margin}, "
            f"Revenue Growth: {revenue_growth}, "
            f"RSI: {rsi}"
        )
    except:
        context = "Limited data available"
        rsi = 50.0

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",
                 "content": THESIS_PROMPT.format(
                     ticker=ticker)},
                {"role": "user",
                 "content": (
                     f"Ticker: {ticker}\n"
                     f"Market Context: {context}"
                 )}
            ],
            temperature=0.2,
            max_tokens=600
        )

        content = response.choices[0].message.content
        # Clean JSON if wrapped in markdown
        content = content.replace(
            "```json", "").replace("```", "").strip()
        thesis = json.loads(content)
        thesis["ticker"] = ticker
        thesis["technical"]["rsi"] = rsi
        return thesis

    except Exception as e:
        return {
            "ticker": ticker,
            "fundamental": {
                "signal": "NEUTRAL",
                "reason": "Insufficient data",
                "citation": "N/A"
            },
            "technical": {
                "signal": "NEUTRAL",
                "reason": f"RSI: {rsi}",
                "rsi": rsi
            },
            "sentiment": {
                "signal": "NEUTRAL",
                "reason": "Unable to analyze",
                "score": 0.0
            },
            "verdict": "WATCH",
            "confidence": "LOW",
            "error": str(e)
        }