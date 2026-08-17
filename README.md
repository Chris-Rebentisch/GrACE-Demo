# GrACE-Demo

**Graph as Auditable Context Engine — classroom / student edition.**

GrACE turns documents (and optionally email) into an **auditable knowledge graph**:
every fact carries its source, a certainty band, and — uniquely — the *human's reasoning*
for why things are the way they are. You ask questions in plain language; answers come
from the graph with evidence.

**There is no web app in this demo. Your own cloud LLM is the interface.** Open this
folder in Claude Code, Cursor, ChatGPT/Codex, Gemini, Copilot — any agent that can read
files, run a terminal, and call HTTP — give it your API key once, and it:

1. installs and starts the GrACE stack (Postgres + ArcadeDB + the API),
2. reads your documents and **authors** competency questions and an ontology,
3. **auto-accepts** the ontology (no clicking through schema types),
4. **extracts** facts into the graph,
5. **interviews you for the *why*** behind the important facts (you may skip),
6. answers your questions from the graph, with certainty bands and sources.

It works with **any** cloud vendor — Anthropic (Claude), OpenAI (ChatGPT), DeepSeek,
Groq, Together, xAI, or any OpenAI-compatible endpoint. Embeddings are optional: with a
chat-only key (Anthropic, DeepSeek, Groq, …) retrieval uses keyword + graph strategies.

## Start here

| You are… | Read |
|---|---|
| **An LLM / coding agent** the student mounted | **[docs/LLM_OPERATOR.md](docs/LLM_OPERATOR.md)** — your operating manual. Session 0 first. |
| Pasting a system prompt into Claude / ChatGPT / Cursor | **[docs/LLM_SYSTEM_PROMPT.md](docs/LLM_SYSTEM_PROMPT.md)** (one page) |
| A human installing the stack (or checking what the LLM did) | **[INSTALL.md](INSTALL.md)** |
| Running the first document → graph → answer loop | **[docs/ONBOARDING.md](docs/ONBOARDING.md)** |
| The human sitting with the LLM | **[docs/USER_MANUAL.md](docs/USER_MANUAL.md)** |
| Curious what "intent Q&A" is | **[docs/INTENT_QA.md](docs/INTENT_QA.md)** |
| Wondering what is in / out of this cut | **[docs/CHARTER.md](docs/CHARTER.md)** |
| Wanting the whole-product background | [docs/GrACE-Product.md](docs/GrACE-Product.md) |

## The 10-minute version

```bash
git clone <this repo> GrACE-Demo && cd GrACE-Demo
# prerequisites: Docker, PostgreSQL 17, uv  (see INSTALL.md — macOS + Windows + Linux)
uv python install 3.14 && uv sync --extra dev && source .venv/bin/activate
cp .env.example .env            # put your cloud key in LLM_API_KEY; pick the vendor in config/discovery.yaml
createdb grace_demo
docker compose -f docker/docker-compose.arcade.yml up -d
curl -s -u root:gracedev -X POST http://localhost:2480/api/v1/server \
  -H 'Content-Type: application/json' -d '{"command":"create database grace_demo"}'
alembic upgrade head
uvicorn src.api.main:app --port 8000          # leave running; new terminal for the rest
bash scripts/smoke-demo.sh                    # API + graph up
bash scripts/demo-fastpath.sh                 # whole loop with shipped samples, no LLM call
```

Then hand the conversation to your LLM: it reads `docs/LLM_OPERATOR.md`, authors its
own CQs / ontology / extractions for `data/demo-corpus/` (or your files) with the
skills in `grace-claude-skills/`, and starts the intent Q&A.

## What's in the box

- `src/` — the GrACE engine (FastAPI on `:8000`; discovery, ontology, extraction,
  graph, retrieval, regeneration, ingestion, MCP server, …).
- `grace-claude-skills/` — the step-by-step skills + deterministic helper scripts the
  operating LLM follows (any vendor; the folder name is historical).
- `data/demo-corpus/` — a fictional insurance mini-corpus (3 documents + 1 email) and
  reference sample outputs (`samples/`) so the loop can be proven without an LLM.
- `scripts/smoke-demo.sh`, `scripts/demo-fastpath.sh`, `scripts/prefetch-models.sh`.
- `docs/` — the manuals above.

## Defaults that matter

- **LLM:** the student's cloud vendor (`config/discovery.yaml` `llm:` + `.env` `LLM_API_KEY`). Default vendor in the yaml is Anthropic; Session 0 switches it.
- **Embeddings:** `GRACE_EMBED_PROVIDER=auto` — on only if an OpenAI-compatible embeddings key is available; otherwise off (keyword + graph retrieval).
- **Ontology:** authored by the LLM, **auto-accepted** (`grace-auto-accept`).
- **Databases:** Postgres `grace_demo`, ArcadeDB `grace_demo`. Tests use `_test` siblings.
- **Not included:** web UI, Grafana/Prometheus, the internal analytics/governance harnesses (see the charter).

## Safety / privacy

`.env` is gitignored — never commit it or paste keys anywhere. The sample corpus is
fictional. Do not point the demo at documents you are not allowed to process.
Dev-only credentials (`root`/`gracedev` for ArcadeDB) are for localhost.

## License

MIT — see [LICENSE](LICENSE).
