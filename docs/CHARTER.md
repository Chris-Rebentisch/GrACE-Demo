# GrACE-Demo charter (locked)

College public-cut of GrACE. Scoping recorded 2026-08-17.

## In

- Demo loop: ingest → AI ontology → auto-accept → extract → Chat (certainty bands, citations, intent elicitation) → retrieval inspector → Settings
- Cloud LLM default (Anthropic / OpenAI-compatible: ChatGPT, DeepSeek, Groq, Together, xAI)
- Cloud embeddings default (768-dim); Ollama optional for embeddings and/or local chat
- Postgres 17 + ArcadeDB + Docker + Alembic (databases named `grace_demo`)
- Document formats, Discovery/extraction/retrieval depth, MCP server
- `/metrics` + in-process OpenTelemetry (no Grafana)
- Live Gmail, IMAP, Exchange (readonly, opt-in) + `.eml` fallback + thin triage + threads
- Voice style profiles + Voice Card export (no PII redactor, no DPIA gate)
- Photo vision (`generate_vision` + `Image_Asset`), opt-in
- Golden dataset JSON as demo questions (DeepEval not in default install)

## Out

- Guided Review / human ontology ratification; Cytoscape graph viewer in nav
- Grafana, dashboards, correlation engine, alerting; Signals A–F / agent daemon / calibration
- Reconciliation, Change Directives, Decomposition, Permissions/Sensitivity, Federation, remote support
- Four-tier mail plant, retriage scheduler, corroboration scorer
- Bench4KE export; DeepEval as required runtime
- GOLD dumps, customer documents, real secrets, chunk-lifecycle factory, full D-series archive

## Human-in-the-loop

Chat interrogation + intent elicitation. The model authors the ontology; `grace-auto-accept` activates it (CLLM 2026-06-10).
