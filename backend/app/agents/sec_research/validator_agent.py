"""Validation of retrieval results and generated answers."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    name = "validator"

    async def run(self, input: dict) -> dict:
        chunks: list[dict[str, Any]] = input.get("chunks") or []
        answer: str | None = input.get("answer")
        warnings: list[str] = []

        if input.get("retrieval_failed"):
            warnings.append("retrieval_error")
        elif not chunks:
            warnings.append("no_sec_chunks_retrieved")
        else:
            empty_count = sum(
                1 for c in chunks if not (c.get("chunk_text") or "").strip()
            )
            if empty_count == len(chunks):
                warnings.append("all_chunks_empty_text")
            elif empty_count > 0:
                warnings.append(f"{empty_count}_of_{len(chunks)}_chunks_empty")

        if answer:
            answer_str = str(answer).strip()

            if len(answer_str) < 40:
                warnings.append("answer_too_short")

            cited_nums = {
                int(r) for r in re.findall(r"\[(\d+)\]", answer_str)
                if r.isdigit()
            }
            valid_nums = set(range(1, len(chunks) + 1))
            phantom = cited_nums - valid_nums
            if phantom:
                warnings.append(f"phantom_citations:{sorted(phantom)}")
                logger.warning(
                    "ValidatorAgent: phantom chunk refs %s",
                    phantom,
                )

            if re.search(r"\b(BUY|SELL)\b", answer_str, re.IGNORECASE):
                warnings.append("answer_contains_buy_or_sell")
                logger.error("ValidatorAgent: BUY/SELL in answer")

            if "not investment advice" not in answer_str.lower():
                warnings.append("missing_educational_disclaimer")

        ok = len(warnings) == 0
        if warnings:
            logger.info("ValidatorAgent warnings: %s", warnings)

        return {"ok": ok, "warnings": warnings}


def parse_answer_meta(answer: str) -> tuple[str, str | None, str]:
    upper = answer.upper()

    if "SOURCE: SEC" in upper or "SEC FILING" in upper:
        source = "SEC_FILING"
    elif "WOLFRAM" in upper:
        source = "WOLFRAM"
    elif "MARKET DATA" in upper:
        source = "MARKET_DATA"
    else:
        source = "LLM"

    citation: str | None = None
    m = re.search(r"CITATION:\s*(.+?)(?:\n|$)", answer, re.IGNORECASE)
    if m:
        citation = m.group(1).strip()

    if re.search(r"CONFIDENCE:\s*HIGH", answer, re.IGNORECASE):
        confidence_level = "HIGH"
    elif re.search(r"CONFIDENCE:\s*LOW", answer, re.IGNORECASE):
        confidence_level = "LOW"
    else:
        confidence_level = "MEDIUM"

    return source, citation, confidence_level
