"""Lightweight validation of retrieval results and generated answers."""

from __future__ import annotations

import re
from typing import Any

from app.agents.base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    name = "validator"

    async def run(self, input: dict) -> dict:
        chunks: list = input.get("chunks") or []
        answer = input.get("answer")
        warnings: list[str] = []
        if not chunks:
            warnings.append("no_sec_chunks_retrieved")
        else:
            empty = sum(
                1 for c in chunks if not (c.get("chunk_text") or "").strip()
            )
            if empty == len(chunks):
                warnings.append("all_chunks_empty_text")

        if answer:
            if len(str(answer).strip()) < 40:
                warnings.append("answer_too_short")

        return {
            "ok": len(warnings) == 0,
            "warnings": warnings,
        }


def parse_answer_meta(answer: str) -> tuple[str, str | None, str]:
    """Extract source label, optional CITATION line, confidence from model text."""
    source = "LLM"
    if "SOURCE: SEC" in answer.upper() or "SEC FILING" in answer.upper():
        source = "SEC_FILING"
    elif "WOLFRAM" in answer.upper():
        source = "WOLFRAM"
    elif "MARKET DATA" in answer.upper():
        source = "MARKET_DATA"

    citation = None
    m = re.search(r"CITATION:\s*(.+?)(?:\n|$)", answer, re.IGNORECASE)
    if m:
        citation = m.group(1).strip()

    confidence_level = "MEDIUM"
    if re.search(r"CONFIDENCE:\s*HIGH", answer, re.IGNORECASE):
        confidence_level = "HIGH"
    elif re.search(r"CONFIDENCE:\s*LOW", answer, re.IGNORECASE):
        confidence_level = "LOW"

    return source, citation, confidence_level
