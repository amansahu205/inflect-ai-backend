"""Thin HTTP layer only: POST /analyze → orchestrator. No LLM or RAG logic here."""

from fastapi import APIRouter

from app.orchestrator.pipeline import run_query_pipeline
from app.schemas.query import QueryRequest

router = APIRouter()


@router.post("/analyze")
async def analyze_query(request: QueryRequest):
    return await run_query_pipeline(request)
