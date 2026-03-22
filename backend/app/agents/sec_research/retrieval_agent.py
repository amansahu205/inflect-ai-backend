"""Retrieve SEC filing chunks from Snowflake (keyword / ILIKE)."""

from __future__ import annotations

import asyncio
import logging

from app.agents.base_agent import BaseAgent
from app.services.snowflake_rag_service import search_sec_chunks

logger = logging.getLogger(__name__)


class RetrievalAgent(BaseAgent):
    name = "sec_retrieval"

    async def run(self, input: dict) -> dict:
        ticker = input.get("ticker")
        query = input["query"]
        limit = int(input.get("limit", 5))

        try:
            chunks = await asyncio.to_thread(
                search_sec_chunks, ticker, query, limit
            )
            logger.debug(
                "RetrievalAgent: fetched %d chunks for ticker=%s",
                len(chunks),
                ticker,
            )
            return {"chunks": chunks, "retrieval_failed": False, "error": None}

        except Exception as e:
            logger.error(
                "RetrievalAgent: Snowflake query failed for ticker=%s: %s",
                ticker,
                e,
            )
            return {
                "chunks": [],
                "retrieval_failed": True,
                "error": str(e),
            }
