# AsyncApply

An agent pipeline that reads a job posting, evaluates real fit against your
CV, drafts a tailored CV and cover letter, and finds a contact worth reaching
out to — grounded in your actual profile, never fabricated.

Extracted from a larger personal productivity app on 2026-09-28. This repo is
AsyncApply on its own: backend, frontend, and nothing else.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, Postgres, `uv`
- Frontend: React, Vite, Tailwind
- LLM: OpenRouter (OpenAI-compatible), schema-constrained JSON responses
- Browser automation: Playwright (Chromium), a shared singleton browser process

## Local setup

```bash
cp backend/.env.example backend/.env   # add your OPENROUTER_API_KEY
cp backend/services/asyncapply/context/user/profile.example.yml backend/services/asyncapply/context/user/profile.yml
# edit profile.yml with your real CV/profile — it is gitignored, never committed

docker compose up -d --build
```

Backend: http://localhost:8000 · Frontend: http://localhost:3000

## Status

Currently single-tenant, no auth. Multi-tenancy (Firebase auth, per-user
profiles, admin console, token budgets) is in progress.
