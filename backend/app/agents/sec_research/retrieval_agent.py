"""Retrieve SEC filing chunks from Snowflake (keyword / ILIKE)."""

from __future__ import annotations

import asyncio

from app.agents.base_agent import BaseAgent
from app.services.snowflake_rag_service import search_sec_chunks


class RetrievalAgent(BaseAgent):
    name = "sec_retrieval"

    async def run(self, input: dict) -> dict:
        ticker = input.get("ticker")
        query = input["query"]
        limit = int(input.get("limit", 5))
        chunks = await asyncio.to_thread(
            search_sec_chunks, ticker, query, limit
        )
        return {"chunks": chunks}
