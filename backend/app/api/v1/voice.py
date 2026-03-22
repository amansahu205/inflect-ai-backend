import asyncio
import logging
import os
import tempfile

import httpx
from fastapi import APIRouter, File, UploadFile
from groq import Groq

logger = logging.getLogger(__name__)

router = APIRouter()


def _stt_groq_allowed() -> bool:
    """
    If ELEVENLABS_API_KEY is set, Groq is off by default so STT stays on ElevenLabs only.
    Set STT_GROQ_FALLBACK=true to allow Whisper when Scribe fails.
    """
    v = os.getenv("STT_GROQ_FALLBACK", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    has_el = bool(os.getenv("ELEVENLABS_API_KEY", "").strip())
    return not has_el


def _extract_elevenlabs_text(payload: dict) -> str:
    text = payload.get("text") or payload.get("transcript") or payload.get("transcription") or ""
    if isinstance(text, dict):
        text = text.get("text", "")
    return str(text).strip()


def _transcribe_elevenlabs_httpx(path: str, filename: str, api_key: str) -> tuple[str, float] | None:
    """REST fallback if the Python SDK is unavailable or fails."""
    model_id = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2").strip() or "scribe_v2"
    try:
        with httpx.Client(timeout=120.0) as client:
            with open(path, "rb") as f:
                files = {"file": (filename or "recording.webm", f, "audio/webm")}
                data: dict[str, str] = {"model_id": model_id}
                lang = os.getenv("ELEVENLABS_STT_LANGUAGE", "").strip()
                if lang:
                    data["language_code"] = lang
                r = client.post(
                    "https://api.elevenlabs.io/v1/speech-to-text",
                    headers={"xi-api-key": api_key},
                    files=files,
                    data=data,
                )
        if r.status_code != 200:
            logger.warning(
                "ElevenLabs HTTP STT failed status=%s body=%s",
                r.status_code,
                (r.text or "")[:800],
            )
            return None
        payload = r.json()
        text = _extract_elevenlabs_text(payload)
        if not text:
            logger.warning("ElevenLabs HTTP STT empty text payload keys=%s", list(payload.keys()))
            return None
        conf = float(payload.get("language_probability", payload.get("confidence", 0.92)) or 0.92)
        return (text, conf)
    except Exception:
        logger.exception("ElevenLabs HTTP STT error")
        return None


def _sdk_stt_result_to_text(result: object) -> str:
    """Normalize Scribe response (single channel vs multichannel)."""
    text = getattr(result, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    transcripts = getattr(result, "transcripts", None)
    if transcripts:
        parts: list[str] = []
        for t in transcripts:
            chunk = getattr(t, "text", None)
            if isinstance(chunk, str) and chunk.strip():
                parts.append(chunk.strip())
        return " ".join(parts).strip()
    return ""


def _transcribe_elevenlabs_sdk(path: str, api_key: str) -> tuple[str, float] | None:
    """Official SDK (recommended) — matches ElevenLabs Scribe docs."""
    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        logger.warning("elevenlabs package not installed; pip install elevenlabs")
        return None

    model_id = os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2").strip() or "scribe_v2"
    try:
        client = ElevenLabs(api_key=api_key)
        with open(path, "rb") as audio_file:
            kwargs: dict = {"file": audio_file, "model_id": model_id}
            lang = os.getenv("ELEVENLABS_STT_LANGUAGE", "").strip()
            if lang:
                kwargs["language_code"] = lang
            result = client.speech_to_text.convert(**kwargs)
        text = _sdk_stt_result_to_text(result)
        if not text:
            return None
        conf = getattr(result, "language_probability", None)
        try:
            conf_f = float(conf) if conf is not None else 0.92
        except (TypeError, ValueError):
            conf_f = 0.92
        return (text, conf_f)
    except Exception:
        logger.exception("ElevenLabs SDK STT error")
        return None


def _transcribe_elevenlabs_sync(path: str, filename: str) -> tuple[str, float] | None:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return None
    out = _transcribe_elevenlabs_sdk(path, api_key)
    if out:
        return out
    return _transcribe_elevenlabs_httpx(path, filename, api_key)


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    tmp_path: str | None = None
    try:
        content = await audio.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        assert tmp_path is not None
        filename = audio.filename or "recording.webm"

        if os.getenv("ELEVENLABS_API_KEY", "").strip():
            el = await asyncio.to_thread(_transcribe_elevenlabs_sync, tmp_path, filename)
            if el:
                return {
                    "transcript": el[0],
                    "confidence": el[1],
                    "provider": "elevenlabs",
                }
            if not _stt_groq_allowed():
                return {
                    "transcript": "",
                    "confidence": 0.0,
                    "provider": "elevenlabs",
                    "error": (
                        "ElevenLabs speech-to-text failed (check ELEVENLABS_API_KEY, Scribe access, "
                        "and credits). Install `elevenlabs` and set ELEVENLABS_STT_MODEL=scribe_v2 if needed."
                    ),
                }

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {
                "transcript": "",
                "confidence": 0.0,
                "error": "No STT provider: set ELEVENLABS_API_KEY and/or GROQ_API_KEY",
            }

        def _groq_sync() -> tuple[str, float]:
            gclient = Groq(api_key=api_key)
            with open(tmp_path, "rb") as f:
                data = f.read()
            transcription = gclient.audio.transcriptions.create(
                file=(filename, data),
                model="whisper-large-v3",
                language="en",
            )
            return (transcription.text, 0.95)

        gr = await asyncio.to_thread(_groq_sync)
        return {"transcript": gr[0], "confidence": gr[1], "provider": "groq"}
    except Exception as e:
        logger.exception("transcribe failed")
        return {"transcript": "", "confidence": 0.0, "error": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
