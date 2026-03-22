"""Vision analysis — delegates to vision agent."""

from fastapi import APIRouter, UploadFile, File

from app.agents.vision_agent import VisionAgent

router = APIRouter()


@router.post("/analyze")
async def analyze_chart(image: UploadFile = File(...)):
    raw = await image.read()
    mime = image.content_type or "image/png"
    return await VisionAgent().run({"raw": raw, "mime": mime})
