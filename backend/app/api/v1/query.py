from fastapi import APIRouter
from pydantic import BaseModel
from groq import Groq
import os, json

router = APIRouter()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class QueryRequest(BaseModel):
    text: str
    session_context: dict = {}

INTENT_PROMPT = """You are a financial intent classifier.
Extract structured data from the query.
Return ONLY valid JSON, nothing else:
{
  "intent_type": "research|price_check|trade|thesis",
  "ticker": "AAPL or null",
  "metric": "gross_margin|revenue|eps|pe_ratio or null",
  "timeframe": "Q4 2023|last year or null",
  "confidence": 0.95,
  "side": "buy|sell or null",
  "quantity": 0
}"""

ANSWER_PROMPT = """You are Inflect, an AI financial 
research assistant powered by SEC filings and 
market data.

Rules:
- Be concise and precise — max 150 words
- Cite your source at end: 
  SOURCE: [SEC Filing/Market Data/Wolfram Alpha]
- Never say BUY or SELL
- Use real knowledge about public companies
- If asked about specific numbers mention the 
  filing they come from
- Always end with confidence level:
  CONFIDENCE: HIGH/MEDIUM/LOW"""

@router.post("/analyze")
async def analyze_query(request: QueryRequest):
    # Step 1: Intent classification
    try:
        intent_resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", 
                 "content": INTENT_PROMPT},
                {"role": "user", 
                 "content": request.text}
            ],
            temperature=0.0,
            max_tokens=200
        )
        intent = json.loads(
            intent_resp.choices[0].message.content
        )
    except Exception:
        intent = {
            "intent_type": "research",
            "ticker": None,
            "confidence": 0.5
        }

    # Get ticker from intent or session
    ticker = (
        intent.get("ticker") or
        request.session_context.get("ticker", "")
    )

    # Step 2: Generate answer
    try:
        answer_resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",
                 "content": ANSWER_PROMPT},
                {"role": "user",
                 "content": (
                     f"Question: {request.text}\n"
                     f"Ticker: {ticker}\n"
                     f"Metric: {intent.get('metric')}\n"
                     f"Timeframe: {intent.get('timeframe')}"
                 )}
            ],
            temperature=0.1,
            max_tokens=400
        )
        answer = answer_resp.choices[0].message.content
    except Exception as e:
        answer = f"Unable to generate answer: {str(e)}"

    # Parse source
    source = "LLM"
    if "SEC Filing" in answer:
        source = "SEC_FILING"
    elif "Wolfram" in answer:
        source = "WOLFRAM"
    elif "Market Data" in answer:
        source = "MARKET_DATA"

    # Parse confidence
    confidence_level = "MEDIUM"
    if "CONFIDENCE: HIGH" in answer:
        confidence_level = "HIGH"
    elif "CONFIDENCE: LOW" in answer:
        confidence_level = "LOW"

    return {
        "intent_type": intent.get("intent_type"),
        "ticker": ticker or None,
        "metric": intent.get("metric"),
        "timeframe": intent.get("timeframe"),
        "confidence": intent.get("confidence", 0.8),
        "answer": answer,
        "source": source,
        "citation": None,
        "confidence_level": confidence_level
    }