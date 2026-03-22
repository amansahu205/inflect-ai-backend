"""3-signal thesis synthesis (fundamental + technical + sentiment)."""

from __future__ import annotations

import asyncio
import json
import os

import yfinance as yf
from groq import Groq

from app.agents.base_agent import BaseAgent
from app.services.snowflake_rag_service import (
    get_fundamentals,
    get_metrics,
    get_news,
)


def _score_sentiment_groq(headlines: list[str]) -> float:
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        headlines_text = "\n".join(headlines[:5])
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Score the overall sentiment of these financial headlines "
                        "for a stock from -1.0 (very negative) to +1.0 (very positive). "
                        "Return ONLY a number.\n\n"
                        f"Headlines:\n{headlines_text}"
                    ),
                }
            ],
            max_tokens=10,
            temperature=0,
        )
        return float(resp.choices[0].message.content.strip())
    except Exception:
        return 0.0


def _snowflake_context_hints(ticker: str) -> str:
    """Optional fundamentals, news, and metrics from Snowflake for LLM context."""
    parts: list[str] = []
    row = get_fundamentals(ticker)
    if row:
        parts.append(f"fundamentals (Snowflake): {str(row)[:1200]}")
    news_rows, headlines = get_news(ticker)
    if news_rows:
        scores = [
            r.get("sentiment", 0)
            for r in news_rows
            if r.get("sentiment") is not None
        ]
        avg_score = sum(scores) / len(scores) if scores else 0
        if avg_score == 0:
            hl = headlines or [str(r.get("headline", "")) for r in news_rows]
            hl = [h for h in hl if h]
            if hl:
                avg_score = _score_sentiment_groq(hl)
        parts.append(
            f"news sentiment (Snowflake): "
            f"avg_score={avg_score:.2f}, "
            f"headlines={[r.get('headline', '')[:80] for r in news_rows[:3]]}"
        )
    m = get_metrics(ticker)
    if m:
        parts.append(f"metrics (Snowflake): {str(m)[:1200]}")
    if not parts:
        return ""
    return "\n\nSnowflake context:\n" + "\n".join(parts)

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
        from app.services.snowflake_rag_service \
            import get_snowflake_connection

        conn = get_snowflake_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    WITH daily AS (
                        SELECT CLOSE_PRICE,
                        LAG(CLOSE_PRICE) OVER
                            (ORDER BY TRADE_DATE) AS prev
                        FROM PRICES
                        WHERE TICKER = %s
                        ORDER BY TRADE_DATE DESC
                        LIMIT 15
                    ),
                    changes AS (
                        SELECT
                            CLOSE_PRICE - prev AS chg
                        FROM daily
                        WHERE prev IS NOT NULL
                    )
                    SELECT
                        AVG(CASE WHEN chg > 0
                            THEN chg ELSE 0 END) AS avg_gain,
                        AVG(CASE WHEN chg < 0
                            THEN ABS(chg) ELSE 0 END) AS avg_loss
                    FROM changes
                    """,
                    (ticker.upper(),),
                )
                row = cursor.fetchone()
                if row and row[1] and row[1] > 0:
                    rs = row[0] / row[1]
                    return round(100 - (100 / (1 + rs)), 1)
                return 50.0
            finally:
                cursor.close()
        finally:
            conn.close()
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
        context += _snowflake_context_hints(ticker)
    except Exception:
        context = "Limited data available" + _snowflake_context_hints(ticker)

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
                {
                    "role": "user",
                    "content": f"Ticker: {ticker}\nMarket Context: {context}",
                },
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
