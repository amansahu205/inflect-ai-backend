from fastapi import APIRouter, UploadFile, File
from groq import Groq
import os, tempfile

router = APIRouter()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        suffix = ".webm"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcription = (
                client.audio.transcriptions.create(
                    file=(audio.filename or 
                          "audio.webm", f.read()),
                    model="whisper-large-v3",
                    language="en",
                )
            )

        os.unlink(tmp_path)

        return {
            "transcript": transcription.text,
            "confidence": 0.95
        }
    except Exception as e:
        return {
            "transcript": "",
            "confidence": 0.0,
            "error": str(e)
        }