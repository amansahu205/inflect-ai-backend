# Inflect

AI-assisted market research and portfolio UI: text or voice questions, structured metrics, SEC-grounded context, and a live ticker strip. Built for **HooHacks 2026**.

**Disclaimer:** Educational demo only. Not investment advice.

## Stack

- **Frontend:** React, TypeScript, Vite, Tailwind, Zustand, TanStack Query, React Router
- **Backend:** Python, FastAPI, Uvicorn
- **Auth:** Supabase (profiles, trades, queries)
- **Data:** Snowflake (prices, fundamentals, SEC RAG)
- **LLM:** Groq; optional Gemini / Wolfram
- **Voice:** ElevenLabs; optional Groq STT fallback
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
- `GET /api/v1/market/tickers`, `/quote`, `/history`, `/metric`
- `POST /api/v1/voice/transcribe`
- `POST /api/v1/thesis/generate`

## Security

Do not commit `.env` or keys. Do not set `VITE_E2E_AUTH` in production builds.
