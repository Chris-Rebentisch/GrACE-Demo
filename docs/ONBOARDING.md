# GrACE-Demo — first run (documents → graph → why → answers)

**Agents:** this is your step list after Session 0 (student's key + vendor set, stack up,
`scripts/smoke-demo.sh` green). Read [LLM_OPERATOR.md](LLM_OPERATOR.md) first. Each step
below points at a skill in `grace-claude-skills/` whose `SKILL.md` has the exact
commands and file shapes.

## Goal

Load the sample corpus (or the human's files), author and auto-accept an ontology,
extract facts, **interview the human for intent (or they skip)**, then answer a question
from the graph with a certainty band and sources.

## Sample corpus

`data/demo-corpus/` — a fictional insurance mini-world (Northwind Specialty Cargo):

| Path | What |
|---|---|
| `documents/northwind-overnight-exception-memo.txt` | the exception process for overnight courier claims |
| `documents/northwind-endorsement-c14-settlement-schedule.txt` | the settlement schedule the memo refers to |
| `documents/northwind-adjuster-desk-procedure-oc3.txt` | roles and the standard-path steps |
| `email/sample-exception-followup.eml` | a follow-up email (optional email path) |
| `samples/` | reference outputs: `cqs.json`, `seed_schema.json`, `extraction_*.json`, `intent_bundle_example.json` |

No real people, policies, or claims.

## Fast path first (no LLM call)

```bash
bash scripts/demo-fastpath.sh
```
Runs steps 0–6 below with the shipped samples and asks the graph a question. If it
passes, the stack is fine and any later problem is in the authoring, not the plumbing.
(It ratifies a sample ontology; your own auto-accept in step 4 simply becomes the next
active version.)

## The loop (you do the reasoning)

```bash
export GRACE_ROOT="$PWD"; P=.venv/bin/python; S=grace-claude-skills/scripts
```

| # | Do | Skill / command |
|---|---|---|
| 0 | Process documents into Postgres (Docling; no LLM) | `$P -m src.discovery.batch_runner --source-dir data/demo-corpus/documents` |
| 1 | Export the text and **read it** | `$P $S/export_corpus.py` → `workspace/corpus/insurance.md` (**grace-corpus-export**) |
| 2 | Author competency questions → `workspace/cqs.json`, import | `$P $S/import_cqs.py --in workspace/cqs.json --domain insurance` (**grace-cq-authoring**) |
| 3 | Author the ontology → `workspace/seed_schema.json`, map coverage | `$P $S/map_coverage.py --in workspace/seed_schema.json --domain insurance` (**grace-ontology-proposal**) |
| 4 | **Auto-accept** (ratify + ArcadeDB DDL + intent meta-layer) | `$P $S/auto_accept.py --in workspace/seed_schema.json` (**grace-auto-accept**) |
| 5 | *(optional)* detail properties, re-accept | **grace-property-detailing** |
| 6 | Extract each document → `workspace/extraction_<doc>.json`, import | `$P $S/import_extraction.py --in workspace/extraction_<doc>.json --doc-file <doc>.txt --module insurance` (**grace-graph-extraction**) |
| 7 | **Speak first:** offer intent Q&A; interview or accept the skip | `$P $S/intent_query.py --facts '*'` → `--fact <gid>` → `intent_apply.py --bundle …` (**grace-intent-elicitation**) |
| ask | Answer from the graph | `POST /api/retrieval/query` / `POST /api/regeneration/query` |

Prove the graph can answer, e.g.:

**What is the exception process for overnight courier claims?**

The answer should be grounded in the memo (three conditions AND a supervisor rationale;
no goodwill exception), carry a certainty band, and name the source document.

```bash
curl -s -X POST http://localhost:8000/api/retrieval/query -H 'Content-Type: application/json' \
  -H 'X-Graph-Scope: all' \
  -d '{"query_text":"What is the exception process for overnight courier claims?","top_k":8}'
```

## Email (optional)

After the file corpus works: `.eml` files (`data/demo-corpus/email/`), or Gmail / IMAP /
Exchange (read-only, opt-in). Commands are in LLM_OPERATOR.md ("Email"). Skip live mail
if OAuth is not ready.

## The human's own documents

Point step 0 at their folder (`--source-dir /path/to/their/docs`; PDF, DOCX, XLSX, PPTX,
TXT, MD, HTML, CSV, images). Then repeat steps 1–7 — new domain, new CQs, new ontology
(auto-accept makes it the next active version), new extractions.

## You are not done until

- [ ] `GET /api/health` and `GET /api/graph/health` are ok
- [ ] `GET /api/ontology/active` returns a schema (after auto-accept)
- [ ] Extraction has run for every document; `GET /api/graph/entities` shows them
- [ ] You offered intent Q&A (and either wrote a confirmed bundle, or they skipped)
- [ ] You answered the courier-exception question from the graph with band + source
- [ ] No keys or private documents were committed
