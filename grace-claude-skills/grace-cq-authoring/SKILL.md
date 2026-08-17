---
name: grace-cq-authoring
description: >
  STEP 2 of the GrACE-Demo produce track. You (the operating LLM — any vendor)
  read the exported corpus bundle and author Competency Questions (CQs): the
  questions the ontology must be able to answer. Produces workspace/cqs.json,
  which import_cqs.py validates and persists. No local model, no embeddings.
---

# grace-cq-authoring

## Role
You are the CQ generator. You read the corpus, think across four perspectives, and
emit a JSON list of CQs. A helper script then validates and persists them.

## Inputs
- Corpus bundle(s) from **grace-corpus-export** (`workspace/corpus/<domain>.md`).
- Method reference: `references/cq-authoring-method.md` (the "combined / A3"
  multi-perspective method GrACE itself uses).
- Worked example for the sample corpus: `data/demo-corpus/samples/cqs.json`.

## What a CQ is (and is NOT)
- A CQ is a question the **ontology schema** must be able to answer. It shapes types,
  relationships, and properties. It is **not** a graph node/edge and not a fact lookup.
- Good CQs force structure: relationship CQs imply edges; metaproperty CQs imply
  properties; validating CQs imply integrity constraints / required links.

## Method (summary — full detail in references/cq-authoring-method.md)
Author CQs in ONE combined pass per domain, covering four perspectives:
1. **Top-down** — the big entity classes and their obvious relationships.
2. **Bottom-up** — specifics visible in the documents (named fields, dates, amounts).
3. **Middle-out** — cross-document / cross-domain links (e.g. memo → endorsement).
4. **Negative evidence** — integrity checks: "does every X reference a Y?", "is there
   any goodwill exception?".

Aim for a **compact canonical set**: roughly **10–30 high-value CQs per domain**
(10 is plenty for the 3-document sample corpus). One well-phrased CQ beats five
rephrasings of the same need. Do not pad.

## Output format
Emit a JSON list matching `templates/cqs.example.json`. Per item:
- `canonical_text` (REQUIRED) — the question.
- `cq_type` — one of SCOPING | VALIDATING | FOUNDATIONAL | RELATIONSHIP | METAPROPERTY | UNCLASSIFIED.
- `domain` — the corpus domain (from the bundle header, e.g. `insurance`).
- `priority` — HIGH | MEDIUM | LOW | UNSET.
- `rationale` — one line on what schema element it forces (stored in metadata).
- `evidence_files` — filenames from the corpus header that ground the CQ (optional;
  resolved to `linked_document_ids` on import).
- `confidence` — your 0–1 confidence (optional).

Write it to `workspace/cqs.json`.

## Persist (no LLM)
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/import_cqs.py --in workspace/cqs.json --domain <domain> --dry-run   # validate
.venv/bin/python grace-claude-skills/scripts/import_cqs.py --in workspace/cqs.json --domain <domain>             # write
```
Each row is tagged `source=HUMAN_AUTHORED` (operator-curated) with
`metadata_extra.authoring_method="combined-a3"` for audit.

## Do NOT run the native CQ merge
The merge (`/api/discovery/merge-cqs`) exists to compress the redundant output of
weak local models. You author one combined, deduped, type-classified set, so there
is nothing to merge. Go straight to **grace-ontology-proposal**; coverage (which CQ
each type answers) is computed there by `map_coverage.py`.

## Safety
- The authoring is your own inference — no local model.
- `import_cqs.py` writes the database named in `.env` (`grace_demo`). Intended.
