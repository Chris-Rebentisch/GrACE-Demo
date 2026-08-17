---
name: grace-corpus-export
description: >
  STEP 1 of the GrACE-Demo produce track. Export the processed documents from
  Postgres into per-domain markdown bundles that you (the operating LLM — Claude,
  ChatGPT, Gemini, Cursor, any agent) read before authoring competency questions
  and the ontology. Balanced all-document coverage. No LLM call, no embeddings.
---

# grace-corpus-export

## Why this exists
GrACE stores every processed document's text in Postgres (`processed_documents`).
This step pulls that text out as readable markdown so **you** can be the reasoning
engine for the next steps. It touches Postgres only.

## Preconditions
- The API stack is installed (`INSTALL.md`) and the documents were processed:
  ```bash
  cd "$GRACE_ROOT"
  .venv/bin/python -m src.discovery.batch_runner --source-dir data/demo-corpus/documents
  # or --source-dir <the human's folder of .pdf/.docx/.txt/.md/...>
  ```
  (Docling parse/OCR on CPU — no LLM.) Files land as `status=COMPLETE` rows.
- `GRACE_ROOT` = the checkout root (`export GRACE_ROOT="$PWD"` from the repo). Every
  helper script also auto-detects the checkout it lives in, so the export is only
  a convenience.

## Do this
```bash
cd "$GRACE_ROOT"
.venv/bin/python grace-claude-skills/scripts/export_corpus.py
# scoped:
.venv/bin/python grace-claude-skills/scripts/export_corpus.py --domain insurance --domain legal
# tighter budget if a domain is huge:
.venv/bin/python grace-claude-skills/scripts/export_corpus.py --max-chars 120000
```
Output lands in `workspace/corpus/` (gitignored):
- `<domain>.md` — one bundle per domain (header lists doc count + filenames).
- `manifest.json` — domains, doc/char counts, file lists.

## Coverage guarantee
The script calls GrACE's own `build_balanced_document_text`, so **every** document in
a domain gets an equal slice of the character budget (head/middle/tail sampled for
long docs). Short documents are never crowded out by a few long ones.

## Hand-off
Open and read `workspace/corpus/<domain>.md` (you have file access; there is nothing
to "attach"), then follow **grace-cq-authoring** (Step 2). You will reuse the same
bundles for **grace-ontology-proposal** (Step 3).

## Safety
- Reads Postgres only. Writes files under `workspace/`.
- Uses the database named in `.env` (`DATABASE_URL` → `grace_demo`).
