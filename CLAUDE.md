# GrACE-Demo — operational notes for coding agents

**Classroom cut of GrACE. The student's cloud LLM (any vendor) is the interface — there is
no web app.** If you are the agent a student mounted: read
**[docs/LLM_OPERATOR.md](docs/LLM_OPERATOR.md)** (Session 0 first: their API key, their
vendor, how to run), then [INSTALL.md](INSTALL.md) and [docs/ONBOARDING.md](docs/ONBOARDING.md).
Pasteable prompt: [docs/LLM_SYSTEM_PROMPT.md](docs/LLM_SYSTEM_PROMPT.md).
Scope: [docs/CHARTER.md](docs/CHARTER.md).

## Tech stack

- **Python 3.14** managed with **uv** (`pyproject.toml` + `uv.lock`; interpreter pinned in
  `.python-version`). Always use the repo venv: `.venv/bin/python`.
- **API:** FastAPI + Uvicorn on `localhost:8000` (`uvicorn src.api.main:app --port 8000`,
  one worker). OpenAPI at `/docs`.
- **Relational DB:** PostgreSQL 17, database **`grace_demo`**; SQLAlchemy 2.0; Alembic
  (`alembic upgrade head`).
- **Graph DB:** ArcadeDB 26.5.1 in Docker (`docker/docker-compose.arcade.yml`, loopback
  ports 2480/2424, named volume, laptop-sized JVM heap via `ARCADE_HEAP`), database
  **`grace_demo`** (`ARCADE_DATABASE` in `.env`). OpenCypher for DML/DQL, SQL for DDL and
  vector search.
- **LLM provider abstraction** (`src/shared/llm_provider.py`): `config/discovery.yaml`
  `llm:` block selects `anthropic` | `openai` (any OpenAI-compatible: OpenAI, DeepSeek,
  Groq, Together, xAI, …) | `ollama`; key in `.env` `LLM_API_KEY`; `airgap_mode: false`
  for cloud. `POST /api/llm/config/test` proves it; `POST /api/llm/config` persists it.
- **Embeddings** (`src/shared/embeddings.py`): `GRACE_EMBED_PROVIDER=auto` (default) →
  OpenAI-compatible `/v1/embeddings` only when `GRACE_EMBED_API_KEY` is set or the chat
  vendor is real OpenAI; otherwise **none** and every consumer degrades (semantic strategy
  empty, ANN entity resolution skipped, lexical coverage mapping). `openai` / `ollama` /
  `none` are explicit overrides.
- **Document processing:** Docling (PDF/DOCX/XLSX/PPTX/HTML/TXT/MD/CSV + image OCR).
  `KMP_DUPLICATE_LIB_OK=TRUE` + `OMP_NUM_THREADS=1` in `.env` on macOS.
- **Retrieval:** BM25 + graph (+ semantic when embeddings are on) fused by RRF; CPU
  cross-encoder rerank when the model is cached (`bash scripts/prefetch-models.sh`),
  otherwise fusion order. Indexes rebuilt via `POST /api/retrieval/build-indexes`
  (`import_extraction.py` does this for you).
- **Observability:** in-process OpenTelemetry + `GET /metrics`. No Grafana in this demo.
- **MCP server:** `src/mcp_server/` over stdio (`python -m src.mcp_server`;
  sample config `scripts/claude_desktop_config.example.json`).
- **Schema:** Pydantic v2 is the source of truth → JSON Schema (generated) → optional RDF.

## The produce track (what the operating LLM runs)

`grace-claude-skills/<skill>/SKILL.md` + `grace-claude-skills/scripts/*.py`
(any agent; see `grace-claude-skills/README.md`):
process documents (`src.discovery.batch_runner`) → `export_corpus.py` → author CQs →
`import_cqs.py` → author ontology → `map_coverage.py` → `auto_accept.py` (ratify + ArcadeDB
DDL + intent meta-layer; **no human schema gate**) → author extractions →
`import_extraction.py --doc-file …` → **intent Q&A** (`intent_query.py`, `intent_apply.py`;
human may skip) → answer (`POST /api/retrieval/query`, `POST /api/regeneration/query`).
Reference outputs: `data/demo-corpus/samples/`. LLM-free proof of the whole loop:
`bash scripts/demo-fastpath.sh`.

## How to run things

- Install: `uv python install 3.14 && uv sync --extra dev && source .venv/bin/activate`
- Config: `cp .env.example .env` (edit `LLM_API_KEY`, `DATABASE_URL` user); pick the
  vendor in `config/discovery.yaml`.
- Postgres: `createdb grace_demo`; ArcadeDB: `docker compose -f docker/docker-compose.arcade.yml up -d`
  then create database `grace_demo` (INSTALL.md Step 5).
- Migrate: `alembic upgrade head`. Start: `uvicorn src.api.main:app --port 8000`.
- Gates: `bash scripts/smoke-demo.sh` (plumbing), `bash scripts/demo-fastpath.sh`
  (whole loop; `--reset` recreates the demo DBs).
- Tests (maintainers): `python -m pytest tests/ -q` — auto-redirects to the isolated
  `grace_demo_test` Postgres DB and `grace_demo_test` ArcadeDB (create both once, see
  `grace-claude-skills/grace-testing-protocol/SKILL.md`). Never point tests at live data.
  Known-failure registry: `docs/test-suite-allowlist.md`.

## Critical rules

- **Secrets never committed.** `LLM_API_KEY` and all credentials live only in `.env`
  (gitignored). Never paste real secret values into chat, logs, code, docs, or commits.
- **The LLM proposes the ontology; auto-accept activates it.** Humans contribute *why*
  (intent Q&A), not schema click-through. Never send the human to a web UI — none exists.
- **Provenance is mandatory.** Every extracted fact carries a source, temporal validity,
  and a certainty band (never raw numbers in what the human sees).
- **Pydantic is the source of truth.** JSON Schema is generated, never hand-written.
- **Test-DB isolation.** `pytest` uses the `_test` siblings; never the demo/live data.
- **Long-running pipelines run out-of-process** (CLIs spawned by routes), never inside
  the API process.
- **Dev credentials are dev-only.** ArcadeDB `root`/`gracedev` is for localhost; rotate
  before any non-localhost exposure (the API warns at startup).
- **Don't guess.** If a configuration or architectural choice is unclear, stop and ask.

## Directory layout

```
src/                  Engine (discovery, ontology, extraction, graph, retrieval, regeneration,
                      ingestion, analytics, mcp_server, shared, api, …)
grace-claude-skills/  Skills + helper scripts the operating LLM follows (any vendor)
data/demo-corpus/     Fictional sample corpus (documents/, email/) + reference samples/
alembic/              Database migrations
config/               YAML/JSON configuration (discovery.yaml holds the llm: block)
docker/               docker-compose.arcade.yml
scripts/              smoke-demo.sh, demo-fastpath.sh, prefetch-models.sh, set-api-key.sh, …
seeds/                Reference ontologies (FIBO, LKIF, PROV-O, Schema.org)
tests/                Test suite (mirrors src/)
docs/                 LLM_OPERATOR, LLM_SYSTEM_PROMPT, ONBOARDING, USER_MANUAL, INTENT_QA, CHARTER, GrACE-Product
```
