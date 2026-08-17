---
name: grace-ontology-proposal
description: >
  STEP 3 of the GrACE-Demo produce track. You (the operating LLM — any vendor)
  read the corpus + the CQs and author the ontology proposal (entity types +
  relationships, skeleton-first) as workspace/seed_schema.json. map_coverage.py
  then records which CQ each type/relationship answers, and grace-auto-accept
  ratifies it. Optional seed grounding (FIBO / LKIF / Schema.org / PROV-O).
---

# grace-ontology-proposal

## Role
You are the schema extractor + merger. You produce a **skeleton-first** proposal:
types and relationships with light properties. Property detailing can happen later
(**grace-property-detailing**, optional).

## Inputs
- Corpus bundle(s) from **grace-corpus-export** (`workspace/corpus/<domain>.md`).
- The CQ set from **grace-cq-authoring** (`workspace/cqs.json`, or the DB table
  `competency_questions`, or `GET /api/discovery/cqs`).
- Optional **seed reference** — `workspace/seed_reference_<domain>.md` (see below).
- Contract reference: `references/data-contracts.md` (the exact SeedSchema shape).
- Worked example for the sample corpus: `data/demo-corpus/samples/seed_schema.json`.

## Seed grounding (optional — align to proven domain ontologies)
GrACE ships reference ontologies (FIBO, LKIF, Schema.org, PROV-O). Render the ones
relevant to your domain and read them while you author:
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/export_seed_reference.py --domain <domain>
# add --provision to parse any uncached seed RDF (rdflib, CPU, no LLM)
```
For each proposed type/relationship: if it matches a seed class, adopt the seed's
name/hierarchy and set `seed_source` (`fibo|lkif|schema_org|prov_o`),
`seed_type_name` (or `seed_rel_name`), `seed_alignment`, `provenance="seed_aligned"`.
If the documents need a type the seed lacks, keep it with `provenance="llm_authored"`,
`seed_source: null`. Skip seeding entirely when you only need an internal ontology
that fits the documents.

## Method
1. **Cluster the CQs into entity classes.** Each recurring subject → a candidate type
   (PascalCase_With_Underscores, e.g. `Claims_Process`, `Legal_Entity`).
2. **Derive relationships** from RELATIONSHIP/middle-out CQs. Set `richness_tier`:
   `simple` (bare link), `attributed` (edge carries properties), `reified` (the
   relationship is itself an entity with a lifecycle).
   - **Model transactional facts as first-class types.** If a fact has money + a
     date + two parties (a payment, a bid, a claim settlement), it is a type of its own
     with `amount`/`date`/`status` — not a property hanging off a static entity.
   - **Model negatives explicitly.** If the documents say something is *not*
     acceptable / *not* allowed, give the graph an unambiguous way to say so (a boolean
     property such as `acceptable`, and/or a distinct relationship such as
     `rejects_evidence` next to `accepts_evidence`). Downstream answers must not have
     to infer a negative from the absence of an edge.
3. **Skeleton properties only.** 2–5 obvious properties per type (IDs, names, key
   dates, the ones CQs directly demand). Every type gets a `name` property.
4. **Map each CQ to the type(s)/relationship(s) that answer it** in `answerable_cqs`.
   You read the corpus; you know the coverage — fill it in yourself. `map_coverage.py`
   keeps what you wrote and only tops it up.
5. **Ground in evidence.** Put corpus filenames in `evidence_documents` /
   `evidence_document_count`.
6. **Align to the seed** if you rendered one (above).

## Output format
Emit one JSON object matching `templates/seed_schema.example.json`:
- `entity_types[]` — each with `name`, `description`, `display_label`,
  `plain_description`, `domain`, `properties[]` (`name`, `data_type`, `description`,
  `required`, `answerable_cqs`), `confidence`, `answerable_cqs`, `provenance`
  (`"seed_aligned"` or `"llm_authored"`), `seed_source`, `seed_type_name`, `seed_alignment`.
- `relationships[]` — each with `name`, `source_type`, `target_type`, `richness_tier`,
  `richness_rationale`, `edge_properties[]`, `confidence`, `provenance`, `seed_source`,
  `seed_rel_name`, `answerable_cqs`.
- `coverage_matrix` (leave `[]`), `provenance_summary`, `quality_metrics` (leave `{}`),
  `gap_report` (may be `{}`), `extraction_run_id` (`"llm-authored"`),
  `industry_profile`, `created_at` (ISO).

Write it to `workspace/seed_schema.json`.

## Map CQ coverage (no LLM)
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/map_coverage.py --in workspace/seed_schema.json --domain <domain>
```
Fills `coverage_matrix` + `quality_metrics.cq_coverage_rate`. Two modes, chosen
automatically: embedding similarity when an embeddings vendor is configured, otherwise
**lexical** (token overlap on top of the `answerable_cqs` you authored — the normal
GrACE-Demo case with a chat-only key). The printout lists any **uncovered CQs**; if a
CQ has no answering type/relationship, add the missing element and re-run.

## Next → auto-accept (Step 4), NOT a human review screen
Hand the coverage-enriched `workspace/seed_schema.json` straight to **grace-auto-accept**:
```bash
.venv/bin/python grace-claude-skills/scripts/auto_accept.py --in workspace/seed_schema.json
```
That ratifies the proposal as the active ontology AND syncs the DDL to ArcadeDB.
Humans contribute *why* later (grace-intent-elicitation), not by clicking through
schema types.

## Safety
- Your own inference — no local model.
- Writes only files under `workspace/` until auto-accept.
