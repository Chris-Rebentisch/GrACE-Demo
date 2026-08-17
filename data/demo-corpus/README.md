# Sample corpus (fictional)

Teaching files only. No real policyholders, mailboxes, employees, insurers or claims.
"Northwind Specialty Cargo" and every person, address and document here are invented.

| Path | What it is |
|---|---|
| `documents/northwind-overnight-exception-memo.txt` | Claims exception process for overnight courier claims |
| `documents/northwind-endorsement-c14-settlement-schedule.txt` | The settlement schedule (Endorsement C-14) the memo refers to |
| `documents/northwind-adjuster-desk-procedure-oc3.txt` | Roles + standard-path steps + evidence rules |
| `email/sample-exception-followup.eml` | Follow-up email referring to the memo (optional email path) |
| `samples/cqs.json` | Reference competency questions (what the LLM authors in step 2) |
| `samples/seed_schema.json` | Reference ontology proposal (step 3) |
| `samples/extraction_*.json` | Reference per-document extractions (step 6) |
| `samples/intent_bundle_example.json` | Shape of a confirmed intent bundle (step 7); fact grace_ids are placeholders |

`bash scripts/demo-fastpath.sh` runs the whole loop with these samples (no LLM call).
Process the documents with `python -m src.discovery.batch_runner --source-dir data/demo-corpus/documents`
(the README and `samples/` are deliberately outside that folder).

Headline question after extraction: **What is the exception process for overnight courier claims?**
