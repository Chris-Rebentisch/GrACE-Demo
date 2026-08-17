## What

## Why

## Checks
- [ ] `bash scripts/smoke-demo.sh` green
- [ ] `bash scripts/demo-fastpath.sh` green
- [ ] `python -m pytest tests/ -q` green (or failures explained)
- [ ] Still vendor-agnostic and works with embeddings off (`GRACE_EMBED_PROVIDER=auto`, chat-only key)
- [ ] No keys, no real documents, no real people in samples
