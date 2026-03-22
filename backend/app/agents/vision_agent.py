"""Gemini vision analysis for chart screenshots."""

from __future__ import annotations

import asyncio
import base64
import logging
import os

import httpx

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent"
)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_VISION_PROMPT = (
    "You are a financial chart assistant. Describe the trend, "
    "support/resistance levels if visible, and key risks. "
    "Do not give buy/sell instructions or price targets. "
    "Keep under 120 words. End with: Educational only. Not investment advice."
)


class VisionAgent(BaseAgent):
    name = "vision"

    async def run(self, input: dict) -> dict:
        raw: bytes = input["raw"]
        mime: str = input.get("mime") or "image/png"

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return {"error": "GEMINI_API_KEY not configured", "summary": ""}

        b64 = base64.standard_b64encode(raw).decode("ascii")
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": _VISION_PROMPT},
                        {"inline_data": {"mime_type": mime, "data": b64}},
                    ]
                }
            ]
        }

        last_error = "Unknown error"

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(f"{_GEMINI_URL}?key={key}", json=body)

                if r.status_code == 200:
                    data = r.json()
                    parts = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [])
                    )
                    text = "".join(p.get("text", "") for p in parts).strip()
                    return {"summary": text, "model": "gemini-1.5-flash"}

                if r.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                    last_error = f"HTTP {r.status_code}"
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "VisionAgent: %s, retry in %.1fs", r.status_code, delay
                    )
                    await asyncio.sleep(delay)
                    continue

                err_msg = r.json().get("error", {}).get("message", r.text)
                logger.error("VisionAgent: Gemini %s: %s", r.status_code, err_msg)
                return {"error": err_msg, "summary": ""}

            except httpx.TimeoutException:
                last_error = f"Timeout attempt {attempt}"
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                else:
                    logger.error("VisionAgent: timed out")

            except Exception as e:
                logger.error("VisionAgent: %s", e)
                return {"error": str(e), "summary": ""}

        return {
            "error": f"Gemini failed after {_MAX_RETRIES} attempts: {last_error}",
            "summary": "",
        }
