"""LLM answer generation (Groq) for research queries."""

from __future__ import annotations

import asyncio
import logging
import os

from groq import Groq

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

ANSWER_PROMPT = """You are Inflect, an AI financial research assistant.
You may receive excerpts from SEC filings — ground your answer in them when present.

Rules:
- Be concise — max 180 words
- Cite sources in-line using [1], [2] matching the provided excerpt numbers
- End with a line: SOURCE: SEC Filing | Market Data | Wolfram Alpha (pick one primary)
- Never say BUY or SELL or give price targets
- Finish with: CONFIDENCE: HIGH or MEDIUM or LOW
- Close with: Educational only. Not investment advice."""

_groq_client: Groq | None = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


class AnswerAgent(BaseAgent):
    name = "answer"

    async def run(self, input: dict) -> dict:
        user_content = input["user_content"]
        system_prompt = input.get("system_prompt") or ANSWER_PROMPT
        primary_model = input.get("primary_model", "llama-3.3-70b-versatile")
        fallback_model = input.get("fallback_model", "llama-3.1-8b-instant")

        if not os.getenv("GROQ_API_KEY"):
            return {
                "answer": (
                    "GROQ_API_KEY is not set; cannot run the research pipeline."
                ),
                "error": "missing_groq_key",
            }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        def _call(model: str) -> str:
            client = _get_groq_client()
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.15,
                max_tokens=280,
            )
            return resp.choices[0].message.content or ""

        try:
            text = await asyncio.to_thread(_call, primary_model)
            logger.debug("AnswerAgent: primary model %s succeeded", primary_model)
            return {"answer": text}
        except Exception as primary_err:
            logger.warning(
                "AnswerAgent: primary model %s failed (%s) — retrying with %s",
                primary_model,
                primary_err,
                fallback_model,
            )

        try:
            text = await asyncio.to_thread(_call, fallback_model)
            logger.debug("AnswerAgent: fallback model %s succeeded", fallback_model)
            return {"answer": text}
        except Exception as fallback_err:
            logger.error(
                "AnswerAgent: fallback model %s also failed: %s",
                fallback_model,
                fallback_err,
            )
            return {
                "answer": f"Unable to generate answer: {fallback_err}",
                "error": str(fallback_err),
            }
