from fastapi import APIRouter, UploadFile, File
from groq import Groq
import httpx
import os
import tempfile

router = APIRouter()


async def _transcribe_elevenlabs(path: str, filename: str) -> tuple[str, float] | None:
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(path, "rb") as f:
                files = {"file": (filename or "audio.webm", f, "audio/webm")}
                data = {"model_id": "scribe_v1"}
                r = await client.post(
                    "https://api.elevenlabs.io/v1/speech-to-text",
                    headers={"xi-api-key": key},
                    files=files,
                    data=data,
                )
            if r.status_code != 200:
                return None
            payload = r.json()
            text = (
                payload.get("text")
                or payload.get("transcript")
                or (payload.get("transcription") or "")
            )
            if isinstance(text, dict):
                text = text.get("text", "")
            if not text:
                return None
            conf = float(payload.get("confidence", 0.92) or 0.92)
            return (text.strip(), conf)
    except Exception:
        return None


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
        el = await _transcribe_elevenlabs(tmp_path, audio.filename or "recording.webm")
        if el:
            return {"transcript": el[0], "confidence": el[1]}

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"transcript": "", "confidence": 0.0, "error": "No STT provider"}

        client = Groq(api_key=api_key)
        with open(tmp_path, "rb") as f:
            data = f.read()

        transcription = client.audio.transcriptions.create(
            file=(audio.filename or "audio.webm", data),
            model="whisper-large-v3",
            language="en",
        )
        return {"transcript": transcription.text, "confidence": 0.95}
    except Exception as e:
        return {"transcript": "", "confidence": 0.0, "error": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
