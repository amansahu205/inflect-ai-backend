"""3-signal thesis synthesis (fundamental + technical + sentiment)."""

from __future__ import annotations

import asyncio
import json
import os

import yfinance as yf
from groq import Groq

from app.agents.base_agent import BaseAgent

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
NEVER output BUY or SELL or price targets.
Base verdict on real publicly known data."""

EDU = "Educational only. Not investment advice."


def compute_verdict(thesis: dict) -> str:
    """
    2+ BEARISH → AVOID
    1+ BEARISH → WATCH
    2+ BULLISH → HOLD
    else → WATCH
    (Sentiment: NEGATIVE counts as bearish; POSITIVE as bullish.)
    """
    fund = (thesis.get("fundamental") or {}).get("signal", "NEUTRAL")
    tech = (thesis.get("technical") or {}).get("signal", "NEUTRAL")
    sent = (thesis.get("sentiment") or {}).get("signal", "NEUTRAL")

    bear = 0
    bull = 0
    if fund == "BEARISH":
        bear += 1
    elif fund == "BULLISH":
        bull += 1
    if tech == "BEARISH":
        bear += 1
    elif tech == "BULLISH":
        bull += 1
    if sent == "NEGATIVE":
        bear += 1
    elif sent == "POSITIVE":
        bull += 1

    if bear >= 2:
        return "AVOID"
    if bear >= 1:
        return "WATCH"
    if bull >= 2:
        return "HOLD"
    return "WATCH"


def calculate_rsi(ticker: str) -> float:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="30d")
        if hist is None or len(hist) < 14:
            return 50.0
        delta = hist["Close"].diff()
        gain = delta.clip(lower=0).mean()
        loss = -delta.clip(upper=0).mean()
        if loss == 0 or (gain / loss) is None:
            return 50.0
        rs = gain / loss
        return round(100 - (100 / (1 + rs)), 1)
    except Exception:
        return 50.0


def _generate_thesis_sync(ticker: str) -> dict:
    rsi = calculate_rsi(ticker)
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        pe = info.get("trailingPE", "N/A")
        margin = info.get("profitMargins", "N/A")
        revenue_growth = info.get("revenueGrowth", "N/A")
        context = (
            f"P/E: {pe}, Profit Margin: {margin}, "
            f"Revenue Growth: {revenue_growth}, RSI(14 proxy): {rsi}"
        )
    except Exception:
        context = "Limited data available"

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "ticker": ticker,
            "fundamental": {
                "signal": "NEUTRAL",
                "reason": "GROQ_API_KEY not configured",
                "citation": "N/A",
            },
            "technical": {
                "signal": "NEUTRAL",
                "reason": f"RSI estimate: {rsi}",
                "rsi": rsi,
            },
            "sentiment": {
                "signal": "NEUTRAL",
                "reason": "Unable to analyze without LLM",
                "score": 0.0,
            },
            "verdict": "WATCH",
            "confidence": "LOW",
            "educational_note": EDU,
        }

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": THESIS_PROMPT.format(ticker=ticker)},
                {"role": "user", "content": f"Ticker: {ticker}\nMarket Context: {context}"},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        content = response.choices[0].message.content or "{}"
        content = content.replace("```json", "").replace("```", "").strip()
        thesis = json.loads(content)
        thesis["ticker"] = ticker
        thesis.setdefault("technical", {})["rsi"] = rsi
        thesis["verdict"] = compute_verdict(thesis)
        thesis["educational_note"] = EDU
        return thesis
    except Exception as e:
        return {
            "ticker": ticker,
            "fundamental": {
                "signal": "NEUTRAL",
                "reason": "Insufficient data",
                "citation": "N/A",
            },
            "technical": {
                "signal": "NEUTRAL",
                "reason": f"RSI: {rsi}",
                "rsi": rsi,
            },
            "sentiment": {
                "signal": "NEUTRAL",
                "reason": "Unable to analyze",
                "score": 0.0,
            },
            "verdict": "WATCH",
            "confidence": "LOW",
            "educational_note": EDU,
            "error": str(e),
        }


class ThesisAgent(BaseAgent):
    name = "thesis"

    async def run(self, input: dict) -> dict:
        ticker = (input.get("ticker") or "").upper().strip()
        if not ticker:
            return {"error": "Ticker required"}
        return await asyncio.to_thread(_generate_thesis_sync, ticker)
