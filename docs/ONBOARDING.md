# GrACE-Demo — first run (document → graph → ask)

Do this **after** [INSTALL.md](../INSTALL.md) and a green `scripts/smoke-demo.sh`.

Agents: also read [LLM_OPERATOR.md](LLM_OPERATOR.md).

## Goal

Load the synthetic sample corpus, auto-accept an ontology, extract, ask one question in Chat that cites a source.

## Sample corpus

Files live in `data/demo-corpus/` (fictional insurance memo + a sample `.eml`). They are **not** customer data.

## Path A — LLM-operated (recommended)

From the repo root, with API + frontend running:

```bash
export GRACE_ROOT="$PWD"

# Fast path (no LLM): ratify the shipped sample ontology + ArcadeDB DDL
.venv/bin/python "$GRACE_ROOT/grace-claude-skills/scripts/auto_accept.py" \
  --in "$GRACE_ROOT/data/demo-corpus/seed_schema.json"

# Full path: export corpus, author CQs, propose schema (see grace-claude-skills/),
# then auto-accept your proposal instead of the sample seed.
```

Then open http://localhost:3000/chat and ask: **What is the exception process for overnight courier claims?**

You should see a certainty band and a source link into the sample memo.

## Path B — UI-operated

1. **Sources** — include `data/demo-corpus/`.
2. Run document processing from Onboarding / Sources (Docling for binaries; `.txt` is read directly).
3. Have your LLM (ChatGPT/Claude/Cursor with [LLM_OPERATOR.md](LLM_OPERATOR.md)) propose + auto-accept the ontology. Do **not** use Guided Review.
4. Extract.
5. **Chat** — same question as Path A.
6. **Inspector** — confirm retrieval used the sample document.

## Email (optional, after Path A works)

Connect Gmail, IMAP, or Exchange in **Ingestion** (readonly). Or drop extra `.eml` files next to the sample. Thin triage + thread reconstruction apply. Skip live mail if OAuth is not ready — the file corpus is enough to demo.

## Intent (optional)

After facts exist, run `grace-intent-elicitation`: interview the human for *why*, write it to the graph, then ask Chat a “why did we decide X?” question.

## You are not done until

- [ ] `GET /api/health` is ok
- [ ] `GET /api/graph/health` is ok
- [ ] `GET /api/ontology/active` returns a schema (after auto-accept)
- [ ] Chat answers the courier-exception question with a citation
- [ ] No GOLD/customer files were used
