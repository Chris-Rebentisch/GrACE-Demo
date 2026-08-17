# Contributing to GrACE-Demo

Thanks for trying the demo. This repository is a **classroom cut**: the goal is that
anyone can clone it, mount their own cloud LLM, and get from documents to an auditable
knowledge graph with intent captured — reliably. Contributions that keep it that way are
welcome.

## Before you open an issue

1. Run the two gates on your machine and paste their output:
   ```bash
   bash scripts/smoke-demo.sh
   bash scripts/demo-fastpath.sh
   ```
2. Say which OS, which cloud vendor (`config/discovery.yaml` `llm.provider`), and whether
   embeddings were on or off (the API logs `embeddings_disabled` at startup when off).
3. Never paste your `.env` or an API key. Redact anything that looks like a key.

## Making changes

- Install per [INSTALL.md](INSTALL.md); use the repo venv (`.venv/bin/python`).
- Keep the demo **vendor-agnostic** (Anthropic / OpenAI-compatible / Ollama all via
  `src/shared/llm_provider.py`) and **embedding-optional** (`GRACE_EMBED_PROVIDER=auto`
  must keep working with a chat-only key). See [docs/CHARTER.md](docs/CHARTER.md) for
  what is in and out of scope — please don't re-add a web UI or a human schema gate.
- Skills (`grace-claude-skills/*/SKILL.md`) must stay readable by any agent: paths
  relative to the checkout (`$GRACE_ROOT`), no vendor-specific wording.
- Tests: `python -m pytest tests/ -q`. The suite auto-redirects to isolated
  `grace_demo_test` databases (Postgres + ArcadeDB) — create them once, see
  `grace-claude-skills/grace-testing-protocol/SKILL.md`. Please don't blanket-skip
  failing tests; triage them.
- Sample corpus (`data/demo-corpus/`) must stay **fictional**. No real people, no real
  companies, no real emails or claims.

## Pull requests

- One topic per PR, with the two gates green and `pytest` green (or the failure
  explained).
- CI runs lint, a Tier-1 unit slice, and the full demo loop (migrate → API → smoke →
  fast path) against Postgres and ArcadeDB service containers. It must pass.
- The secret scan (gitleaks) must pass. If it flags a *documented fake* credential, add
  it to `.gitleaks.toml` with a comment; never a real one.

## Code of conduct

Be kind, be specific, assume good faith. This is a teaching project.
