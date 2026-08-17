# Installing GrACE-Demo

**If you are an AI agent setting this up for a student:** read
[docs/LLM_OPERATOR.md](docs/LLM_OPERATOR.md) Session 0 first (their cloud vendor,
`LLM_API_KEY`, endpoints), then run this file top to bottom, then
[docs/ONBOARDING.md](docs/ONBOARDING.md). Stop and show the error if any step fails.

## 30-second orientation

GrACE-Demo compresses documents (and optional email) into a knowledge graph and answers
questions from it with evidence and certainty bands. The **student's cloud LLM** is the
brain *and* the interface — there is no web app. **Ollama is not required.**

Three local services: PostgreSQL 17 (relational store), ArcadeDB in Docker (graph
store), and the GrACE API (FastAPI on `localhost:8000`). Databases are named
**`grace_demo`**.

## Install flow

```
1. OS prerequisites (Docker, PostgreSQL 17, uv)
2. Python deps (uv)                        uv sync --extra dev
3. .env                                    cp .env.example .env  → LLM_API_KEY, DATABASE_URL user
4. Postgres database                       createdb grace_demo
5. ArcadeDB (Docker) + database            docker compose … up -d ; create database grace_demo
6. Migrations                              alembic upgrade head
7. API                                     uvicorn src.api.main:app --port 8000
8. Smoke                                   bash scripts/smoke-demo.sh
9. Fast path (whole loop, no LLM call)     bash scripts/demo-fastpath.sh
then docs/ONBOARDING.md
```

## Step 1 — Prerequisites

| Component | macOS (Homebrew) | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Docker | `brew install colima docker docker-compose` then `colima start --cpu 2 --memory 4 --disk 20` (or Docker Desktop) | Docker Desktop (WSL 2 backend) | `apt install docker.io docker-compose-v2` (or Docker Desktop) |
| PostgreSQL 17 | `brew install postgresql@17 && brew services start postgresql@17` | `winget install -e --id PostgreSQL.PostgreSQL.17` | `apt install postgresql-17` (pgdg repo) |
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `irm https://astral.sh/uv/install.ps1 \| iex` | same as macOS |
| Git | Xcode CLT / `brew install git` | Git for Windows | `apt install git` |

Notes:
- Python is **not** installed separately: `uv` provisions the pinned interpreter
  (`.python-version` = 3.14).
- Give Docker at least **4 GB** RAM (ArcadeDB's JVM defaults to a 1–3 GB heap here).
- Postgres user: on macOS/Linux it is usually your OS username with no password; on
  Windows it is usually `postgres` with the password you set at install (make sure
  `psql` / `createdb` are on your PATH, e.g. `C:\Program Files\PostgreSQL\17\bin`).

## Step 2 — Dependencies

```bash
cd GrACE-Demo
uv python install 3.14
uv sync --extra dev
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
```

`uv sync` pulls the document-processing stack (Docling, torch, sentence-transformers) —
a few GB the first time; give it a few minutes.

## Step 3 — `.env`

```bash
cp .env.example .env
```

Edit `.env` (it is gitignored — never commit it):

| Key | Set to |
|---|---|
| `LLM_API_KEY` | the student's **chat** cloud key (Anthropic, OpenAI, DeepSeek, Groq, Together, xAI, …). Then match `config/discovery.yaml` `llm.provider` / `llm.model` / `llm.base_url` to that vendor — cheat sheet below and in the yaml comments. |
| `DATABASE_URL` | `postgresql+psycopg2://<your-pg-user>@localhost:5432/grace_demo` (add `:<password>` after the user on Windows: `postgresql+psycopg2://postgres:<pw>@localhost:5432/grace_demo`) |
| `ARCADE_DATABASE` | `grace_demo` (already set) |
| `GRACE_EMBED_PROVIDER` | leave `auto` (see "Embeddings" below) |

## Step 4 — Postgres

```bash
createdb grace_demo
# Windows / password auth:  psql -U postgres -c "CREATE DATABASE grace_demo;"
```

## Step 5 — ArcadeDB

```bash
docker compose -f docker/docker-compose.arcade.yml up -d
```

Create the demo graph database once (dev login `root` / `gracedev`):

```bash
curl -s -u root:gracedev -X POST http://localhost:2480/api/v1/server \
  -H 'Content-Type: application/json' \
  -d '{"command":"create database grace_demo"}'
```

`{"result":"ok"}` — an "already exists" error on re-run is fine. (Windows without
curl: open http://localhost:2480 in a browser → Studio → login → run the SQL
`create database grace_demo` from the server tab.)

## Step 6 — Migrations

```bash
alembic upgrade head
```

## Step 7 — Run the API

```bash
uvicorn src.api.main:app --port 8000
```

Leave it running; open a second terminal for everything else.

- Health: http://localhost:8000/api/health → `{"status":"ok","product":"GrACE-Demo"}`
- Graph health: http://localhost:8000/api/graph/health
- Metrics: http://localhost:8000/metrics
- OpenAPI: http://localhost:8000/docs

The startup log tells you the embeddings posture (`embeddings_disabled` is normal with a
chat-only key). One uvicorn worker only.

## Step 8 — Smoke test

```bash
bash scripts/smoke-demo.sh
```

Exit 0 = health, metrics, graph connectivity, and the embedding unit tests (mocked HTTP,
no GPU) passed. **Do not demo until this is green on the machine you will use.**

## Step 9 — Fast path (proves the whole loop, no LLM call)

```bash
bash scripts/demo-fastpath.sh
```

Processes the sample corpus, imports the shipped sample CQs / ontology / extractions,
auto-accepts the ontology, writes the graph, and asks it a question. Idempotent — run
it as often as you like. `--reset` recreates the `grace_demo` databases first (asks
for confirmation; restart the API afterwards).

Then go to [docs/ONBOARDING.md](docs/ONBOARDING.md) and let the student's LLM do the
authoring itself.

## Optional — reranker model (one-time network)

Retrieval reranks results with a small CPU cross-encoder. The API runs offline
(`HF_HUB_OFFLINE=1`), so on a fresh machine the model is not cached and retrieval
simply keeps fusion order. To enable reranking, once, with network:

```bash
bash scripts/prefetch-models.sh
```

## Provider cheat sheet

Set these in `config/discovery.yaml` under `llm:` (or let the LLM do it via
`POST /api/llm/config` once the API is up). Keep `airgap_mode: false` for any cloud vendor.

| Student's cloud | `llm.provider` | `llm.model` (example) | `llm.base_url` |
|---|---|---|---|
| Claude (Anthropic) | `anthropic` | `claude-haiku-4-5-20251001` | `""` (unused) |
| ChatGPT (OpenAI) | `openai` | `gpt-4.1-mini` | `https://api.openai.com/v1` (or `""`) |
| DeepSeek | `openai` | `deepseek-chat` | `https://api.deepseek.com/v1` |
| Groq | `openai` | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1` |
| Together | `openai` | vendor model id | `https://api.together.xyz/v1` |
| xAI / other OpenAI-compatible | `openai` | vendor model id | that vendor's `/v1` root |
| Local Ollama (optional) | `ollama` | e.g. `qwen2.5:7b` | `http://localhost:11434` |

Verify without saving: `POST /api/llm/config/test`; save: `POST /api/llm/config`
(writes the yaml and `LLM_API_KEY`); inspect: `GET /api/llm/config` (key masked),
`GET /api/llm/registry`.

## Embeddings (optional)

`GRACE_EMBED_PROVIDER=auto` turns vectors **on** only when an OpenAI-compatible
embeddings key is available (`GRACE_EMBED_API_KEY`, or `LLM_API_KEY` when the chat
vendor is real OpenAI) and **off** otherwise. Off is fine for the demo: retrieval uses
keyword (BM25) + graph strategies, entity resolution uses exact/alias matching, CQ
coverage uses lexical matching. To turn vectors on with a chat-only key, add an
OpenAI-compatible embeddings key as `GRACE_EMBED_API_KEY`, or install Ollama, run
`ollama pull nomic-embed-text`, and set `GRACE_EMBED_PROVIDER=ollama`.

## Platform notes

- macOS: `KMP_DUPLICATE_LIB_OK=TRUE` and `OMP_NUM_THREADS=1` in `.env` prevent an
  OpenMP crash in Docling. Harmless elsewhere.
- OCR backend is automatic (Apple Vision on macOS, RapidOCR elsewhere).
- Docker on Apple Silicon / Windows ARM: the ArcadeDB image is multi-arch.
- Ports used: 8000 (API), 5432 (Postgres), 2480/2424 (ArcadeDB).

## Uninstall / reset

`bash scripts/demo-fastpath.sh --reset` recreates the demo databases.
`docker compose -f docker/docker-compose.arcade.yml down -v` removes ArcadeDB and its
volume. `dropdb grace_demo` removes the Postgres database. Delete the folder.
