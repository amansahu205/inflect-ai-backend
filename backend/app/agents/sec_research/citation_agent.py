"""Format retrieved chunks for the LLM and build accurate citation strings."""

from __future__ import annotations

import re
from typing import Any

from app.agents.base_agent import BaseAgent

_CHUNK_HEAD = 1000
_CHUNK_TAIL = 400
_CHUNK_MAX = _CHUNK_HEAD + _CHUNK_TAIL


def _smart_truncate(text: str) -> str:
    if len(text) <= _CHUNK_MAX:
        return text
    return text[:_CHUNK_HEAD] + "\n...[truncated]...\n" + text[-_CHUNK_TAIL:]


def format_rag_context_static(chunks: list[dict[str, Any]]) -> tuple[str, str | None]:
    if not chunks:
        return "", None

    parts: list[str] = []
    for i, c in enumerate(chunks):
        label = f"[{i + 1}]"
        meta = (
            f"{c.get('form_type', '')} filed {c.get('filing_date', '')} "
            f"- {c.get('section', '')}"
        )
        text = _smart_truncate(c.get("chunk_text") or "")
        parts.append(f"{label} ({meta})\n{text}")

    first = chunks[0]
    fallback_citation = (
        f"{first.get('ticker', '')} {first.get('form_type', '')} - "
        f"{first.get('filing_date', '')} - {first.get('section', '')}"
    )
    return "\n\n".join(parts), fallback_citation


def build_citations_from_answer(
    answer: str,
    chunks: list[dict[str, Any]],
) -> str | None:
    if not chunks or not answer:
        return None

    raw_refs = re.findall(r"\[(\d+)\]", answer)
    cited_indices = sorted(
        {int(r) - 1 for r in raw_refs if r.isdigit()}
    )

    valid = [i for i in cited_indices if 0 <= i < len(chunks)]
    if not valid:
        valid = [0]

    parts: list[str] = []
    for i in valid:
        c = chunks[i]
        parts.append(
            f"{c.get('ticker', '')} {c.get('form_type', '')} - "
            f"{c.get('filing_date', '')} - {c.get('section', '')}"
        )

    return " | ".join(parts) if parts else None


class CitationAgent(BaseAgent):
    name = "citation"

    async def run(self, input: dict) -> dict:
        chunks = input.get("chunks") or []
        answer = input.get("answer")

        rag_block, fallback_citation = format_rag_context_static(chunks)

        if answer:
            citation = build_citations_from_answer(answer, chunks)
        else:
            citation = fallback_citation

        return {
            "rag_block": rag_block,
            "citation": citation,
            "fallback_citation": fallback_citation,
        }
