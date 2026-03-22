from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os

# backend/app/main.py -> parents[2] = repo root (inflect/)
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

app = FastAPI(title="Inflect API", version="1.0.0")

_origins = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in _origins.split(",") if o.strip()] or ["*"]


def _combined_cors_origin_regex(raw: str) -> str | None:
    """
    Starlette allows one allow_origin_regex. Accept multiple patterns separated by
    semicolons; join with | so Lovable preview (*.lovableproject.com) and related
    hosts can all match.
    """
    s = raw.strip()
    if not s:
        return None
    parts = [p.strip() for p in s.split(";") if p.strip()]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return "|".join(f"(?:{p})" for p in parts)


_cors_regex = _combined_cors_origin_regex(os.getenv("CORS_ORIGIN_REGEX", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


from app.api.v1.router import router

app.include_router(router, prefix="/api/v1")
