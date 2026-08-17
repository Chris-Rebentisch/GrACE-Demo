---
name: grace-property-detailing
description: >
  OPTIONAL STEP 5 of the GrACE-Demo produce track. After the skeleton ontology is
  active, you (the operating LLM — any vendor) fill in the full property set for
  each type and relationship, then re-run map_coverage + auto_accept so the
  detailed schema becomes a new active version. Skip it for a first demo run.
---

# grace-property-detailing

## Role
You are the property detailer. The skeleton from **grace-ontology-proposal** has
types + relationships with only 2–5 obvious properties each. Here you flesh out the
**full** property set the documents and CQs justify, in one reasoning pass.

## Inputs
- The skeleton proposal on disk: `workspace/seed_schema.json`.
- The corpus bundle(s) from **grace-corpus-export** (evidence for property values).

## Step A — prepare the subset (no LLM)
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/export_proposal_for_detailing.py \
  --in workspace/seed_schema.json
```
Writes `workspace/to_detail.json` (the skeleton, slimmed to what you need to fill).
(`--session-id <ID> --only-accepted` exists only for the optional human-review
variant; the default GrACE-Demo path has no review session — skip those flags.)

## Step B — you detail properties
Read `to_detail.json` + the corpus. For **every** entity type and relationship, author
the complete property set the documents and CQs justify. Per property:
- `name` (snake_case), `data_type` (string | datetime | float | boolean | integer | reference),
  `description`, `required` (true only when every instance must have it), `answerable_cqs`.
- Add edge_properties to relationships whose `richness_tier` is `attributed`/`reified`.
- Keep names PascalCase_With_Underscores (types) / snake_case (properties).
- Ground each property in the evidence; don't invent fields the corpus never implies.

Emit the **same SeedSchema shape** as `grace-ontology-proposal/templates/seed_schema.example.json`,
now with rich `properties[]`. Write it to `workspace/seed_schema.detailed.json`.

## Step C — re-map coverage + auto-accept (no LLM, no human gate)
Refresh coverage on the detailed schema, then auto-accept it as a NEW active ontology
version (human ratification is bypassed — see grace-auto-accept):
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/map_coverage.py \
  --in workspace/seed_schema.detailed.json --domain <domain>
.venv/bin/python grace-claude-skills/scripts/auto_accept.py \
  --in workspace/seed_schema.detailed.json
```
`auto_accept.py` ratifies the detailed schema (a new active version with an OM4OV diff
from the skeleton) **and re-syncs the DDL to ArcadeDB** — the prerequisite for graph
extraction (grace-graph-extraction).

## Note on the native engine
GrACE has a built, tested batched detailer (`detail_types`, `run_stage2_batch`,
batch_size 4) in `src/discovery/schema_extractor.py`, but there is **no write-back
endpoint** to patch properties onto a ratified version — you re-review/re-ratify a new
version. This skill takes that same re-ratify path, with you doing the detailing.

## Safety
- Your own inference — no local model.
- Keep `GRACE_PERMISSION_ENFORCEMENT_ENABLED=0` (the `.env.example` default).
