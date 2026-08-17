---
name: Bug report
about: Something in the demo loop did not work
title: ''
labels: bug
---

**Which step failed?** (INSTALL step N / smoke / fastpath / a skill step / a question)

**Gate output** — paste the tail of:
```
bash scripts/smoke-demo.sh
bash scripts/demo-fastpath.sh
```

**Environment**
- OS:
- Cloud vendor (`config/discovery.yaml` `llm.provider` / `llm.model`):
- Embeddings on or off? (API startup log line `embeddings_disabled` present?):
- Which LLM/agent was operating (Claude Code / Cursor / ChatGPT / …):

**What happened / expected**

**Logs** (redact anything that looks like a key — never paste `.env`)
