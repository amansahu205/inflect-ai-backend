"""Format retrieved chunks for the LLM and build primary citation strings."""

from __future__ import annotations

from typing import Any

from app.agents.base_agent import BaseAgent


def format_rag_context_static(chunks: list[dict[str, Any]]) -> tuple[str, str | None]:
    if not chunks:
        return "", None
    parts: list[str] = []
    for i, c in enumerate(chunks):
        label = f"[{i + 1}]"
        meta = (
            f"{c.get('form_type', '')} filed {c.get('filing_date', '')} "
            f"— {c.get('section', '')}"
        )
        text = (c.get("chunk_text") or "")[:1400]
        parts.append(f"{label} ({meta})\n{text}")
    citation = None
    first = chunks[0]
    if first:
        citation = (
            f"{first.get('ticker', '')} {first.get('form_type', '')} · "
            f"{first.get('filing_date', '')} · {first.get('section', '')}"
        )
    return "\n\n".join(parts), citation


class CitationAgent(BaseAgent):
    name = "citation"

    async def run(self, input: dict) -> dict:
        chunks = input.get("chunks") or []
        rag_block, citation = format_rag_context_static(chunks)
        return {"rag_block": rag_block, "citation": citation}
