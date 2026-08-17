---
name: grace-auto-accept
description: >
  STEP 4 of the GrACE-Demo produce track. Auto-accepts the LLM-authored ontology
  proposal — makes it the ACTIVE ontology version and syncs the DDL into ArcadeDB —
  WITHOUT a human review/ratify gate, and merges the intent meta-layer types so
  grace-intent-elicitation can write the human's why. Use right after
  grace-ontology-proposal + map_coverage. No LLM call.
---

# grace-auto-accept

## Why this exists
Hand-reviewing ontology types is meaningless to a non-technical human. Once you
authored the proposal and `map_coverage.py` confirms coverage, the schema still has to
become **active + synced** or graph extraction has nothing to write against — so we
do that programmatically and drop only the *human* click-through. GrACE's review /
`POST /api/ontology/ratify` code is untouched.

## What it does (two standalone HTTP calls — no review session needed)
1. `POST /api/ontology/ratify` — converts the SeedSchema into GrACE's ratified
   `schema_json` (`{entity_types:{…}, relationships:{…}}`) + per-domain
   `schema_modules`, ratifies it as a new **active** `OntologyVersion` (Postgres).
   By default the **intent meta-layer** (`Decision_Principle`, `Decision_Rationale`,
   `Counterfactual`, `Mandatory_Provision` + `explains` / `justifies` /
   `applies_principle` / `rejected_alternative_to` / `traded_for` / `depends_on` /
   `compels` / `specializes`) is merged in as its own module `intent`.
2. `POST /api/graph/sync-schema` — generates DDL from the active version and executes
   it on ArcadeDB (CREATE VERTEX/EDGE TYPE + indexes). Idempotent.

## Inputs
- The coverage-enriched `workspace/seed_schema.json` from **grace-ontology-proposal**.

## Do this
```bash
cd "$GRACE_ROOT"
# preview the payload without writing anything:
.venv/bin/python grace-claude-skills/scripts/auto_accept.py --in workspace/seed_schema.json --dry-run
# accept + sync to ArcadeDB:
.venv/bin/python grace-claude-skills/scripts/auto_accept.py --in workspace/seed_schema.json
```
Output reports the new active version number, type/relationship counts, and the DDL
sync result (statements executed, any errors), then verifies `GET /api/ontology/active`.

Flags: `--no-sync` (ratify only), `--no-intent-layer` (skip the intent meta-layer),
`--source manual|discovery|adaptive_evolution`, `--reviewer "<who/what>"`,
`--api-base http://127.0.0.1:8000`, `--admin-key` (only if `GRACE_ADMIN_KEY` is set).

## Prereqs
- API running (`uvicorn src.api.main:app --port 8000`); **ArcadeDB up** for the sync
  step; `GRACE_PERMISSION_ENFORCEMENT_ENABLED=0` (the `.env.example` default).

## After this
- **Step 6 (grace-graph-extraction):** the active+synced schema is the typing
  vocabulary extraction writes against.
- **Optional Step 5 (grace-property-detailing):** fill full properties, then run
  `auto_accept.py` again on the detailed schema (a new version).

## Re-running / versions
Each run ratifies a NEW active version (v1, v2, …) with a diff from the predecessor;
`sync-schema` is idempotent. Safe to re-run after edits.

## Safety
- No LLM — pure HTTP. Mutating: writes the active ontology version (Postgres) + ArcadeDB
  DDL, in the databases named by `.env` (`grace_demo`).
