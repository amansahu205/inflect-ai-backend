"""LLM answer generation (Groq) for research queries."""

from __future__ import annotations

import asyncio
import os

from groq import Groq

from app.agents.base_agent import BaseAgent

ANSWER_PROMPT = """You are Inflect, an AI financial research assistant.
You may receive excerpts from SEC filings — ground your answer in them when present.

Rules:
- Be concise — max 180 words
- Cite sources in-line using [1], [2] matching the provided excerpt numbers
- End with a line: SOURCE: SEC Filing | Market Data | Wolfram Alpha (pick one primary)
- Never say BUY or SELL or give price targets
- Finish with: CONFIDENCE: HIGH or MEDIUM or LOW
- Close with: Educational only. Not investment advice."""


class AnswerAgent(BaseAgent):
    name = "answer"

    async def run(self, input: dict) -> dict:
        user_content = input["user_content"]
        system_prompt = input.get("system_prompt") or ANSWER_PROMPT
        primary_model = input.get("primary_model", "llama-3.3-70b-versatile")
        fallback_model = input.get("fallback_model", "llama-3.1-8b-instant")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {
                "answer": (
                    "GROQ_API_KEY is not set; cannot run the research pipeline."
                ),
                "error": "missing_groq_key",
            }

        client = Groq(api_key=api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        def _call(model: str) -> str:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.15,
                max_tokens=500,
            )
            return resp.choices[0].message.content or ""

        try:
            text = await asyncio.to_thread(_call, primary_model)
            return {"answer": text}
        except Exception:
            try:
                text = await asyncio.to_thread(_call, fallback_model)
                return {"answer": text}
            except Exception as e:
                return {"answer": f"Unable to generate answer: {e}", "error": str(e)}
