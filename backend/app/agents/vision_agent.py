"""Gemini vision analysis for chart screenshots."""

from __future__ import annotations

import base64
import os

import httpx

from app.agents.base_agent import BaseAgent


class VisionAgent(BaseAgent):
    name = "vision"

    async def run(self, input: dict) -> dict:
        raw: bytes = input["raw"]
        mime = input.get("mime") or "image/png"
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return {"error": "GEMINI_API_KEY not configured", "summary": ""}

        b64 = base64.standard_b64encode(raw).decode("ascii")

        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "You are a financial chart assistant. Describe trend, "
                                "support/resistance if visible, and key risks. "
                                "Do not give buy/sell instructions or price targets. "
                                "Keep under 120 words. End with: Educational only. Not investment advice."
                            )
                        },
                        {"inline_data": {"mime_type": mime, "data": b64}},
                    ]
                }
            ]
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash:generateContent"
        )
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(f"{url}?key={key}", json=body)
                data = r.json()
                if r.status_code != 200:
                    return {
                        "error": data.get("error", {}).get("message", r.text),
                        "summary": "",
                    }
                parts = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                text = "".join(p.get("text", "") for p in parts)
                return {"summary": text.strip(), "model": "gemini-1.5-flash"}
        except Exception as e:
            return {"error": str(e), "summary": ""}
