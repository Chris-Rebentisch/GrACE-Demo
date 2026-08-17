# GrACE-Demo charter

Classroom / public cut of GrACE. Scope locked 2026-08-17.

## In

- The demo loop: process documents → the operating LLM authors CQs + ontology →
  **auto-accept** → the LLM extracts facts into the graph → **the LLM interviews the
  human for intent (skippable)** → answers with certainty bands + sources.
- **Any cloud LLM** as operator and as GrACE's configured vendor: Anthropic, OpenAI,
  DeepSeek, Groq, Together, xAI, any OpenAI-compatible `/v1` (local Ollama optional).
- Embeddings **optional** (`GRACE_EMBED_PROVIDER=auto`): on with an OpenAI-compatible
  embeddings key, off otherwise (keyword + graph retrieval, exact-name resolution).
- Postgres 17 + ArcadeDB (Docker) + Alembic; databases `grace_demo`.
- Document formats via Docling (PDF, DOCX, XLSX, PPTX, HTML, TXT, MD, CSV, images);
  discovery / extraction / retrieval / regeneration depth; MCP server; `/metrics`.
- Email: `.eml` folder (shipped sample) + Gmail / IMAP / Exchange (read-only, opt-in),
  triage tiers 1–4, extraction bridge, thread reconstruction.
- Voice/tone profiles + Voice Card export; photo vision (`generate_vision`) — opt-in.
- Golden dataset JSON over the sample corpus as demo questions (DeepEval not required).
- `scripts/smoke-demo.sh` (plumbing) and `scripts/demo-fastpath.sh` (whole loop with
  shipped samples, no LLM call) as the go/no-go gates.

## Out

- **Any web UI** (the student's LLM is the interface); Guided Review / human ontology
  ratification; graph viewer.
- Grafana / Prometheus dashboards and alerting; the internal analytics harnesses
  (signals, correlation, gap remediation, ingestion golden gates), agent daemon,
  calibration, reconciliation, change directives, decomposition, permissions /
  sensitivity gate, federation, remote support (the code may exist under `src/`; it is
  not part of the demo path).
- Customer documents, GOLD dumps, real secrets, the internal chunk-lifecycle build
  factory and its D-series archive.

## Human-in-the-loop

Chat interrogation + intent elicitation **in the operating LLM's conversation**. The model
authors the ontology; `grace-auto-accept` activates it. The human contributes the *why*
and may skip.
