"""
Orchestrator: intent classification, SEC retrieval, validation, citation,
optional Wolfram enrichment, answer generation.

Groq is required only for the research path (not for price_check / trade / thesis).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from groq import Groq

from app.agents.sec_research.answer_agent import AnswerAgent
from app.agents.sec_research.citation_agent import CitationAgent, build_citations_from_answer
from app.agents.sec_research.retrieval_agent import RetrievalAgent
from app.agents.sec_research.validator_agent import ValidatorAgent, parse_answer_meta
from app.services.market_service import get_quote_snapshot
from app.services.market_widgets_service import build_metric_card, normalize_metric_key
from app.services.news_service import build_local_context_block
from app.services.wolfram_service import fetch_wolfram_result
from app.schemas.query import QueryRequest

logger = logging.getLogger(__name__)

_retrieval_agent = RetrievalAgent()
_citation_agent = CitationAgent()
_validator_agent = ValidatorAgent()
_answer_agent = AnswerAgent()

INTENT_PROMPT = """You are a financial intent classifier.
Extract structured data from the user message.
Return ONLY valid JSON, no markdown:
{
  "intent_type": "research|price_check|trade|thesis",
  "ticker": "AAPL, TSLA, MSFT, etc. or null — map companies: Apple→AAPL, Tesla→TSLA, Microsoft→MSFT, Google/Alphabet→GOOGL, Amazon→AMZN, Meta/Facebook→META, Nvidia→NVDA",
  "metric": "gross_margin|revenue|eps|pe_ratio or null",
  "timeframe": "Q4 2023|last year or null",
  "confidence": 0.95,
  "side": "buy|sell or null",
  "quantity": 0
}"""

# Company names → symbol when the model omits ticker
_COMPANY_TO_TICKER: tuple[tuple[str, str], ...] = (
    ("apple", "AAPL"),
    ("tesla", "TSLA"),
    ("microsoft", "MSFT"),
    ("google", "GOOGL"),
    ("alphabet", "GOOGL"),
    ("amazon", "AMZN"),
    ("meta", "META"),
    ("facebook", "META"),
    ("nvidia", "NVDA"),
    ("netflix", "NFLX"),
    ("intel", "INTC"),
    ("amd", "AMD"),
    ("jpmorgan", "JPM"),
    ("berkshire", "BRK.B"),
    ("visa", "V"),
    ("mastercard", "MA"),
    ("walmart", "WMT"),
    ("costco", "COST"),
    ("disney", "DIS"),
    ("boeing", "BA"),
)


_SKIP_TICKER_TOKENS = frozenset(
    {"IT", "EPS", "ETF", "IPO", "SEC", "AND", "THE", "FOR", "YOU", "LLC", "USA"}
)


def _infer_ticker_from_text(text: str) -> str | None:
    """Resolve ticker from company name or ALLCAPS symbol (2–5 letters)."""
    if not text:
        return None
    low = text.lower()
    for name, sym in _COMPANY_TO_TICKER:
        if re.search(rf"\b{re.escape(name)}\b", low):
            return sym
    for m in re.finditer(r"\b([A-Z]{2,5})\b", text):
        tok = m.group(1).upper()
        if tok not in _SKIP_TICKER_TOKENS:
            return tok
    return None


def _user_asks_stock_price(text: str) -> bool:
    """True when the user wants a live quote, not fundamentals."""
    t = text.lower()
    if re.search(
        r"\b(margin|margins|revenue|eps\b|p/e|pe ratio|earnings per|dividend yield|"
        r"gross profit|operating income|balance sheet|cash flow)\b",
        t,
    ) and not re.search(r"\b(price|quote|trading|how much)\b", t):
        return False
    return bool(
        re.search(
            r"\b(stock\s+)?price\b|\bquote\b|\btrading\s+at\b|"
            r"how\s+much\s+(?:is|does|are|was)\s+.+\b(?:stock|share|trading)\b|"
            r"what\s+.+\s+price",
            t,
        )
    )


def _extract_json(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    return json.loads(s)


def _default_intent() -> dict[str, Any]:
    return {
        "intent_type": "research",
        "ticker": None,
        "metric": None,
        "timeframe": None,
        "confidence": 0.5,
        "side": None,
        "quantity": 0,
    }


def _classify_intent_sync(user_text: str) -> dict[str, Any]:
    intent = _default_intent()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return intent
    client = Groq(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": INTENT_PROMPT},
                {"role": "user", "content": user_text},
            ],
            temperature=0.0,
            max_tokens=220,
        )
        raw = resp.choices[0].message.content or "{}"
        return {**intent, **_extract_json(raw)}
    except Exception as e:
        logger.warning("Intent classification failed: %s", e)
        return intent


def _format_price_answer(snap: dict[str, Any]) -> tuple[str, str, None]:
    body = (
        f"{snap['ticker']} is at ${snap['price']:.2f}, {snap['direction']} "
        f"{abs(snap['change_percent']):.2f}% vs prior close. "
        f"Volume ~{snap['volume']:,}. "
        f"SOURCE: Market Data\nCONFIDENCE: HIGH\n"
        f"Educational only. Not investment advice."
    )
    return body, "MARKET_DATA", None


def _looks_computational(q: str) -> bool:
    lower = q.lower()
    return bool(
        re.search(
            r"\d+\s*%|\bpe ratio\b|\beps\b|\bcompute\b|\bcalculate\b"
            r"|\bmargin\b|\bratio\b|\bdebt\b|\bgrowth rate\b",
            lower,
        )
        or re.search(r"^what is \d", lower)
    )


def _trade_ack(intent: dict) -> str:
    side = intent.get("side") or "trade"
    qty = intent.get("quantity") or ""
    tk = intent.get("ticker") or "the name"
    return (
        f"I interpreted a {side} request for {qty} shares of {tk}. "
        f"Confirm the order in the trade dialog when it appears. "
        f"I cannot execute trades or give recommendations. "
        f"SOURCE: Market Data\nCONFIDENCE: MEDIUM\n"
        f"Educational only. Not investment advice."
    )


def _thesis_pointer(ticker: str | None) -> str:
    t = ticker or "that company"
    return (
        f"For a structured HOLD / WATCH / AVOID thesis on {t}, "
        f"use the Thesis action in the research panel. "
        f"SOURCE: LLM\nCONFIDENCE: MEDIUM\n"
        f"Educational only. Not investment advice."
    )


def _missing_groq_research_response(
    intent_type: str, ticker: str | None, intent: dict
) -> dict[str, Any]:
    return {
        "intent_type": intent_type,
        "ticker": ticker,
        "metric": intent.get("metric"),
        "timeframe": intent.get("timeframe"),
        "confidence": 0.0,
        "answer": "GROQ_API_KEY is not set; cannot run the research pipeline.",
        "source": "LLM",
        "citation": None,
        "confidence_level": "LOW",
        "validation": {"ok": False, "warnings": ["missing_groq_key"]},
    }


def _merge_metric_into_answer(
    answer: str,
    ticker: str | None,
    metric_field: str | None,
    timeframe: str | None,
) -> str:
    """Prepend factual metric line when LLM is empty, stubbed, or omits the number."""
    if not ticker or not metric_field:
        return answer
    nk = normalize_metric_key(metric_field) or metric_field
    card = build_metric_card(ticker, nk)
    val = str(card.get("value") or "").strip()
    if not val or val == "—":
        return answer
    label = str(card.get("metric") or metric_field)
    period = str(card.get("period") or "TTM")
    ch = card.get("change")
    parts = [
        f"{ticker} {label} is {val} (data period: {period}).",
    ]
    if timeframe:
        parts.append(
            f"You asked about {timeframe}; use SEC excerpts below when they reference that period."
        )
    if ch:
        parts.append(f"Change context: {ch}.")
    opening = " ".join(parts)
    tail = (
        "\nSOURCE: SEC Filing | Market Data\nCONFIDENCE: HIGH\n"
        "Educational only. Not investment advice."
    )
    a = (answer or "").strip()
    low = a.lower()
    if len(a) < 50 or "placeholder" in low or "wire up" in low:
        return opening + tail
    compact_val = re.sub(r"[^\d.]", "", val)[:6]
    compact_a = re.sub(r"[^\d.]", "", a)[:80]
    if compact_val and compact_val in compact_a:
        return a if "investment advice" in low else a + tail
    return opening + "\n\n" + a + ("" if "investment advice" in low else tail)


async def run_query_pipeline(request: QueryRequest) -> dict[str, Any]:
    intent = await asyncio.to_thread(_classify_intent_sync, request.text)

    ticker: str | None = intent.get("ticker") or request.session_context.get("ticker") or None
    if isinstance(ticker, str):
        ticker = ticker.upper().strip() or None
    if not ticker:
        ticker = _infer_ticker_from_text(request.text)

    intent_type: str = intent.get("intent_type") or "research"

    if intent_type not in ("trade", "thesis") and _user_asks_stock_price(request.text) and ticker:
        intent_type = "price_check"

    if intent_type == "price_check" and ticker:
        snap = await asyncio.to_thread(get_quote_snapshot, ticker)
        answer, source, citation = _format_price_answer(snap)
        return {
            "intent_type": intent_type,
            "ticker": ticker,
            "metric": intent.get("metric"),
            "timeframe": intent.get("timeframe"),
            "confidence": float(intent.get("confidence") or 0.9),
            "answer": answer,
            "source": source,
            "citation": citation,
            "confidence_level": "HIGH",
            "validation": {"ok": True, "warnings": []},
        }

    if intent_type == "trade":
        answer = _trade_ack(intent)
        source, citation, conf = parse_answer_meta(answer)
        return {
            "intent_type": intent_type,
            "ticker": ticker,
            "metric": intent.get("metric"),
            "timeframe": intent.get("timeframe"),
            "confidence": float(intent.get("confidence") or 0.75),
            "answer": answer,
            "source": source,
            "citation": citation,
            "confidence_level": conf,
            "validation": {"ok": True, "warnings": []},
        }

    if intent_type == "thesis":
        answer = _thesis_pointer(ticker)
        return {
            "intent_type": intent_type,
            "ticker": ticker,
            "metric": intent.get("metric"),
            "timeframe": intent.get("timeframe"),
            "confidence": float(intent.get("confidence") or 0.7),
            "answer": answer,
            "source": "LLM",
            "citation": None,
            "confidence_level": "MEDIUM",
            "validation": {"ok": True, "warnings": []},
        }

    if not os.getenv("GROQ_API_KEY"):
        logger.error("run_query_pipeline: GROQ_API_KEY is not set (research path)")
        return _missing_groq_research_response(intent_type, ticker, intent)

    ret_out = await _retrieval_agent.run(
        {"ticker": ticker, "query": request.text, "limit": 5}
    )
    chunks: list = ret_out["chunks"]
    retrieval_failed: bool = ret_out.get("retrieval_failed", False)

    async def _maybe_wolfram() -> str:
        if len(chunks) < 2 and _looks_computational(request.text):
            result = await fetch_wolfram_result(request.text)
            return f"\n\nWolfram Alpha result: {result}\n" if result else ""
        return ""

    cit_task = asyncio.create_task(
        _citation_agent.run({"chunks": chunks})
    )
    wolfram_task = asyncio.create_task(_maybe_wolfram())

    cit_out, supplemental = await asyncio.gather(cit_task, wolfram_task)

    rag_block: str = cit_out["rag_block"]
    rag_citation: str | None = cit_out["citation"]

    pre_validation = await _validator_agent.run({
        "chunks": chunks,
        "retrieval_failed": retrieval_failed,
    })
    if not pre_validation["ok"]:
        logger.info(
            "Pre-answer validation warnings: %s", pre_validation["warnings"]
        )

    local_ctx = build_local_context_block(ticker)

    user_content = (
        f"User question: {request.text}\n"
        f"Ticker focus: {ticker or 'none'}\n"
        f"Metric: {intent.get('metric')}\n"
        f"Timeframe: {intent.get('timeframe')}\n\n"
    )
    if rag_block:
        user_content += "SEC filing excerpts:\n" + rag_block + supplemental
    else:
        user_content += (
            "No SEC excerpts retrieved (database offline or no keyword match). "
            "Answer from general public knowledge and note uncertainty."
        ) + supplemental
    user_content += local_ctx

    if ticker and intent.get("metric"):
        try:
            mc = await asyncio.to_thread(
                build_metric_card, ticker, str(intent.get("metric"))
            )
            v = str(mc.get("value") or "").strip()
            if v and v != "—":
                user_content += (
                    f"\n\n[Metric snapshot — cite or reconcile with SEC excerpts] "
                    f"{mc.get('metric')}: {v} ({mc.get('period')}).\n"
                )
        except Exception as e:
            logger.debug("metric snapshot for prompt: %s", e)

    ans_out = await _answer_agent.run({"user_content": user_content})
    answer: str = _merge_metric_into_answer(
        ans_out.get("answer", ""),
        ticker,
        intent.get("metric"),
        intent.get("timeframe"),
    )

    post_validation = await _validator_agent.run({
        "chunks": chunks,
        "answer": answer,
        "retrieval_failed": retrieval_failed,
    })
    if not post_validation["ok"]:
        logger.warning(
            "Post-answer validation warnings: %s", post_validation["warnings"]
        )

    accurate_citation: str | None = build_citations_from_answer(answer, chunks)

    source, inline_citation, confidence_level = parse_answer_meta(answer)
    if chunks:
        final_citation = inline_citation or accurate_citation or rag_citation
        if source == "LLM":
            source = "SEC_FILING"
    else:
        final_citation = inline_citation or rag_citation

    return {
        "intent_type": intent_type,
        "ticker": ticker,
        "metric": intent.get("metric"),
        "timeframe": intent.get("timeframe"),
        "confidence": float(intent.get("confidence") or 0.8),
        "answer": answer,
        "source": source,
        "citation": final_citation,
        "confidence_level": confidence_level,
        "validation": post_validation,
    }
