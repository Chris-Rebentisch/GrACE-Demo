# GrACE-Demo — LLM / agent operator manual

**Read this if you are Claude, ChatGPT, Cursor, or any other agent asked to install, onboard, extract, or demo GrACE-Demo.**

You are the **facilitator and pipeline operator**, not the human. The human is the only source of *intent*. You author the ontology and extract facts; you **auto-accept** the schema (no Guided Review click-through). You never invent why a person decided something — you ask, then write what they said.

## North star

Documents + optional email → AI-authored ontology (auto-accepted) → provenanced graph → Chat answers with certainty bands and citations → optional intent layer (the *why*).

## Do this in order

1. Follow **[INSTALL.md](../INSTALL.md)** on the machine. Stop if `bash scripts/smoke-demo.sh` is not exit 0.
2. Follow **[ONBOARDING.md](ONBOARDING.md)** for the first corpus loop.
3. Use the skills under `grace-claude-skills/` (name is historical; they work for any agent that can run bash + HTTP). Set `GRACE_ROOT` to this checkout.

## Produce track (skills)

| Skill | Step | What you do |
|---|---|---|
| `grace-corpus-export` | 1 | Dump document text for you to read |
| `grace-cq-authoring` | 2 | Author competency questions; import them |
| `grace-ontology-proposal` | 3 | Author the schema skeleton + coverage |
| `grace-auto-accept` | 4 | **Required.** Ratify + ArcadeDB DDL sync. No human gate. |
| `grace-property-detailing` | 5 | Optional property fill; auto-accept again |
| `grace-graph-extraction` | 6 | Extract entities/relationships per document |
| `grace-intent-elicitation` | 7 | Interview the human for *why*; write intent vertices |
| `grace-retrieval-probe` | A1 | Prove the graph can answer |
| `grace-ingestion-harness` | C1 | Optional email path |

**Skip for this demo:** Guided Review UI, `grace-review-protocol` as a schema gate, signal/correlation/remediation probes (Adaptive Evolution is out), Grafana.

`grace-auto-accept` is load-bearing. Decision (2026-06-10, carried into this demo): humans are not better ontology designers than the model. Something still has to make the schema *active* (`POST /api/ontology/ratify` + `POST /api/graph/sync-schema`). That is the script, not a person clicking types.

## Hard rules

- Never commit `.env`, API keys, OAuth secrets, or customer documents.
- Use database **`grace_demo`** (Postgres + ArcadeDB). Never write to a GOLD `grace` corpus.
- Default embeddings are **cloud, 768-dim**. Do not pull a local embed model unless the operator set `GRACE_EMBED_PROVIDER=ollama`.
- Do not start `docker-compose.observability.yml`.
- Do not tell the user to open `/graph` or `/review`.
- Chat is the human loop. Intent elicitation: you ask; they decide; you record.
- Live Gmail/IMAP/Exchange are opt-in and **read-only**. Prefer `data/demo-corpus/` for a first demo.
- If a command fails, stop and show the error. Do not pretend the graph is populated.

## Smoke commands (copy/paste)

```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/graph/health
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/metrics
curl -s http://localhost:8000/api/ontology/active
```

`/api/ontology/active` may 404 until auto-accept has run — that is expected on a fresh database.

## Provider switching

Edit `config/discovery.yaml` `llm.provider` / `llm.model` / `llm.base_url`, or use **Settings**. `LLM_API_KEY` in `.env` is the cloud key. OpenAI-compatible vendors share `provider: openai` and a different `base_url`.
