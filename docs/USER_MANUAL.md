# GrACE-Demo — for the human in the room

You do not need to install anything by hand and there is no web app to open. **Your own
cloud LLM is the interface** — Claude, ChatGPT / Codex, Cursor, Gemini, Copilot, any agent
that can read files and run commands.

## Setup, in one sentence

Open this folder in that tool (or paste [LLM_SYSTEM_PROMPT.md](LLM_SYSTEM_PROMPT.md) into
its custom instructions), tell it which cloud vendor you use, and give it an API key
**once**. It puts the key in `.env` and will not show it back. If it asks you to install
Docker / PostgreSQL / uv, [INSTALL.md](../INSTALL.md) has the exact commands for macOS,
Windows and Linux.

## What will happen

1. It starts GrACE and proves the plumbing works (`scripts/smoke-demo.sh`,
   `scripts/demo-fastpath.sh`).
2. It reads the sample documents (`data/demo-corpus/`) — or your own folder.
3. It writes the questions the knowledge should answer and proposes an ontology; GrACE
   **auto-accepts** it. You do not click through schema types.
4. It extracts the facts into the graph.
5. It tells you it needs the *why* and asks you about the important facts, one at a
   time. **You may skip.** If you skip, it continues from the documents only.
6. You ask it questions in that same conversation. Answers carry a certainty band
   (high / medium / low / insufficient evidence) and point at the source document.

## When it asks "why"

Answer honestly, or say skip. The protocol it follows is [INTENT_QA.md](INTENT_QA.md):
it shows you the fact first and must not suggest the answer; it asks one follow-up; it
records how sure you are as a band, never a number; it reads back what it will store and
you confirm or edit. The LLM must not invent your rationale.

Try it on the sample: *"Why may an overnight courier claim leave the standard path only
when all three conditions hold?"* — there is no right answer in the documents; that is
the point.

## Good questions to ask afterwards

- What is the exception process for overnight courier claims?
- Who must record a rationale before a payment above the settlement schedule?
- Which evidence is not acceptable, and where does that rule come from?
- Should an adjuster be able to pay a rush claim above schedule on their own judgement?
  (uses the *why* you gave, if you gave one)

## If something looks wrong

1. `curl http://localhost:8000/api/health` → `{"status":"ok","product":"GrACE-Demo"}`
2. `curl http://localhost:8000/api/graph/health` → `"status":"ok"`
3. `bash scripts/smoke-demo.sh` then `bash scripts/demo-fastpath.sh`
4. `.env` databases are `grace_demo` (Postgres and ArcadeDB)
5. Ask the LLM to show you the exact command that failed and its error.

## Privacy

Everything runs on your machine except calls to the cloud LLM you chose. Do not feed it
documents you are not allowed to process. Your key lives only in `.env`, which git ignores.
