# grace-claude-skills — the produce track for any operating LLM

Step-by-step "skills" (one `SKILL.md` per folder) plus the deterministic helper
scripts they call. The folder name is historical (they were first written for Claude
Desktop); **any agent that can read files, run bash, and make HTTP calls can follow
them** — Claude, ChatGPT / Codex, Gemini, Cursor, Copilot, …

**Read first:** [`docs/LLM_OPERATOR.md`](../docs/LLM_OPERATOR.md) (you are the demo
interface; Session 0 = the student's cloud key + endpoints), then
[`INSTALL.md`](../INSTALL.md) and [`docs/ONBOARDING.md`](../docs/ONBOARDING.md).

Set `GRACE_ROOT` to the checkout root (`export GRACE_ROOT="$PWD"`); every script also
auto-detects the checkout it lives in. All heavy reasoning (CQs, ontology, extraction,
intent Q&A) is **your own inference** — no local model is ever loaded. Embeddings are
optional (see below).

## The produce track (do these in order)

| Step | Skill | What happens | Who reasons |
|---|---|---|---|
| 0 | *(no skill)* | Process documents: `python -m src.discovery.batch_runner --source-dir data/demo-corpus/documents` | none (Docling) |
| 1 | **grace-corpus-export** | Dump processed document text to `workspace/corpus/<domain>.md` | none (Postgres) |
| 2 | **grace-cq-authoring** | You author competency questions → `workspace/cqs.json` → `import_cqs.py` | **you** |
| 3 | **grace-ontology-proposal** | You author the schema → `workspace/seed_schema.json` → `map_coverage.py` | **you** |
| 4 | **grace-auto-accept** | `auto_accept.py`: ratify as active ontology + ArcadeDB DDL (+ intent meta-layer). No human schema gate. | none (HTTP) |
| 5 | **grace-property-detailing** *(optional)* | You fill full properties → re-run coverage + auto-accept | **you** |
| 6 | **grace-graph-extraction** | You extract entities/relationships per document → `import_extraction.py` | **you** |
| 7 | **grace-intent-elicitation** | **You interview the human for the *why*** (they may skip) → `intent_apply.py` | **you** (facilitator) |
| ask | *(no skill)* | `POST /api/retrieval/query` (facts + evidence) and/or `POST /api/regeneration/query` (prose via the student's cloud vendor) | GrACE + vendor |

Consume-side probes (optional, for checking your own work): **grace-retrieval-probe**
(does the graph answer?), **grace-regeneration-probe** (does it answer in prose,
faithfully?), **grace-review-protocol** (facilitate a fact-review with the human),
**grace-testing-protocol** (how the test suite is isolated).

**LLM-free fast path** — proves the stack before you author anything:
`bash scripts/demo-fastpath.sh` runs steps 0–6 with the shipped samples in
`data/demo-corpus/samples/` and asks the graph a question.

## Helper scripts (`scripts/`)

| Script | Step | Purpose |
|---|---|---|
| `export_corpus.py` | 1 | balanced per-domain corpus export |
| `import_cqs.py` | 2 | validate + persist CQs (`--dry-run` first) |
| `export_seed_reference.py` | 3 | render FIBO / LKIF / Schema.org / PROV-O for grounding (optional) |
| `map_coverage.py` | 3 | which CQ each type/relationship answers (embedding or lexical mode) |
| `auto_accept.py` | 4 | ratify + `POST /api/graph/sync-schema` (+ intent meta-layer) |
| `export_proposal_for_detailing.py` | 5 | slim the proposal for property detailing |
| `import_extraction.py` | 6 | two-phase bulk insert with registry / exact-alias / (optional) ANN resolution; `--doc-file <name>` |
| `intent_query.py` | 7 | `--facts '*'`, `--fact <gid>`, `--similar`, `--ask` |
| `intent_apply.py` | 7 | write a confirmed decision bundle to the graph |
| `import_proposal.py` | opt | open a browsable review record (not required) |
| `retrieval_probe.py`, `retrieval_router.py`, `run_battery.py`, `retrieval_golden_gate.py`, `cypher_exec.py` | probe | consume-side checks |
| `regen_compose.py`, `regen_decompress.py`, `regeneration_golden_gate.py`, `faithfulness_score.py` | probe | regeneration checks |
| `intent_golden_gate.py` | probe | intent-layer invariants (written for a legal validation corpus) |
| `safe_pytest.sh` | infra | pytest wrapper enforcing test-DB isolation |
| `_common.py` | infra | repo-root / `.env` / DB-session bootstrap |

## Embeddings are optional

`GRACE_EMBED_PROVIDER=auto` (the `.env.example` default) uses OpenAI-compatible
embeddings only when a `GRACE_EMBED_API_KEY` is set or the chat vendor is real
OpenAI; with an Anthropic / DeepSeek / Groq key it resolves to **none**. Everything
still works: `map_coverage.py` runs in lexical mode, `import_extraction.py` skips ANN
resolution (registry + exact/alias dedup remain), retrieval uses BM25 + graph, and
intent principles are stored without vectors. Set `GRACE_EMBED_API_KEY` (or
`GRACE_EMBED_PROVIDER=ollama` with a local `nomic-embed-text`) to turn vectors on.

## Decisions baked in

1. **CQ import status → ACCEPTED**, `source=HUMAN_AUTHORED` (operator-curated),
   `metadata_extra.authoring_method="combined-a3"`.
2. **No CQ merge on this path.** You author a deduped set; coverage is computed at
   propose time by `map_coverage.py`.
3. **Human ontology ratification → bypassed.** `auto_accept.py` ratifies + syncs
   programmatically. GrACE's review/ratify code stays; nobody has to click through
   schema types. Humans contribute the *why* (Step 7) instead.
4. **Seed grounding is optional** (`export_seed_reference.py`); use it when
   standards alignment matters.
5. **Intent meta-layer is merged at auto-accept** so Step 7 has types to write to.

## Known limitations

- **Auto-accept = a new active version each run** (v1, v2, …). Property detailing
  re-accepts a new version.
- **Entity resolution without embeddings is exact/alias only.** Use the same `name`
  for the same thing across documents (see grace-graph-extraction).
- **Accept-before-extract.** Graph insertion requires the ontology active AND synced
  to ArcadeDB (Step 4 does both); undefined types fail at the DB.

## Non-negotiables

- Databases are the ones in `.env` (`grace_demo`). Tests use an isolated `_test`
  sibling (`safe_pytest.sh`, `tests/conftest.py`).
- Keep `GRACE_PERMISSION_ENFORCEMENT_ENABLED=0` during onboarding.
- Use the repo venv (`.venv/bin/python`); the system python may be too old.
- Never print, log, or commit `LLM_API_KEY`.
