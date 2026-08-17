---
name: grace-graph-extraction
description: >
  STEP 6 of the GrACE-Demo produce track. You (the operating LLM — any vendor)
  read one document + the active ontology and extract entities + relationships
  as JSON; import_extraction.py writes them to ArcadeDB through the documented
  bulk endpoints with registry + exact/alias entity resolution (ANN resolution
  too when an embeddings vendor is configured). Use after grace-auto-accept.
---

# grace-graph-extraction

## Role
You are the graph extractor. For one document at a time, you read the text + the
active ontology and emit the entities and relationships present, typed against the
ratified schema.

## Hard prerequisite
An ontology must be **active AND synced to ArcadeDB** — produced by
**grace-auto-accept** (Step 4). ArcadeDB rejects any `entity_type` /
`relationship_type` the schema does not define. Fetch the live schema and use ONLY
its type names, relationship names, and property names:
```
GET http://127.0.0.1:8000/api/ontology/active
```

## Inputs
- One document's text (from `workspace/corpus/<domain>.md`, or the
  `processed_documents.extracted_text` row).
- The active ontology (`GET /api/ontology/active`) — your typing vocabulary.
- Worked examples for the sample corpus: `data/demo-corpus/samples/extraction_*.json`.

## Method
1. Identify the entities in the document. Type each against the ontology
   (`entity_type` = a defined vertex type). Put the human-readable identifier in
   `name` and in `properties.name`; fill the other ontology properties you can ground.
2. Identify relationships. Reference endpoints **by name + type** (`source_name`,
   `source_type`, `target_name`, `target_type`) — the helper resolves grace_ids.
3. **Use the same `name` for the same real-world thing across documents** (e.g.
   always `Endorsement C-14`, not `C-14` in one file and `Endorsement C14` in the
   next). Exact-name repeats merge into ONE vertex and missing properties are filled
   in; different spellings become separate vertices unless an embeddings vendor is
   configured for similarity resolution. When unsure, look at what already exists:
   `GET /api/graph/entities?limit=100`.
4. Set a `confidence` per item. Add `sensitivity_tags` (bar-form, e.g. `"|privileged|"`)
   when the source warrants it; default `""`.
5. Do NOT invent entities/relations the document doesn't support. If the document
   says something is *not* the case, use the ontology's explicit negative
   (e.g. `rejects_evidence`, `acceptable=false`) rather than omitting the fact.

## Output format
Emit one JSON object per document matching `templates/extraction.example.json`
(`entities[]` + `relationships[]`). Write it to `workspace/extraction_<docname>.json`.

## Write to the graph (no LLM)
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/import_extraction.py \
  --in workspace/extraction_<docname>.json --doc-file <docname.ext> --module <domain> --dry-run
.venv/bin/python grace-claude-skills/scripts/import_extraction.py \
  --in workspace/extraction_<docname>.json --doc-file <docname.ext> --module <domain>
```
`--doc-file` is the processed document's file name (resolved to its UUID); `--doc-id
<UUID>` also works. Phase A sends entities through `POST /api/graph/entities/bulk`
(new vertices created; exact-name repeats matched case-insensitively on name|alias and
fill-only merged); Phase B inserts the relationships against the resolved grace_ids;
then the retrieval indexes are rebuilt so `POST /api/retrieval/query` sees the new
facts immediately.

Repeat for every document (loop the helper over per-document JSON files). Verify:
```bash
curl -s "http://127.0.0.1:8000/api/graph/entities?limit=50" -H 'X-Graph-Scope: all'
curl -s -X POST http://127.0.0.1:8000/api/retrieval/query -H 'Content-Type: application/json' \
  -H 'X-Graph-Scope: all' -d '{"query_text":"<a question the documents answer>","top_k":8}'
```

## Entity resolution (what the helper does)
- Layer 1 — `workspace/entity_registry.json`: (type, name) → grace_id you already minted.
- Layer 2 — GrACE's canonical lookup at insert (case-insensitive name OR alias).
- Layer 3 — ANN over `_embedding` (`vectorNeighbors`) with per-type thresholds —
  **only when an embeddings vendor is configured** (`GRACE_EMBED_PROVIDER` resolves
  to a vendor). With a chat-only key this layer is skipped and the helper says so.
Flags: `--no-resolve`, `--er-threshold`, `--review-floor`, `--registry`, `--dry-run`.

## After extraction — start intent Q&A
This is the moment to speak to the human (see `docs/LLM_OPERATOR.md`, "After
extraction"): you know *what* the documents say; ask for the *why*
(**grace-intent-elicitation**). They may skip.

## Safety
- Your own inference — no local model.
- Writes the ArcadeDB database named in `.env` (`ARCADE_DATABASE=grace_demo`).
