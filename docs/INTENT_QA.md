# Intent Q&A — protocol for the operating LLM

This is **your** conversation with the human after extraction. You are the interface.
There is no web app. Canonical copy: [LLM_OPERATOR.md](LLM_OPERATOR.md) ("After
extraction"). Full method + write tool: `grace-claude-skills/grace-intent-elicitation/SKILL.md`.

## When

Immediately after graph extraction has written facts. Do not wait for "now do intent."

## Opening line

> The documents are in the graph. I know *what* they say. I need the *why* — the decision,
> the tradeoff, the path you rejected. I'll show you a fact and ask why it is built that
> way. I will not guess. **You can skip** and I'll continue from the documents only.

## If they skip

Acknowledge once. Stop interviewing. Answer later questions from ingested facts only.

## If they participate

1. **Fact first**, verbatim and in plain language (`intent_query.py --facts '*'` →
   `--fact <gid>`); then an open "why is it built that way?". Never suggest the answer.
2. **One surgical follow-up** — the single rung they left implicit (often the rejected
   alternative or the load-bearing constraint).
3. **Bands only**: `high` / `medium` / `low` / `insufficient_evidence`. "I don't know" is
   a valid, valuable answer — record it, do not fill it.
4. **Restate the structure** — principle (the reusable rule), rationale (this decision),
   rejected alternative, band — they confirm or edit. Then the next fact, or stop.
5. **Write** the confirmed bundle: `grace-claude-skills/scripts/intent_apply.py --bundle
   <confirmed.json>` (shape: `data/demo-corpus/samples/intent_bundle_example.json`).

## Sample fact (demo corpus)

Overnight courier claims leave the standard path only when weather ground-stop *or*
customs hold, signature-required delivery, *and* a supervisor rationale are all true.
Ask why. Do not guess.

## Later

`intent_query.py --ask "<a new decision>"` retrieves the captured principles, precedent
and rejected paths so you can answer a question the documents never anticipated — in the
human's own reasoning.
