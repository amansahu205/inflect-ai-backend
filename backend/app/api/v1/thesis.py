"""Thesis generation — delegates to thesis agent."""

from fastapi import APIRouter

from app.agents.thesis_agent import ThesisAgent

router = APIRouter()


@router.post("/generate")
async def generate_thesis_route(payload: dict):
    return await ThesisAgent().run(payload)
