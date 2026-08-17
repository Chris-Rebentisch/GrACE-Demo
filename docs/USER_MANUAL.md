# GrACE-Demo — end-user manual

This is for the person using the web UI (student, TA, presenter). Install is in [INSTALL.md](../INSTALL.md). Agents should read [LLM_OPERATOR.md](LLM_OPERATOR.md).

## What you will do

1. Point GrACE at documents (and optionally email).
2. Let the LLM propose an ontology; the system **auto-accepts** it (no schema click-through).
3. Extract facts into the graph.
4. Ask questions in **Chat**. Answers show certainty bands and source links.
5. Optionally capture *why* a decision was made (intent elicitation), not just *what* the documents say.

You do **not** design OWL types. You do **not** use a graph viewer in this demo (it was unreliable; ask the chat LLM if you want a picture).

## Screens (nav)

| Tab | Use it for |
|---|---|
| **Onboarding** | First-run checklist |
| **Sources** | Choose folders/files to process |
| **Ingestion** | Email sources (Gmail / IMAP / Exchange) — opt-in |
| **Chat** | Ask questions; this is the human-in-the-loop |
| **Inspector** | See what retrieval used for an answer |
| **Claims** | Flagged extractions if verification quarantined a fact |
| **Voice** | Communication style profiles + Voice Card export |
| **Settings** | Cloud provider, model, API key, optional Ollama |

Pages such as Guided Review, graph viewer, permissions, Grafana, and autonomy **are not in the demo nav** on purpose.

## Chat

- Ask in plain language (“What does the policy say about exceptions?”).
- Each substantive claim is tagged **high / medium / low / insufficient** — not a fake percentage.
- Click through to the source span when you need to defend an answer.
- If the LLM interviewer asks *why* you decided something, answer honestly. That intent is stored as graph structure so later questions can use it.

## Documents

Use **Sources** to include the sample corpus under `data/demo-corpus/` first. Then add your own PDF/DOCX/TXT. Binary office files go through Docling.

## Email (optional)

You can run the whole demo with files only.

To connect a live mailbox:

1. **Gmail** — create a Google Cloud OAuth client (readonly Gmail scope). Put client id/secret in `.env` as documented in onboarding. Never commit them.
2. **IMAP** — host, username, app password.
3. **Exchange** — Microsoft Graph app, `Mail.Read`.

Mail is **pulled read-only**. A thin filter drops empty/auto-reply noise, then relevant messages are extracted. Threads are reconstructed so the same conversation is not extracted twelve times. There is no “four-tier production plant” and no corroboration scorer in this demo.

## Voice Cards

After email is in the graph, **Voice** can build a communication style profile and export a Voice Card (markdown/json/yaml). This demo does **not** run PII redaction or a DPIA gate — do not export real colleagues’ mail in a public setting.

## Settings

- Pick Anthropic, OpenAI-compatible (ChatGPT, DeepSeek, Groq, Together), or optional Ollama.
- Cloud embeddings are the default (`GRACE_EMBED_PROVIDER=openai`). Switch to Ollama embeddings only if the machine can spare it.
- `airgap_mode` stays off unless you are fully local.

## When something looks wrong

1. `curl http://localhost:8000/api/health` → `{"status":"ok","product":"GrACE-Demo"}`
2. `curl http://localhost:8000/api/graph/health` → ArcadeDB up
3. Re-run `bash scripts/smoke-demo.sh`
4. Check `.env` database names are `grace_demo`, not `grace`
