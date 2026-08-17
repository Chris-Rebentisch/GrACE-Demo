# Installing GrACE-Demo

**If you are an AI agent setting this up, read this file top to bottom, then `docs/ONBOARDING.md` and `docs/LLM_OPERATOR.md`.**

## 30-second orientation

GrACE-Demo compresses documents (and optional email) into a knowledge graph and answers questions with citations. The **cloud LLM** is the default brain. **Ollama is optional** — even a small local embed model can lock a student laptop.

The ontology is **authored by the LLM and auto-accepted**. Humans contribute intent in Chat, not by ratifying schema types.

## Install flow

```
INSTALL.md (this file)
  1. OS + prerequisites
  2. Python deps (uv)
  3. .env
  4. Postgres database `grace_demo`
  5. ArcadeDB (Docker) + database `grace_demo`
  6. alembic upgrade head
  7. API + frontend
  8. scripts/smoke-demo.sh   ← must pass before you demo this to anyone
then docs/ONBOARDING.md
```

## Step 1 — Prerequisites

| Component | macOS (Homebrew) | Windows |
|-----------|------------------|---------|
| Docker | `brew install colima docker docker-compose` then `colima start --cpu 2 --memory 4 --disk 20` | Docker Desktop |
| PostgreSQL 17 | `brew install postgresql@17` then `brew services start postgresql@17` | `winget install -e --id PostgreSQL.PostgreSQL.17` |
| Node.js 20+ | `brew install node` | `winget install -e --id OpenJS.NodeJS.LTS` |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `irm https://astral.sh/uv/install.ps1 \| iex` |
| Ollama | **optional** — only if you set `GRACE_EMBED_PROVIDER=ollama` | optional |

Python is **not** installed separately; `uv` provisions the pin in `.python-version` (3.14).

## Step 2 — Dependencies

```bash
cd GrACE-Demo
uv python install 3.14
uv sync --extra dev
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
cd frontend && npm install && cd ..
```

## Step 3 — `.env`

```bash
cp .env.example .env
```

Fill in:

- `LLM_API_KEY` — Anthropic (`sk-ant-…`) if you keep the default provider, or your OpenAI/DeepSeek/Groq key if you switch `config/discovery.yaml`.
- `GRACE_EMBED_PROVIDER=openai` (default) **and** an embeddings-capable key (`GRACE_EMBED_API_KEY` or the same `LLM_API_KEY`). Cloud embeddings request **768 dimensions** so they fit ArcadeDB.
- `DATABASE_URL` — point at database **`grace_demo`**, not `grace`.
- `ARCADE_DATABASE=grace_demo`

To use a local embedder instead: `GRACE_EMBED_PROVIDER=ollama`, install Ollama, `ollama pull nomic-embed-text`.

## Step 4 — Postgres

```bash
createdb grace_demo    # or: psql postgres -c 'CREATE DATABASE grace_demo;'
```

## Step 5 — ArcadeDB

```bash
docker compose -f docker/docker-compose.arcade.yml up -d
```

Create the demo graph database once (ArcadeDB default login `root` / `gracedev`):

```bash
curl -s -u root:gracedev -X POST http://localhost:2480/api/v1/server \
  -H 'Content-Type: application/json' \
  -d '{"command":"create database grace_demo"}'
```

Ignore an error if `grace_demo` already exists.

## Step 6 — Migrations

```bash
alembic upgrade head
```

## Step 7 — Run

Terminal A:

```bash
uvicorn src.api.main:app --reload --port 8000
```

Terminal B:

```bash
cd frontend && npm run dev
```

- API: http://localhost:8000
- UI: http://localhost:3000
- Health: http://localhost:8000/api/health
- Metrics: http://localhost:8000/metrics
- Graph health: http://localhost:8000/api/graph/health

## Step 8 — Smoke test (required before a live demo)

With the API up:

```bash
bash scripts/smoke-demo.sh
```

Exit 0 means health, metrics, graph connectivity, and embedding unit tests passed. **Do not present this repo until that script is green on the machine you will use.**

## Provider cheat sheet

| Goal | `config/discovery.yaml` `llm.provider` | `.env` |
|---|---|---|
| Claude | `anthropic` | `LLM_API_KEY=sk-ant-…` |
| ChatGPT | `openai` | `LLM_API_KEY=sk-…`, `base_url: https://api.openai.com/v1` |
| DeepSeek | `openai` | DeepSeek key + `https://api.deepseek.com/v1` |
| Groq | `openai` | Groq key + `https://api.groq.com/openai/v1` |
| Local chat | `ollama` | no cloud key; Ollama running |

You can also change provider/model in **Settings** after the UI is up.

## Platform notes

- OCR backend is automatic (Apple Vision on macOS, RapidOCR elsewhere).
- Postgres username is your macOS user; on Windows often `postgres`.
- One uvicorn worker only.
- Grafana / Prometheus compose files may exist in `docker/` from the parent product; **do not start them** for this demo.
