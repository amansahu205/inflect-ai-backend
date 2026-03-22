# Inflect - AI

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Pipeline](https://img.shields.io/badge/Pipeline-Multi--agent-green)]()
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run-4285F4?logo=googlecloud&logoColor=white)](https://cloud.google.com/run)
[![Docker](https://img.shields.io/badge/Docker-container-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Snowflake](https://img.shields.io/badge/Snowflake-warehouse-29B5E8?logo=snowflake&logoColor=white)](https://www.snowflake.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%2B%20DB-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)

[![Groq](https://img.shields.io/badge/Groq-LLM-F55000)](https://groq.com/)
[![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Finnhub](https://img.shields.io/badge/Finnhub-Market%20data-22C55E)](https://finnhub.io/)
[![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Voice-000000)](https://elevenlabs.io/)
[![Wolfram](https://img.shields.io/badge/Wolfram%7CAlpha-enrichment-DD1100)](https://www.wolframalpha.com/)

[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![TanStack Query](https://img.shields.io/badge/TanStack-Query-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query)
[![Plotly](https://img.shields.io/badge/Plotly.js-Charts-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/javascript/)
[![Playwright](https://img.shields.io/badge/Playwright-E2E-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Vitest](https://img.shields.io/badge/Vitest-unit-6E9F18?logo=vitest&logoColor=white)](https://vitest.dev/)

**Inflect** — Market intelligence that thinks faster than the market moves. Research any Fortune 500 company in seconds — speak it, type it, trade it.

> **Disclaimer:** Educational demo only. Not investment advice. We never output BUY/SELL or price targets.

---

## Inspiration

Bloomberg Terminal costs $24,000 a year. TradingView assumes you already know what RSI means. ThinkorSwim was built for professionals, not students learning to trade.

We built Inflect because financial research shouldn't require a finance degree or a six-figure budget. Every retail investor and finance student deserves the same depth of insight that institutional traders take for granted — delivered instantly, cited accurately, and explained clearly.

The name comes from the concept of an *inflection point* — the moment a trend changes direction. That's exactly what we're trying to help users find, before everyone else does.


---

## What it does

Inflect is an AI-powered financial research platform that synthesizes SEC filings, real-time market data, technical indicators, and news sentiment into instant, cited answers.

Ask anything about a Fortune 500 company — fundamentals, technicals, earnings, price action — and Inflect returns a grounded answer with source citations pulled directly from SEC EDGAR filings, along with auto-generated interactive charts and a structured *Trade Thesis Card* showing:

- 📊 *Fundamental signal* — from 10-K/10-Q/8-K RAG retrieval
- 📈 *Technical signal* — RSI, MACD, Bollinger Bands via TA-Lib
- 📰 *Sentiment signal* — FinBERT scoring across recent headlines
- ⚖️ *Verdict* — HOLD / WATCH / AVOID (never BUY/SELL — we're educators, not advisors)

Users can also execute *paper trades* with $100K in simulated capital, upload chart screenshots for AI-powered vision analysis, and switch seamlessly between a voice interface and a Perplexity-style chat interface depending on their workflow.

Every single answer is citation-grounded. A Validator Agent blocks any response that cannot be traced back to a retrieved source document — *zero hallucination tolerance*.

- **Ask anything** — fundamentals, price checks, filings-aware Q&A via a multi-step backend pipeline (intent → retrieval → answer → validation).
- **Citations** — SEC filing excerpts from **Snowflake** when retrieval matches; answers are run through a **Validator** pass to flag weak grounding and missing disclaimers.
- **Live context** — ticker strip and quotes via **Finnhub**, with **Snowflake** backfill when server-side Yahoo access is slow or blocked.
- **Trade thesis card** — structured view (fundamental / technical / sentiment-style framing) with a verdict bucketed as **HOLD / WATCH / AVOID** (never BUY/SELL).
- **Charts** — **Plotly.js** line and gauge views on the frontend, fed by API chart/history data.
- **Voice + chat** — type in a research thread or use voice (ElevenLabs STT with optional **Groq Whisper** fallback).
- **Paper trading** — simulated orders tied to **Supabase** (profiles, positions, trades).

---

## How we built it

| Layer | Choices |
|--------|---------|
| **Frontend** | React 18, TypeScript, **Vite**, Tailwind, shadcn-style UI, Zustand, TanStack Query, React Router; **Plotly.js** for research visualizations. |
| **Backend** | **FastAPI** + Uvicorn, modular agents (retrieval, citation, answer, validator, thesis, chart, trade). |
| **Deploy** | Backend container on **Google Cloud Run** (`backend/Dockerfile`); frontend on static hosts / **Lovable** / custom domain with strict **CORS** (exact origins + regex for previews). |
| **Data** | **Snowflake** — `PRICES`, fundamentals, metrics, SEC text chunks for keyword / ILIKE RAG (vector search path documented for future BGE-scale embeddings). |
| **LLM** | **Groq** (e.g. LLaMA 3.1 8B intent, LLaMA 3.3 70B answers); **Gemini** / **Wolfram** hooks in the pipeline. |
| **Voice** | **ElevenLabs** Scribe; **Groq** Whisper when `STT_GROQ_FALLBACK` is enabled. |
| **Auth & app DB** | **Supabase** Auth + Postgres for user state, query log, and paper portfolio. |

---

## Challenges we ran into

- **Server-side market data** — `yfinance` from Cloud Run IPs was slow and often rate-limited; we moved hot paths to **Finnhub** and **batched Snowflake** closes for the ticker bar.
- **CORS & previews** — Lovable and other preview hosts need **regex `Access-Control-Allow-Origin`** patterns, not only a fixed allowlist.
- **Intent without tickers** — queries like “Tesla price?” needed **company → symbol** resolution and heuristics so **price_check** didn’t fall through to generic research.
- **Compliance tone** — thesis and answers must stay educational (no **BUY/SELL**), enforced in prompts, parsing, and UI copy.

---

## Accomplishments we’re proud of

- A working **analyze** pipeline with retrieval, optional Wolfram enrichment, and **post-answer validation** metadata exposed to the client.
- **Finnhub-first** quotes + **Snowflake** merge so the UI stays responsive on Cloud Run.
- **Dual UX** — research chat with example prompts, metric cards, thesis actions, and voice.
- **Paper trading** wired to Supabase with a Quick Trade flow on the home dashboard.
- **Playwright** smoke tests for `/app/home`, `/app/portfolio`, and `/app/research` (with a dev-only E2E auth flag).

---

## What we learned

- **Latency** is a product feature: parallel Finnhub fetches and avoiding unnecessary Yahoo round-trips matter as much as model choice.
- **RAG “faithfulness”** is harder than “retrieval hit rate” — validators and citation formatting catch drift early.
- **CORS and auth** should be planned with your real hosting URLs (prod domain + every preview origin) before demo day.

---

## What’s next

- Denser **vector** search over SEC chunks (embeddings pipeline exists in scripts; production cosine path is the next step).
- Richer **chart agent** (more chart types / server-side generation) and optional **vision** on uploaded screenshots.
- **Earnings / transcript** namespace and **backtesting** prompts (“If I bought … in …”).
- Mobile shell with offline-friendly cached answers.

---

## Stack (quick reference)

- **Frontend:** React, TypeScript, Vite, Tailwind, Zustand, TanStack Query, React Router, Plotly.js  
- **Backend:** Python, FastAPI, Uvicorn  
- **Auth:** Supabase  
- **Warehouse:** Snowflake  
- **LLM:** Groq; optional Gemini / Wolfram  
- **Voice:** ElevenLabs; Groq STT fallback  
- **Quotes:** Finnhub; Snowflake batch fallback; yfinance optional  
- **Deploy:** Cloud Run (`backend/Dockerfile`)

## Layout

- `backend/` — FastAPI (`app.main:app`)
- `frontend/` — Vite SPA

## Backend

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`GET /health` on port 8000.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Default dev server: **port 8080** (see `vite.config.ts`). Set `VITE_API_URL` to your API (e.g. `http://127.0.0.1:8000`).

## CORS

Backend reads repo-root `.env` and `backend/.env`. Allow your UI origin, e.g. `http://localhost:8080` and `http://127.0.0.1:8080`. For Lovable previews use `CORS_ORIGIN_REGEX` — see `backend/.env.example`.

## Cloud Run

From `backend/`:

```bash
gcloud run deploy inflect-backend --region=us-central1 --source=.
```

See `backend/cloudrun-update-cors-flags.yaml` for example env flags.

## Frontend scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Vite dev |
| `npm run build` | Production build |
| `npm run test` | Vitest |
| `npm run dev:e2e` | E2E mode (`VITE_E2E_AUTH`) |
| `npm run test:e2e` | Playwright |

## API (selected)

- `POST /api/v1/query/analyze`
- `GET /api/v1/market/tickers`
- `GET /api/v1/market/tickers/quote`
- `GET /api/v1/market/tickers/history`
- `GET /api/v1/market/tickers/metric`
- `POST /api/v1/voice/transcribe`
- `POST /api/v1/thesis/generate`

## Security

Do not commit `.env` or keys. Do not set `VITE_E2E_AUTH` in production builds.
