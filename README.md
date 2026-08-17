# GrACE-Demo

**Graph as Auditable Context Engine — college / classroom deployment.**

GrACE turns documents (and optionally email) into an **auditable knowledge graph**. You ask questions in plain language. Every answer carries a certainty band and links back to source evidence.

This repository is the **public demo cut**: cloud LLMs by default (Claude, ChatGPT, DeepSeek, Groq, …), cloud embeddings by default, ontology **auto-accepted** by the model (humans contribute intent in chat, not by clicking through schema review). It is **not** a dump of the internal GrACE factory or any customer corpus.

> Keep this repository **private** until `bash scripts/smoke-demo.sh` exits 0 **on the machine you will demo from**. Packaging smoke (API health, metrics, ArcadeDB, embeddings unit tests) and sample-ontology auto-accept were verified 2026-08-17. Chat-with-citation still needs your cloud `LLM_API_KEY` plus extraction (see [docs/ONBOARDING.md](docs/ONBOARDING.md)).

## Read these, in order

| Audience | Doc |
|---|---|
| Anyone installing | **[INSTALL.md](INSTALL.md)** |
| End user (student / operator in the UI) | **[docs/USER_MANUAL.md](docs/USER_MANUAL.md)** |
| LLM / coding agent driving the pipeline | **[docs/LLM_OPERATOR.md](docs/LLM_OPERATOR.md)** |
| First document → graph → ask loop | **[docs/ONBOARDING.md](docs/ONBOARDING.md)** |
| What is in vs out of this cut | **[docs/CHARTER.md](docs/CHARTER.md)** |

## What a working demo looks like

1. Install prerequisites (Docker, Postgres 17, uv, Node). **Ollama is optional.**
2. `uv sync --extra dev` → ArcadeDB via Docker → `alembic upgrade head` → API + frontend.
3. An LLM (or you) authors competency questions + a schema, then **auto-accepts** it.
4. Extract facts from the sample corpus (or your files / Gmail / IMAP / Exchange).
5. Ask in **Chat**. Inspect retrieval. Capture *why* via intent elicitation.

## Defaults that matter

- **Chat LLM:** cloud (Anthropic by default in `config/discovery.yaml`; switch in Settings).
- **Embeddings:** cloud OpenAI-compatible, **768 dimensions** (ArcadeDB index compatible). Set `GRACE_EMBED_PROVIDER=ollama` only if you want a local embed model.
- **Ontology:** auto-accept (`grace-claude-skills/grace-auto-accept`). No Guided Review gate.
- **No graph viewer** in the nav (desktop LLMs can draw graphs; this UI was unreliable).
- **No Grafana stack.** `GET /api/health` and `GET /metrics` are enough.
- **Mail:** Gmail, IMAP, and Exchange are opt-in; sample `.txt` / `.eml` files work without connecting an inbox.

## License / status

Internal demo packaging for a college presentation. Do not publish customer documents, API keys, or GOLD dumps. `.env` is gitignored.
