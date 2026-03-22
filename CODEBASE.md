# INFLECT — Codebase Documentation

## Last Updated: March 23, 2026

## Team: Aman Kumar Sahu + 3 teammates

---

## Project Overview

**Inflect** is an AI-powered financial research web app aimed at retail investors: voice or chat to query S&P 500–style equities, combine SEC filing context (via Snowflake RAG), live-style quotes (yfinance), and LLM-generated answers (Groq). The **frontend** is React + TypeScript + Vite + Tailwind + shadcn/ui, with Supabase for auth and paper-trading persistence. The **backend** is FastAPI, intended for deployment on **GCP Cloud Run**. Domain logic is organized into an **agent layer** (`app/agents/`), an **orchestrator** (`app/orchestrator/pipeline.py`) for the main `/query/analyze` flow, **thin HTTP routers** (`app/api/v1/`), and **services** for data/API access (`app/services/`). Optional integrations: ElevenLabs (STT/TTS), Gemini (vision), Wolfram Alpha (computation), and Snowflake (SEC chunk store).

**Important naming:** There is no `Research.tsx` / `Portfolio.tsx` at the repo root of `src/pages/`. The main app screens are **`AppResearch.tsx`** (JARVIS research HUD) and **`AppPortfolio.tsx`**. The marketing site is **`Index.tsx`** at `/`.

---

## Backend cleanup (guardrails)

Reference checklist for refactors. **Current state:** `app/api/v1/query.py` is a **thin router only** (~15 lines) calling `run_query_pipeline`; there is **no** `app/api/v1/llm.py` (removed — do not reintroduce). Package inits exist: `app/agents/__init__.py`, `app/agents/sec_research/__init__.py`, `app/orchestrator/__init__.py`, `app/schemas/__init__.py`).

**Do not move LLM/RAG logic into:** `api/v1/market.py`, `api/v1/voice.py`, `api/v1/tts.py`, `services/snowflake_rag_service.py`, `main.py` unless fixing a bug or an agreed product change.

```
CLEANUP INSTRUCTIONS:
1. Replace app/api/v1/query.py entirely
   Old version has monolithic logic
   New version: thin wrapper only

2. Create these __init__.py files:
   app/agents/__init__.py
   app/agents/sec_research/__init__.py
   app/orchestrator/__init__.py
   app/schemas/__init__.py

3. Delete these if they exist:
   app/api/v1/llm.py (replaced by agents)

4. Keep these UNCHANGED:
   app/api/v1/market.py
   app/api/v1/voice.py
   app/api/v1/tts.py
   app/services/snowflake_rag_service.py
   app/main.py
```

---

## Directory Structure

> `data/` is described below as the **intended** dataset layout (scripts write under repo root); the folder may be empty or gitignored in a fresh clone.

```
inflect/
├── CODEBASE.md                 # This file
├── requirements.txt            # ⚠️ Corrupted / pasted markdown — use backend/requirements.txt
├── backend/
│   ├── requirements.txt        # ✅ Python API dependencies
│   └── app/
│       ├── main.py
│       ├── agents/             # Domain agents (SEC, thesis, chart, trade, vision)
│       │   ├── base_agent.py
│       │   ├── sec_research/   # retrieval, citation, validator, answer
│       │   ├── thesis_agent.py
│       │   ├── chart_agent.py
│       │   ├── trade_agent.py
│       │   └── vision_agent.py
│       ├── orchestrator/       # pipeline.py coordinates query flow
│       ├── schemas/            # pydantic: QueryRequest, TradeRequest
│       ├── api/v1/             # Thin FastAPI routers → agents/orchestrator
│       └── services/           # Data access: Snowflake, market, Wolfram, news (local files)
│   └── scripts/
│       ├── download/
│       └── setup/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── components.json         # shadcn config
│   ├── public/                 # Static assets + videos
│   ├── supabase/               # config.toml + SQL migrations
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── index.css
│       ├── api/
│       ├── components/         # app, jarvis, landing, voice, chat, …
│       ├── contexts/
│       ├── hooks/
│       ├── integrations/supabase/
│       ├── lib/
│       ├── pages/
│       ├── store/
│       ├── types/
│       ├── utils/
│       └── test/
└── data/                       # (Optional) SEC, prices, fundamentals, … — see Data section
```

---

## Backend (`inflect/backend/`)

### Entry Point

#### `backend/app/main.py`
**Purpose:** FastAPI application factory, CORS, env loading, health check, mounts v1 API router.  
**Key functions/components:** `app` (FastAPI), `health()`  
**Inputs:** Env: `CORS_ORIGINS` (comma-separated origins; default `*`). Loads `inflect/.env` then `inflect/backend/.env` (non-overriding).  
**Outputs:** `GET /health` → `{"status","version"}`; includes `/api/v1/*` routes.  
**Dependencies:** `fastapi`, `dotenv`, `app.api.v1.router`  
**Status:** ✅ Complete

---

### API Routes (`app/api/v1/`)

#### `backend/app/api/v1/router.py`
**Purpose:** Aggregates all v1 sub-routers under `/api/v1`.  
**Key functions/components:** `router` (`APIRouter`), multiple `include_router(...)` calls.  
**Inputs:** None (import-time wiring).  
**Outputs:** Combined routes for voice, query, market, trades, thesis, tts, vision, rag, chart.  
**Dependencies:** `fastapi.APIRouter`, sibling route modules  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/query.py` ⭐ MOST IMPORTANT (thin HTTP)
**Purpose:** Exposes `POST /analyze` only; delegates to **`app.orchestrator.pipeline.run_query_pipeline`**. No LLM/RAG logic in this file.  
**Key functions/components:** `analyze_query`; imports `QueryRequest` from `app.schemas.query` (~15 lines total).  
**Inputs:** `POST /api/v1/query/analyze` JSON `{ text, session_context }`.  
**Outputs:** Same JSON as before (`AnalyzeResult` shape).  
**Dependencies:** `app.orchestrator.pipeline`, `app.schemas.query`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/market.py`
**Purpose:** Stock quotes for single ticker, ticker bar (30 symbols), and batch wrapper.  
**Key functions/components:** `TICKER_LIST`, `get_stock_quote`, `quote_to_ticker_bar_row`, `get_quote`, `get_ticker_bar`, `get_batch_quotes`  
**Inputs:** `GET /quote?ticker=`, `GET /tickers`, `GET /batch`  
**Outputs:** Quote dict with `price`, `change_percent`, `volume`, `direction`, `timestamp`; tickers array shaped for frontend `useTicker`.  
**Dependencies:** `yfinance`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/voice.py`
**Purpose:** Speech-to-text for uploaded audio (voice mode).  
**Key functions/components:** `_transcribe_elevenlabs`, `transcribe`  
**Inputs:** `POST /api/v1/voice/transcribe` multipart `audio` file. Env: `ELEVENLABS_API_KEY`, `GROQ_API_KEY`.  
**Outputs:** `{ transcript, confidence?, error? }`  
**Dependencies:** `httpx` (ElevenLabs REST), `groq` Whisper fallback  
**Status:** 🔧 Needs work — ElevenLabs endpoint/model may need alignment with current docs

---

#### `backend/app/api/v1/thesis.py` (thin HTTP)
**Purpose:** `POST /generate` → **`ThesisAgent().run(payload)`** (`payload` is the request body dict).  
**Key functions/components:** `generate_thesis_route`  
**Inputs:** JSON `{ ticker }`. Env: `GROQ_API_KEY`.  
**Outputs:** Thesis JSON + `educational_note` + optional `error`.  
**Dependencies:** `app.agents.thesis_agent`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/trades.py` (thin HTTP)
**Purpose:** `POST /execute` → **`TradeAgent().run(order.model_dump())`**; `TradeRequest` from `app.schemas.trade`.  
**Key functions/components:** `execute_trade`  
**Inputs:** `POST /api/v1/trades/execute` JSON `{ ticker, side, quantity, order_type?, user_id? }`  
**Outputs:** Fill payload: `fill_price`, `total_value`, `status`, `order_id`, etc.  
**Dependencies:** `app.agents.trade_agent`, `app.schemas.trade`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/tts.py`
**Purpose:** Text-to-speech via ElevenLabs (MP3 stream).  
**Key functions/components:** `TtsRequest`, `synthesize`  
**Inputs:** `POST /api/v1/tts/synthesize` JSON `{ text }`. Env: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`.  
**Outputs:** `audio/mpeg` stream or error text.  
**Dependencies:** `httpx`  
**Status:** ✅ Complete (frontend currently uses browser `speechSynthesis` for voice playback — this route is optional for product)

---

#### `backend/app/api/v1/vision.py` (thin HTTP)
**Purpose:** Reads upload bytes → **`VisionAgent().run({"raw": bytes, "mime": str})`** (Gemini).  
**Key functions/components:** `analyze_chart`  
**Inputs:** `POST /api/v1/vision/analyze` multipart `image`. Env: `GEMINI_API_KEY`.  
**Outputs:** `{ summary, model? }` or `{ error, summary }`  
**Dependencies:** `app.agents.vision_agent`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/rag.py`
**Purpose:** Debug/admin endpoint for Snowflake chunk retrieval via **`RetrievalAgent`**.  
**Key functions/components:** `RagSearchRequest`, `rag_search`  
**Inputs:** `POST /api/v1/rag/search` JSON `{ ticker?, query, limit? }`  
**Outputs:** `{ count, chunks }`  
**Dependencies:** `app.agents.sec_research.retrieval_agent`  
**Status:** ✅ Complete

---

#### `backend/app/api/v1/chart.py` (thin HTTP)
**Purpose:** `GET /data` → **`ChartAgent().run({"ticker", "metric", "timeframe"})`** (yfinance series; Plotly server-side not yet).  
**Key functions/components:** `chart_data`  
**Inputs:** `GET /api/v1/chart/data?ticker=&metric=&timeframe=`  
**Outputs:** `{ x: string[], y: number[], filingDates?: string[] }`  
**Dependencies:** `app.agents.chart_agent`  
**Status:** ✅ Complete

---

### Orchestrator (`app/orchestrator/`)

#### `backend/app/orchestrator/pipeline.py` ⭐ coordinates `/query/analyze`
**Purpose:** Single entry **`run_query_pipeline(request: QueryRequest)`**: intent classification (**`llama-3.1-8b-instant`**, sync in thread), routing for `price_check` / `trade` / `thesis` / `research`, SEC **RetrievalAgent** → **CitationAgent** → **ValidatorAgent** → **AnswerAgent** (each `run(input: dict) -> dict`), optional **Wolfram** via `wolfram_service`, quote snapshots via **`get_quote_snapshot`** + `_format_price_answer` in pipeline, optional **local file hints** via `news_service.build_local_context_block`.  
**Key functions/components:** `run_query_pipeline`, `_classify_intent_sync`, `_extract_json`, `_default_intent`, `_format_price_answer`, `_looks_computational`, `_trade_ack`, `_thesis_pointer`, `INTENT_PROMPT`  
**Inputs:** `QueryRequest` (`text`, `session_context`). Env: `GROQ_API_KEY`, `WOLFRAM_APP_ID`, Snowflake vars.  
**Outputs:** Dict matching frontend `AnalyzeResult`.  
**Dependencies:** `app.agents.sec_research.*`, `app.services.market_service`, `app.services.wolfram_service`, `app.services.news_service`, `app.schemas.query`, `groq`  
**Status:** ✅ Complete

#### `backend/app/orchestrator/__init__.py`
**Purpose:** Re-exports `run_query_pipeline`.  
**Status:** ✅ Complete

---

### Agents (`app/agents/`)

#### `backend/app/agents/base_agent.py`
**Purpose:** Abstract **`BaseAgent`**: **`async def run(self, input: dict) -> dict`**.  
**Status:** ✅ Complete

---

#### `backend/app/agents/sec_research/retrieval_agent.py`
**Purpose:** **`RetrievalAgent`** — input e.g. `{"ticker", "query", "limit"}`; output `{"chunks": [...]}`; wraps `search_sec_chunks` via `asyncio.to_thread`.  
**Status:** ✅ Complete

---

#### `backend/app/agents/sec_research/citation_agent.py`
**Purpose:** **`CitationAgent.run({"chunks"})` → `{"rag_block", "citation"}`; **`format_rag_context_static`** helper.  
**Status:** ✅ Complete

---

#### `backend/app/agents/sec_research/validator_agent.py`
**Purpose:** **`ValidatorAgent.run({"chunks", "answer"?})` → `{"ok", "warnings"}`**; module **`parse_answer_meta`** for `SOURCE` / `CITATION` / `CONFIDENCE` lines in model text.  
**Status:** ✅ Complete

---

#### `backend/app/agents/sec_research/answer_agent.py`
**Purpose:** **`AnswerAgent.run({"user_content", ...})` → `{"answer"}`** — Groq using **`ANSWER_PROMPT`** (70B + 8B fallback).  
**Status:** ✅ Complete

---

#### `backend/app/agents/thesis_agent.py`
**Purpose:** **`ThesisAgent.run({"ticker": ...})`**, **`compute_verdict`**, **`calculate_rsi`**, **`THESIS_PROMPT`**, **`EDU`** disclaimer; thesis generation runs in **`asyncio.to_thread`** (sync Groq + yfinance).  
**Status:** ✅ Complete

---

#### `backend/app/agents/chart_agent.py`
**Purpose:** **`ChartAgent.run({"ticker", "metric", "timeframe"})`** — yfinance OHLC closes for charts. Server-side Plotly can be added later.  
**Status:** ✅ Complete

---

#### `backend/app/agents/trade_agent.py`
**Purpose:** **`TradeAgent.run({ticker, side, quantity, ...})`** — slippage + fill price from yfinance.  
**Status:** ✅ Complete

---

#### `backend/app/agents/vision_agent.py`
**Purpose:** **`VisionAgent.run({"raw", "mime"})`** — Gemini REST (chart image analysis).  
**Status:** ✅ Complete

---

#### `backend/app/agents/__init__.py`
**Purpose:** Package init; exports **`BaseAgent`**.  
**Status:** ✅ Complete

---

#### `backend/app/agents/sec_research/__init__.py`
**Purpose:** Re-exports SEC sub-agents.  
**Status:** ✅ Complete

---

### Schemas (`app/schemas/`)

#### `backend/app/schemas/query.py`
**Purpose:** Pydantic **`QueryRequest`** (`text`, `session_context`) — shared by orchestrator and `api/v1/query`.  
**Status:** ✅ Complete

---

#### `backend/app/schemas/trade.py`
**Purpose:** Pydantic **`TradeRequest`** — shared by `api/v1/trades` and `trade_agent`.  
**Status:** ✅ Complete

---

#### `backend/app/schemas/__init__.py`
**Purpose:** Re-exports **`QueryRequest`**, **`TradeRequest`**.  
**Status:** ✅ Complete

---

### Services (`app/services/`)

#### `backend/app/services/__init__.py`
**Purpose:** Package marker for service layer.  
**Key functions/components:** —  
**Inputs:** —  
**Outputs:** —  
**Dependencies:** —  
**Status:** ✅ Complete

---

#### `backend/app/services/snowflake_rag_service.py`
**Purpose:** Connect to Snowflake and retrieve SEC filing chunks by **ticker + keyword / ILIKE** (no BGE-M3 query embedding on server).  
**Key functions/components:** `_connect`, `snowflake_configured`, `_query_keywords`, `search_sec_chunks`  
**Inputs:** `ticker` (optional), `user_query`, `limit`. Env: `SNOWFLAKE_*` account credentials.  
**Outputs:** `list[dict]` rows (chunk metadata + text).  
**Dependencies:** `snowflake.connector` (lazy import)  
**Status:** ✅ Complete (🔧 upgrade path: true `VECTOR_COSINE_SIMILARITY` with 1024-dim query embedding)

---

#### `backend/app/services/market_service.py`
**Purpose:** Data only: **`get_quote_snapshot(ticker)`** returns numeric fields (`price`, `change_percent`, `volume`, etc.); **`yfinance_last_price`**. Orchestrator formats user-facing price-check text.  
**Used by:** `app.orchestrator.pipeline`  
**Status:** ✅ Complete

---

#### `backend/app/services/wolfram_service.py`
**Purpose:** Async **`fetch_wolfram_result`** (Wolfram Alpha `/v1/result`).  
**Used by:** `app.orchestrator.pipeline` when RAG is thin and query looks computational.  
**Env:** `WOLFRAM_APP_ID`  
**Status:** ✅ Complete

---

#### `backend/app/services/news_service.py`
**Purpose:** Read-only loaders for cached datasets under **`data/`** (repo root): `fundamentals/{TICKER}.json`, `news/{TICKER}.json`, `metrics/{TICKER}.json`, tail rows from `prices/{TICKER}.csv`; **`build_local_context_block(ticker)`** returns a short text block for the research prompt.  
**Used by:** `app.orchestrator.pipeline`  
**Status:** ✅ Complete

---

### Prompts (`app/prompts/`)

**Status:** ❌ Dedicated `app/prompts/` package not present. Prompt strings live in code:

| Prompt | Location |
|--------|----------|
| `INTENT_PROMPT` | `app/orchestrator/pipeline.py` |
| `ANSWER_PROMPT` | `app/agents/sec_research/answer_agent.py` |
| `THESIS_PROMPT` | `app/agents/thesis_agent.py` |

---

### Scripts (`backend/scripts/`)

#### `backend/scripts/download/sec_edgar_scraper.py`
**Purpose:** Download 10-K / 10-Q / 8-K HTML from SEC EDGAR with rate limiting.  
**Key functions/components:** `SECEdgarScraper` class, CLI  
**Inputs:** CLI args, paths under `data/sec_filings/raw/`.  
**Outputs:** Raw HTML files, logs.  
**Dependencies:** `requests`, `pandas`, `argparse`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/download_fundamentals.py`
**Purpose:** Batch download yfinance fundamentals JSON per ticker list.  
**Key functions/components:** main script logic (writes `data/fundamentals/`).  
**Inputs:** `dotenv`, ticker list / CSV.  
**Outputs:** JSON files under `data/fundamentals/`.  
**Dependencies:** `yfinance`, `pandas`, `tqdm`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/download_news.py`
**Purpose:** Finnhub company news → JSON per ticker.  
**Key functions/components:** Finnhub client loop.  
**Inputs:** `FINNHUB` API keys in `.env`, ticker universe.  
**Outputs:** `data/news/*.json`  
**Dependencies:** `finnhub-python`, `pandas`, `tqdm`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/download_recommendations.py`
**Purpose:** Finnhub analyst recommendations → JSON per ticker.  
**Key functions/components:** Finnhub client loop.  
**Inputs:** `FINNHUB` keys, tickers.  
**Outputs:** `data/recommendations/*.json`  
**Dependencies:** `finnhub-python`, `pandas`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/get_sp500_list.py`
**Purpose:** Scrape Wikipedia S&P 500 table → CSV with tickers, sectors, CIK.  
**Key functions/components:** `scrape_sp500_table`  
**Inputs:** Wikipedia HTML.  
**Outputs:** `sp500_companies.csv` (in download folder).  
**Dependencies:** `requests`, `bs4`, `pandas`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/fortune500_tickers.py`
**Purpose:** Tiny helper — reads `sp500_companies.csv`, prints count, writes `tickers.txt`.  
**Key functions/components:** script body  
**Inputs:** CSV path.  
**Outputs:** `tickers.txt`  
**Dependencies:** `pandas`  
**Status:** ✅ Complete

---

#### `backend/scripts/download/tickers.txt` / `sp500_companies.csv` / `failed_metrics.txt`
**Purpose:** Data artifacts / lists used by download pipelines.  
**Status:** ✅ Data / 🔧 `failed_metrics.txt` — log-style list of failed tickers

---

#### `backend/scripts/setup/sec_html_parser.py`
**Purpose:** Parse SEC HTML to structured JSON (sections, tables → markdown).  
**Key functions/components:** parser functions + multiprocessing pool  
**Inputs:** Raw HTML under `data/sec_filings/raw/`.  
**Outputs:** JSON under `data/sec_filings/processed/text/`.  
**Dependencies:** `beautifulsoup4`, `tqdm`  
**Status:** ✅ Complete

---

#### `backend/scripts/setup/chunk_documents.py`
**Purpose:** Token-aware chunking with **same tokenizer as BGE-M3** (`BAAI/bge-m3`).  
**Key functions/components:** chunking pipeline, CLI  
**Inputs:** Parsed JSON files.  
**Outputs:** Chunk JSON files under `data/sec_filings/processed/chunks/`.  
**Dependencies:** `transformers`, `tqdm`, `scipy`  
**Status:** ✅ Complete

---

#### `backend/scripts/setup/convert_to_jsonl.py`
**Purpose:** Merge all chunk JSON files into one `all_chunks.jsonl` for embedding/streaming.  
**Key functions/components:** `convert_to_jsonl`  
**Inputs:** `chunks/` directory.  
**Outputs:** `all_chunks.jsonl`  
**Dependencies:** stdlib  
**Status:** ✅ Complete

---

#### `backend/scripts/setup/generate_embeddings.py`
**Purpose:** GPU local embedding with **SentenceTransformers `BAAI/bge-m3`**, writes `embeddings_1024.jsonl`.  
**Key functions/components:** `GPUEmbeddingPipeline`  
**Inputs:** `all_chunks.jsonl`, checkpoint file.  
**Outputs:** `embeddings_1024.jsonl`  
**Dependencies:** `sentence_transformers`, `torch`, `tqdm`  
**Status:** ✅ Complete (requires GPU + heavy deps — not in slim `backend/requirements.txt`)

---

#### `backend/scripts/setup/upload_to_snowflake.py`
**Purpose:** Row-oriented upload of `embeddings_1024.jsonl` to Snowflake `SEC_EMBEDDINGS` with resume checkpoint.  
**Key functions/components:** `main`, checkpoint helpers  
**Inputs:** `.env` Snowflake credentials, local JSONL.  
**Outputs:** Rows in Snowflake; checkpoint file.  
**Dependencies:** `snowflake-connector-python`, `tqdm`  
**Status:** ✅ Complete (paths hardcoded to `D:/...` — 🔧 parameterize for CI)

---

#### `backend/scripts/setup/upload_to_snowflake_bulk.py`
**Purpose:** Faster bulk load via stage + `COPY INTO` + vector cast.  
**Key functions/components:** bulk pipeline stages  
**Inputs:** `embeddings_1024.jsonl`, Snowflake creds.  
**Outputs:** Populated `SEC_EMBEDDINGS`.  
**Dependencies:** `snowflake-connector-python`, `csv`, `json`  
**Status:** ✅ Complete (🔧 same path hardcoding note)

---

#### `backend/scripts/setup/pinecone_indexer.py`
**Purpose:** Placeholder for Pinecone indexing.  
**Key functions/components:** `upload_to_pinecone` (stub)  
**Inputs:** —  
**Outputs:** —  
**Dependencies:** —  
**Status:** ❌ Stub

---

#### `backend/scripts/setup/pdf_parser.py`
**Purpose:** Placeholder for PDF text extraction.  
**Key functions/components:** `parse_pdf` (returns `""`)  
**Inputs:** file path  
**Outputs:** empty string  
**Dependencies:** —  
**Status:** ❌ Stub

---

#### `backend/requirements.txt`
**Purpose:** Python dependencies for **FastAPI Cloud Run** service.  
**Key functions/components:** —  
**Inputs:** —  
**Outputs:** —  
**Dependencies:** lists `fastapi`, `uvicorn`, `groq`, `yfinance`, `httpx`, `snowflake-connector-python`, etc.  
**Status:** ✅ Complete

---

## Frontend (`inflect/frontend/`)

### Pages (`src/pages/`)

Note: **`Research.tsx` / `Portfolio.tsx` / `Landing.tsx`** do not exist; use **`AppResearch`**, **`AppPortfolio`**, **`Index`**.

#### `frontend/src/pages/Index.tsx`
**Purpose:** Marketing landing page composition (navbar, hero, features, videos, CTA, footer).  
**Key functions/components:** default export `Index`  
**Inputs:** None  
**Outputs:** Renders full landing layout  
**Dependencies:** `@/components/landing/*`, `framer-motion`  
**Status:** ✅ Complete

---

#### `frontend/src/pages/Login.tsx`
**Purpose:** Auth sign-in UI (Matrix background, glow inputs, Supabase email/password).  
**Key functions/components:** page component  
**Inputs:** User credentials, redirect query  
**Outputs:** Session via Supabase; navigation to `/app/research` or redirect  
**Dependencies:** `@/integrations/supabase/client`, `@/components/auth/*`, `react-router-dom`  
**Status:** ✅ Complete

---

#### `frontend/src/pages/Register.tsx`
**Purpose:** Registration flow mirroring Login styling.  
**Key functions/components:** page component  
**Inputs:** Sign-up form  
**Outputs:** Supabase user + profile trigger  
**Dependencies:** Supabase client, auth UI components  
**Status:** ✅ Complete

---

#### `frontend/src/pages/AppResearch.tsx` ⭐ MOST IMPORTANT
**Purpose:** Core **JARVIS** experience: voice + chat, query pipeline (`analyzeQuery`), thesis generation, chart data, paper trade modal, Supabase query history, ticker session state.  
**Key functions/components:** `AppResearch`, `runPipeline`, `submitQuery`, `handleChatSubmit`, `handleGenerateThesis`, `handlePlotTrend`, `speakText`, `mockAnalyze` (offline), `detectTradeIntent`  
**Inputs:** `VITE_API_URL`, Supabase session, Zustand stores  
**Outputs:** Updates UI panels, inserts into `queries` table, optional `executeTradeApi`  
**Dependencies:** `@/api/query`, `@/api/market`, `@/api/chart`, `@/api/trades`, `@/components/jarvis/*`, `@/store/*`  
**Status:** ✅ Complete

---

#### `frontend/src/pages/AppPortfolio.tsx`
**Purpose:** Portfolio dashboard: positions, trade history, buying power from Supabase; mock P&L randomization for display.  
**Key functions/components:** `AppPortfolio`  
**Inputs:** `user.id` from auth store  
**Outputs:** Tables + summary cards  
**Dependencies:** `@/components/trading/*`, Supabase `.from("positions"|"trades"|"profiles")`  
**Status:** 🔧 Needs work — position value uses `Math.random()` (not live quotes)

---

#### `frontend/src/pages/Demo.tsx`
**Purpose:** Demo / showcase route (secondary entry).  
**Key functions/components:** `Demo`  
**Inputs:** —  
**Outputs:** —  
**Dependencies:** —  
**Status:** ✅ Complete

---

#### `frontend/src/pages/NotFound.tsx`
**Purpose:** 404 fallback for unknown routes.  
**Key functions/components:** `NotFound`  
**Inputs:** —  
**Outputs:** —  
**Dependencies:** `react-router-dom`  
**Status:** ✅ Complete

---

### Components (`src/components/`)

#### `frontend/src/components/` — Shared & layout

| File | Purpose | Status |
|------|---------|--------|
| `NavLink.tsx` | Wrapper for router links with active styling | ✅ |
| `ProtectedRoute.tsx` | Auth gate; redirects to `/login` with `redirect_to` | ✅ |
| `layout/AppLayout.tsx` | Shell for `/app/*` (navbar, ticker, bottom bar) | ✅ |
| `layout/PageTransition.tsx` | Framer-motion page enter/exit | ✅ |

---

#### `frontend/src/components/app/` — In-app shell widgets

| File | Purpose | Status |
|------|---------|--------|
| `AppNavbar.tsx` | Top nav inside app layout | ✅ |
| `AmbientCanvas.tsx` | Background canvas effect | ✅ |
| `BottomBar.tsx` | Portfolio summary strip (duplicate name vs `ui/BottomBar`) | ✅ |
| `ChatMode.tsx` | Chat layout wiring | ✅ |
| `VoiceMode.tsx` | Voice layout wiring | ✅ |
| `MicButton.tsx` | Mic control hook-up | ✅ |
| `ModeToggle.tsx` | Voice/chat toggle (app variant) | ✅ |
| `OutputPanel.tsx` | Legacy output panel | ✅ |
| `QueryHistory.tsx` | App-side query history (vs research duplicate) | ✅ |

---

#### `frontend/src/components/jarvis/` — Research HUD (primary UI)

| File | Purpose | Status |
|------|---------|--------|
| `JarvisCanvas.tsx` | Scene / canvas for orb + HUD | ✅ |
| `JarvisHudCenter.tsx` | Center HUD (orb, voice state) | ✅ |
| `JarvisChatPanel.tsx` | Chat thread + input area | ✅ |
| `JarvisInputBar.tsx` | Text input + submit | ✅ |
| `JarvisMetricsRow.tsx` | Latency / metrics chips | ✅ |
| `JarvisOutputPanel.tsx` | Answer / thesis / chart output | ✅ |
| `JarvisQueryLog.tsx` | Left rail query log | ✅ |

---

#### `frontend/src/components/landing/` — Marketing sections

| File | Purpose | Status |
|------|---------|--------|
| `Navbar.tsx` | Landing header | ✅ |
| `Hero.tsx` | Hero + video | ✅ |
| `LogoStrip.tsx` | Partner / logo strip | ✅ |
| `DashboardPreview.tsx` | Teaser dashboard | ✅ |
| `Features.tsx` | Feature grid | ✅ |
| `VoiceShowcase.tsx` | Voice feature demo | ✅ |
| `HowItWorks.tsx` | Steps | ✅ |
| `BullBear.tsx` | Bull/bear section + video | ✅ |
| `Stats.tsx` | Stats strip | ✅ |
| `DashboardFull.tsx` | Full-width dashboard promo | ✅ |
| `CTA.tsx` | Call to action | ✅ |
| `Footer.tsx` | Footer | ✅ |
| `ParticleCanvas.tsx` | Particle background | ✅ |
| `InflectLogo.tsx` | Logo asset wrapper | ✅ |

---

#### `frontend/src/components/voice/`

| File | Purpose | Status |
|------|---------|--------|
| `VoiceButton.tsx` | JARVIS orb + rings + voice states | ✅ |
| `HudVoiceButton.tsx` | HUD-specific voice trigger | ✅ |
| `WaveformVisualizer.tsx` | Audio level visualization | ✅ |

---

#### `frontend/src/components/chat/`

| File | Purpose | Status |
|------|---------|--------|
| `ChatThread.tsx` | Message list | ✅ |
| `ChatBubble.tsx` | Single bubble styling | ✅ |
| `ChatInput.tsx` | Chat input control | ✅ |

---

#### `frontend/src/components/research/`

| File | Purpose | Status |
|------|---------|--------|
| `AnswerCard.tsx` | Renders LLM answer | ✅ |
| `CitationCard.tsx` | Citation / SEC reference | ✅ |
| `ThesisCard.tsx` | HOLD/WATCH/AVOID thesis | ✅ |
| `QueryHistory.tsx` | Research-style history list | ✅ |

---

#### `frontend/src/components/charts/`

| File | Purpose | Status |
|------|---------|--------|
| `LineChart.tsx` | Recharts line chart wrapper | ✅ |
| `MetricCard.tsx` | Metric tile | ✅ |
| `RSIGauge.tsx` | RSI gauge | ✅ |
| `StockCard.tsx` | Quote + sparkline | ✅ |

---

#### `frontend/src/components/trading/`

| File | Purpose | Status |
|------|---------|--------|
| `TradeModal.tsx` | Confirm paper trade | ✅ |
| `PositionsTable.tsx` | Open positions | ✅ |
| `TradeHistory.tsx` | Past trades | ✅ |

---

#### `frontend/src/components/auth/`

| File | Purpose | Status |
|------|---------|--------|
| `MatrixCanvas.tsx` | Matrix rain background | ✅ |
| `GlowInput.tsx` / `GlowInput.css` | Styled inputs | ✅ |
| `ProtectedRoute.tsx` | Duplicate auth guard (prefer `components/ProtectedRoute.tsx`) | ⚠️ Duplicate |

---

#### `frontend/src/components/ui/` — shadcn/Radix + Inflect

Inflect-specific (not stock shadcn):

| File | Purpose | Status |
|------|---------|--------|
| `TickerBar.tsx` / `TickerBar.css` | Live ticker strip; uses `useTicker` | ✅ |
| `NavBar.tsx` | Navigation bar variant | ✅ |
| `BottomBar.tsx` | Bottom bar variant | ✅ |
| `ModeToggle.tsx` | Voice/chat pill | ✅ |
| `InflectSkeleton.tsx` | Branded skeleton | ✅ |
| `InflectToast.tsx` | Toast provider | ✅ |
| `Toast.tsx` / `toaster.tsx` / `sonner.tsx` | Toast stacks | ✅ |

All other `*.tsx` files in `ui/` are **shadcn/ui** primitives (Radix + `class-variance-authority` + `cn` helper). **Purpose:** accessible UI building blocks (buttons, dialogs, forms, tables, etc.). **Status:** ✅ Complete (generated pattern).

---

### Hooks (`src/hooks/`)

#### `frontend/src/hooks/useAuth.ts`
**Purpose:** Subscribes to Supabase auth; syncs `useAuthStore`.  
**Key functions/components:** `useAuth` (returns `user`, `session`, `loading`, `signOut`)  
**Inputs:** Supabase client events  
**Outputs:** Zustand updates  
**Dependencies:** `@/integrations/supabase/client`, `@/store/authStore`  
**Status:** ✅ Complete

---

#### `frontend/src/hooks/useTicker.ts`
**Purpose:** Polls `GET /api/v1/market/tickers` when `VITE_API_URL` set; else mock quotes; market session heuristic.  
**Key functions/components:** `useTicker`, `getMarketStatus`, `MOCK_QUOTES`  
**Inputs:** `VITE_API_URL`  
**Outputs:** `{ quotes, flashedTickers, marketStatus }`  
**Dependencies:** `fetch`  
**Status:** ✅ Complete

---

#### `frontend/src/hooks/useVoiceRecorder.ts`
**Purpose:** `MediaRecorder` capture + RMS level for waveform.  
**Key functions/components:** `useVoiceRecorder` (start/stop, `audioBlob`, `audioLevel`)  
**Inputs:** Mic permission  
**Outputs:** `Blob` for STT upload  
**Dependencies:** Web Audio API  
**Status:** ✅ Complete

---

#### `frontend/src/hooks/use-mobile.tsx`
**Purpose:** Responsive breakpoint hook (shadcn sidebar pattern).  
**Key functions/components:** `useIsMobile`  
**Inputs:** window width  
**Outputs:** boolean  
**Dependencies:** React state  
**Status:** ✅ Complete

---

#### `frontend/src/hooks/use-toast.ts`
**Purpose:** Toast shim (re-export / shadcn pattern).  
**Status:** ✅ Complete

---

### API Client (`src/api/`)

#### `frontend/src/api/client.ts`
**Purpose:** Authenticated JSON `fetch` wrapper with Supabase bearer token.  
**Key functions/components:** `apiCall<T>`, exports `API_URL`  
**Inputs:** `VITE_API_URL`, session  
**Outputs:** Parsed JSON  
**Dependencies:** `@/integrations/supabase/client`  
**Status:** ✅ Complete

---

#### `frontend/src/api/query.ts`
**Purpose:** `analyzeQuery` + `transcribeAudio` typings.  
**Key functions/components:** `analyzeQuery`, `transcribeAudio`, `AnalyzeResult`  
**Inputs:** text + session context; audio blob for STT  
**Outputs:** `AnalyzeResult` / transcript  
**Dependencies:** `client.ts`, Supabase for STT headers  
**Status:** ✅ Complete

---

#### `frontend/src/api/market.ts`
**Purpose:** Single-quote fetch.  
**Key functions/components:** `getQuote`  
**Inputs:** ticker  
**Outputs:** `StockQuote`  
**Dependencies:** `client.ts`  
**Status:** ✅ Complete

---

#### `frontend/src/api/chart.ts`
**Purpose:** Chart series from backend or local mock.  
**Key functions/components:** `getChartData`  
**Inputs:** ticker, metric, timeframe  
**Outputs:** `ChartData`  
**Dependencies:** `client.ts` when `VITE_API_URL` set  
**Status:** ✅ Complete

---

#### `frontend/src/api/trades.ts`
**Purpose:** Paper trade execution API.  
**Key functions/components:** `executeTrade`, `TradeResult`  
**Inputs:** order payload  
**Outputs:** fill result  
**Dependencies:** `client.ts`  
**Status:** ✅ Complete

---

#### `frontend/src/api/portfolio.ts`
**Purpose:** **Supabase-only** positions + trades (not FastAPI).  
**Key functions/components:** `getPositions`, `getTrades`  
**Inputs:** Supabase RLS  
**Outputs:** Arrays  
**Dependencies:** `@/integrations/supabase/client`  
**Status:** ✅ Complete

---

### State (`src/store/`)

#### `frontend/src/store/authStore.ts`
**Purpose:** Zustand store for `user`, `session`, `loading`.  
**Key functions/components:** `useAuthStore`  
**Status:** ✅ Complete

---

#### `frontend/src/store/sessionStore.ts`
**Purpose:** Voice/chat mode, ticker, timeframe, session id, prior answers.  
**Key functions/components:** `useSessionStore`, `addAnswer`, `clearSession`  
**Status:** ✅ Complete

---

#### `frontend/src/store/portfolioStore.ts`
**Purpose:** Cached positions, trades, buying power, total value.  
**Key functions/components:** `usePortfolioStore`, `addTrade`, `updatePosition`  
**Status:** ✅ Complete

---

### Other `src/` files

#### `frontend/src/types/api.ts`
**Purpose:** Shared TS interfaces (`Profile`, `Position`, `Trade`, `Query`, `StockQuote`, `ThesisResult`, etc.).  
**Status:** ✅ Complete

---

#### `frontend/src/lib/utils.ts`
**Purpose:** `cn()` Tailwind class merge helper.  
**Status:** ✅ Complete

---

#### `frontend/src/lib/api.ts`
**Purpose:** Duplicate/default `API_URL` export (`https://api.inflect.io` fallback).  
**Status:** ⚠️ Overlaps with `client.ts` — prefer `VITE_API_URL` from `client.ts`

---

#### `frontend/src/utils/constants.ts`
**Purpose:** Brand color constants, example queries, market hours.  
**Status:** ✅ Complete

---

#### `frontend/src/utils/formatters.ts`
**Purpose:** `formatCurrency`, `formatPercent`, `formatDate`, `formatNumber`.  
**Status:** ✅ Complete

---

#### `frontend/src/integrations/supabase/client.ts`
**Purpose:** Typed Supabase client.  
**Inputs:** `VITE_SUPABASE_URL`, **`VITE_SUPABASE_PUBLISHABLE_KEY`** (not `ANON_KEY` name in code)  
**Status:** ✅ Complete

---

#### `frontend/src/integrations/supabase/types.ts`
**Purpose:** Generated Database types for Supabase.  
**Status:** ✅ Complete (🔧 regenerate when schema changes)

---

#### `frontend/src/contexts/AuthContext.tsx`
**Purpose:** Alternative React Context auth provider (not wired in `App.tsx` — app uses `useAuth` hook + Zustand).  
**Status:** ⚠️ Possibly unused duplicate of `hooks/useAuth.ts`

---

#### `frontend/src/vite-env.d.ts`
**Purpose:** Vite client types.  
**Status:** ✅ Complete

---

#### `frontend/src/index.css`
**Purpose:** Global CSS + Tailwind layers + design tokens.  
**Status:** ✅ Complete

---

#### `frontend/src/test/example.test.ts`
**Purpose:** Vitest smoke test.  
**Status:** ✅ Complete (minimal)

---

### Config & tooling (frontend root)

| File | Purpose | Status |
|------|---------|--------|
| `vite.config.ts` | Vite + React + path aliases (`@/`) | ✅ |
| `tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json` | TS project refs | ✅ |
| `tailwind.config.ts` | Theme, content paths | ✅ |
| `postcss.config.js` | PostCSS | ✅ |
| `eslint.config.js` | ESLint flat config | ✅ |
| `components.json` | shadcn generator config | ✅ |
| `vitest.config.ts` | Unit tests | ✅ |
| `playwright.config.ts` / `playwright-fixture.ts` | E2E (if used) | 🔧 |
| `public/*` | favicon, robots, **videos** (hero, CTA, etc.) | ✅ |
| `supabase/config.toml` | Local Supabase settings | ✅ |
| `supabase/migrations/*.sql` | Schema: profiles, positions, trades, queries, RLS, triggers | ✅ |

---

## Data (`inflect/data/`)

Expected layout (populated by download/setup scripts; may be absent in clone):

| Path | Purpose | Status |
|------|---------|--------|
| `sec_filings/raw/10-K`, `10-Q`, `8-K` | Raw SEC HTML | 🔧 Not in workspace snapshot |
| `sec_filings/processed/text/` | Parsed JSON per filing | 🔧 |
| `sec_filings/processed/chunks/` | Chunk JSON | 🔧 |
| `sec_filings/processed/all_chunks.jsonl` | Streaming corpus | 🔧 |
| `sec_filings/processed/embeddings_1024.jsonl` | BGE-M3 vectors for Snowflake | 🔧 |
| `prices/*.csv` | OHLCV per ticker | 🔧 |
| `fundamentals/*.json` | yfinance fundamentals | 🔧 |
| `news/*.json` | Finnhub news | 🔧 |
| `metrics/*.json` | Finnhub metrics | 🔧 |
| `recommendations/*.json` | Finnhub recommendations | 🔧 |
| `sp500_companies.csv` | Universe list | 🔧 (copy also under `backend/scripts/download/`) |

---

## Configuration Files

### Root `.env` (expected at `inflect/.env` — do not commit secrets)

| Variable | Used by | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | Backend | LLM + Whisper fallback |
| `ELEVENLABS_API_KEY` | Backend voice/tts | STT + TTS |
| `ELEVENLABS_VOICE_ID` | Backend tts | Voice id |
| `GEMINI_API_KEY` | Backend vision | Chart image analysis |
| `WOLFRAM_APP_ID` | `wolfram_service`, orchestrator pipeline | Short answers |
| `SNOWFLAKE_*` | RAG scripts + `snowflake_rag_service` | Warehouse DB |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Optional server-side | If backend ever uses Supabase |
| `FINNHUB_KEY_1`, `FINNHUB_KEY_2` | Download scripts | News / metrics / recommendations |
| `CORS_ORIGINS` | `main.py` | CORS allowlist |

### Frontend `frontend/.env.local` (not committed)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | FastAPI base URL (empty → mock + no live ticker fetch) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase anon/publishable key (see `client.ts`) |

### `backend/requirements.txt`
**Status:** ✅ Single source of truth for API dependencies.

### Root `requirements.txt`
**Status:** ⚠️ Corrupted (contains pasted markdown). **Replace or delete**; use `backend/requirements.txt`.

### `railway.toml` / Dockerfile
**Status:** ❌ Not present — deployment expected via **GCP Cloud Run** (`gcloud run deploy … --source .`).

---

## External Services & APIs

| # | Service | Role in Inflect | Files / usage | Env var | Free tier notes |
|---|---------|-----------------|---------------|---------|-----------------|
| 1 | **Groq** | Intent (8B), answer (70B), Whisper STT fallback | `orchestrator/pipeline.py`, `answer_agent.py`, `voice.py`, `thesis_agent.py` | `GROQ_API_KEY` | Rate limits per model (check Groq dashboard) |
| 2 | **ElevenLabs** | STT (primary in `voice.py`), TTS (`tts.py`) | `voice.py`, `tts.py` | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Plan-based characters/minutes |
| 3 | **Google Gemini** | Vision chart analysis | `vision_agent.py` (routed by `vision.py`) | `GEMINI_API_KEY` | Generative free tier quotas |
| 4 | **Snowflake** | `SEC_EMBEDDINGS` vector + text store; API uses keyword search | `snowflake_rag_service.py`, scripts | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA` | Warehouse consumes credits |
| 5 | **Supabase** | Auth (PKCE/session), tables: profiles, positions, trades, queries | `frontend` client, `AppResearch`, `AppPortfolio` | `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` | Free tier project limits |
| 6 | **Wolfram Alpha** | Short computational result when RAG thin + query looks computational | `wolfram_service.py`, `pipeline.py` | `WOLFRAM_APP_ID` | Developer API request limits |
| 7 | **yfinance** | Quotes, history, thesis context | `market.py`, `market_service.py`, `chart_agent.py`, `trade_agent.py`, `thesis_agent.py`, download scripts | — | Unofficial; rate limits / breakage possible |
| 8 | **Finnhub** | News, recommendations, metrics download scripts | `download_*.py` | `FINNHUB_KEY_*` | Free tier API caps |
| 9 | **GCP Cloud Run** | Host FastAPI container | N/A (CLI) | GCP project + IAM | Pay per use |
| 10 | **Vercel** | Host frontend | `frontend` build | Vercel env mirrors `VITE_*` | Hobby/pro limits |

---

## Key Flows

### 1. Voice Query Flow
1. User holds mic / space — `useVoiceRecorder` captures audio blob.  
2. `transcribeAudio` → `POST /api/v1/voice/transcribe` (ElevenLabs → Groq).  
3. `submitQuery` → `POST /api/v1/query/analyze` with transcript.  
4. Backend: intent → (price / trade / thesis / research) routing; research pulls Snowflake chunks → Groq answer.  
5. Optional: `POST /api/v1/tts/synthesize` (not used by `AppResearch.tsx` today — **browser TTS** via `speechSynthesis`).  
6. Right panel + query log update; Supabase `queries` insert.

### 2. Chat Query Flow
Same as (3–6) without STT; chat thread in `JarvisChatPanel` / `ChatThread`.

### 3. Trade Thesis Flow
User triggers thesis from output → `POST /api/v1/thesis/generate` with `{ ticker }` → **`ThesisAgent`** (`thesis_agent.py`) → LLM JSON + **`compute_verdict`** → `ThesisCard`.

### 4. Paper Trade Flow
1. Intent `trade` + parsed quantity/ticker → `TradeModal`.  
2. `POST /api/v1/trades/execute` → **`TradeAgent`** returns fill price (yfinance + slippage).  
3. **Intended:** Supabase insert/update from client (🔧 verify `AppResearch` persists trades/positions — may need implementation beyond store).

### 5. Data Pipeline Flow
SEC HTML (`sec_edgar_scraper`) → `sec_html_parser` → `chunk_documents` → `convert_to_jsonl` → `generate_embeddings` → `upload_to_snowflake` / `upload_to_snowflake_bulk`.

---

## Team Responsibilities

| Area | Owner | Status |
|------|-------|--------|
| Frontend UI | Aman | ✅ Complete |
| Backend API | Teammate 2 | 🔧 In progress |
| Data / AI | Teammate 3 | 🔧 Data scripts ✅ — Snowflake upload ongoing |
| Full stack / DevOps | Teammate 4 | 🔧 GCP + env |

---

## What Needs To Be Done

| Task | File(s) | Est. | Priority |
|------|---------|------|----------|
| Fix root `requirements.txt` or remove | `/requirements.txt` | 15m | **HIGH** |
| Confirm trade flow persists to Supabase after `executeTrade` | `AppResearch.tsx`, possibly new API route | 2–4h | **HIGH** |
| Replace portfolio mock random P&L with live quotes | `AppPortfolio.tsx` | 2h | **MEDIUM** |
| Parameterize hardcoded `D:/` paths in scripts | `upload_to_snowflake*.py`, `chunk_documents.py`, etc. | 2h | **MEDIUM** |
| Implement Pinecone indexer or remove | `pinecone_indexer.py` | 2h | **LOW** |
| Query-time BGE-M3 embedding + Snowflake cosine | `snowflake_rag_service.py`, `RetrievalAgent`, new embedding service | 1–2d | **MEDIUM** |
| Deduplicate `AuthContext` vs `useAuth` / `ProtectedRoute` | `contexts/`, `components/auth/` | 1h | **LOW** |
| Align ElevenLabs STT API with latest docs | `voice.py` | 1h | **MEDIUM** |
| Add `sources.txt` + demo video | repo root | — | **HIGH** (hackathon) |

---

## Environment Setup (new teammate)

1. **Clone** the repository.  
2. **Python 3.10+:** `cd backend && pip install -r requirements.txt`  
3. **Copy env:** create `inflect/.env` from team template (keys above).  
4. **Run API:** `cd backend && uvicorn app.main:app --reload --port 8000`  
5. **Node:** `cd frontend && npm install` (or `bun install`)  
6. **Frontend env:** `frontend/.env.local` with `VITE_API_URL=http://localhost:8000` and Supabase keys.  
7. **Run web:** `npm run dev` (Vite default port 5173).  
8. **Test:** `curl http://localhost:8000/health` → `ok`; sign up → `/app/research` with backend URL set.

---

## API Endpoint Reference

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/health` | Liveness | — | `{ status, version }` |
| POST | `/api/v1/query/analyze` | Main research | JSON `QueryRequest` | `AnalyzeResult` shape |
| POST | `/api/v1/voice/transcribe` | STT | multipart `audio` | `{ transcript, confidence }` |
| GET | `/api/v1/market/quote` | Quote | `?ticker=` | Quote + volume |
| GET | `/api/v1/market/tickers` | Ticker bar (30) | — | `TickerQuote[]` |
| GET | `/api/v1/market/batch` | Batch quotes | — | `{ quotes, timestamp, count }` |
| POST | `/api/v1/thesis/generate` | Thesis | `{ ticker }` | Thesis JSON |
| POST | `/api/v1/trades/execute` | Paper fill | `TradeRequest` | Fill result |
| POST | `/api/v1/tts/synthesize` | TTS | `{ text }` | MP3 stream |
| POST | `/api/v1/vision/analyze` | Chart image | multipart `image` | `{ summary }` |
| POST | `/api/v1/rag/search` | Debug RAG | `{ ticker?, query, limit? }` | `{ chunks }` |
| GET | `/api/v1/chart/data` | Chart series | `?ticker=&metric=&timeframe=` | `{ x, y, filingDates? }` |

**Implementation note:** `POST /query/analyze` is implemented by **`app/orchestrator/pipeline.py`** (`run_query_pipeline`), not in `api/v1/query.py` (router only).

---

*Generated for internal team use. Update this file when adding routes, env vars, agents, or ownership changes.*
