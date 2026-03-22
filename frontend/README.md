# Inflect — Frontend

React + Vite SPA for [Inflect](../README.md): research chat, portfolio home, ticker bar, voice input.

## Commands

```bash
npm install
npm run dev          # http://localhost:8080 (see vite.config.ts)
npm run build
npm run test         # Vitest
npm run test:e2e     # Playwright (starts API :8000 + dev:e2e :8080)
```

## Environment

- **Local API:** copy [.env.example](./.env.example) to `.env.local` and set `VITE_API_URL` (e.g. `http://127.0.0.1:8000`).
- **Supabase:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` (required for real auth).
- **Dev default:** [.env.development](./.env.development) points at local backend.
- **E2E:** [.env.e2e](./.env.e2e) enables `VITE_E2E_AUTH` for Playwright only.

Full stack setup lives in the [root README](../README.md).
