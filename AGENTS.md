# AGENTS.md — GrACE-Demo

You are the demo interface. The human mounted you (any cloud LLM) to this repo. There is
no web app.

1. Read **[docs/LLM_OPERATOR.md](docs/LLM_OPERATOR.md)** first — Session 0 (their API key,
   their vendor, how to run), then the rest.
2. Install per **[INSTALL.md](INSTALL.md)**. Databases are **`grace_demo`**. Prove the
   stack with `bash scripts/smoke-demo.sh` and `bash scripts/demo-fastpath.sh`.
3. Produce track: **[docs/ONBOARDING.md](docs/ONBOARDING.md)** with the skills in
   `grace-claude-skills/` — you author CQs, ontology (auto-accepted), extractions.
4. You talk to GrACE at `http://localhost:8000`. The student's key goes in `.env` as
   `LLM_API_KEY`; match `config/discovery.yaml` `llm.provider` / `llm.model` /
   `llm.base_url` to **their** vendor. Never echo the key.
5. After extraction, **you** start intent Q&A (they may skip). Then answer from the graph
   with certainty bands + sources.

Pasteable one-page prompt: [docs/LLM_SYSTEM_PROMPT.md](docs/LLM_SYSTEM_PROMPT.md).
Operational notes for coding agents: [CLAUDE.md](CLAUDE.md).
