---
name: grace-testing-protocol
description: >
  How to run GrACE-Demo's test suite safely: test-DB isolation (pytest never
  touches the demo data), the three-tier test model, service markers, and the
  one smoke gate students actually need. Read before running any pytest.
---

# grace-testing-protocol

## What a student needs (and nothing more)
```bash
bash scripts/smoke-demo.sh       # API + graph + metrics up, embedding unit tests (mocked HTTP)
bash scripts/demo-fastpath.sh    # the whole document → graph → answer loop with shipped samples
```
Both must pass on the machine you demo from. The full pytest suite is for
maintainers.

## The one rule that matters most
**Tests must never touch the live demo/customer database.** `tests/conftest.py`
redirects the test process to the `_test` sibling of the configured DB at import
time, before the SQLAlchemy engine is built (`grace_demo` → `grace_demo_test`;
`ARCADE_DATABASE` gets a `_test` suffix too). Destructive fixtures therefore cannot
reach your data. Redirect precedence:
1. `GRACE_PYTEST_DATABASE_URL` (verbatim, highest)
2. a `DATABASE_URL` already ending `_test`
3. the derived `_test` sibling of the configured DB

**One-time setup (maintainers running the full suite):**
```bash
createdb grace_demo_test
DATABASE_URL=postgresql+psycopg2://$USER@localhost:5432/grace_demo_test .venv/bin/alembic upgrade head
curl -s -u root:gracedev -X POST http://localhost:2480/api/v1/server \
  -H 'Content-Type: application/json' -d '{"command":"create database grace_demo_test"}'
# re-run the alembic upgrade against grace_demo_test whenever migrations land
```

## DB-wipe guard (backstop layer)
Beneath isolation, `pytest_configure()` calls `pytest.exit(78)` if `DATABASE_URL`
still doesn't match a test-safe pattern. Rejected substrings: `prod`, `production`,
`gold`, `live`. Never weaken it.

## Three-tier model
- **Tier 1 — unit/contract:** no DB, no services. Always runnable.
- **Tier 2 — isolated integration:** runs against `grace_demo_test`.
- **Tier 3 — manual end-to-end:** the real demo stack, by hand (`scripts/demo-fastpath.sh`).

Service-dependent tests carry markers `requires_ollama` / `requires_arcade` /
`requires_live_server` / `requires_graph_corpus` and **auto-skip** when the
dependency is absent. Force them with `GRACE_REQUIRE_SERVICES=1`. The live smoke
harness is `@pytest.mark.smoke` and excluded from the default run.

## Embeddings are neutralised under pytest
`conftest.py` clears `GRACE_EMBED_*` so unit tests exercise the mocked HTTP paths
regardless of what your `.env` selects; tests that exercise the switch set it
explicitly with `monkeypatch`.

## How to run (use the wrapper)
```bash
grace-claude-skills/scripts/safe_pytest.sh                    # full safe suite
grace-claude-skills/scripts/safe_pytest.sh tests/discovery -v # scoped
```
The wrapper refuses prod/gold/live `DATABASE_URL`s and uses the repo `.venv`.

## Triage, don't blanket-skip
When a test fails, find the cause. Known failures live in
`docs/test-suite-allowlist.md` (≤5 entries, closed failure-class enum).

## Python interpreter
The system `python3` may be too old. Always use the repo venv: `.venv/bin/python`.
