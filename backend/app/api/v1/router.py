from fastapi import APIRouter

from app.api.v1 import (
    voice,
    query,
    market,
    trades,
    thesis,
    tts,
    vision,
    rag,
    chart,
)

router = APIRouter()
router.include_router(voice.router, prefix="/voice", tags=["voice"])
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(market.router, prefix="/market", tags=["market"])
router.include_router(trades.router, prefix="/trades", tags=["trades"])
router.include_router(thesis.router, prefix="/thesis", tags=["thesis"])
router.include_router(tts.router, prefix="/tts", tags=["tts"])
router.include_router(vision.router, prefix="/vision", tags=["vision"])
router.include_router(rag.router, prefix="/rag", tags=["rag"])
router.include_router(chart.router, prefix="/chart", tags=["chart"])
