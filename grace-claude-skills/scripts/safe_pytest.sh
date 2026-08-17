#!/usr/bin/env bash
# Safe pytest wrapper — enforces the GrACE test-DB isolation doctrine.
#
# The `tests/conftest.py` auto-redirects the test process to the `_test`
# sibling of the configured DB at import time (grace_demo -> grace_demo_test),
# so a normal `pytest tests/` can NEVER reach the demo data. This wrapper makes that explicit and refuses obviously
# unsafe DATABASE_URLs, then runs the default (non-perf, non-smoke) selection.
#
# Usage:
#   ./safe_pytest.sh                      # full safe suite
#   ./safe_pytest.sh tests/discovery -v   # scoped
#
# One-time test-DB setup (GrACE-Demo: the demo DB is grace_demo, so the sibling is
# grace_demo_test; see grace-testing-protocol/SKILL.md):
#   createdb grace_demo_test
#   DATABASE_URL=postgresql+psycopg2://$USER@localhost:5432/grace_demo_test alembic upgrade head
set -euo pipefail

# Default to the checkout this script lives in (…/grace-claude-skills/scripts/../..).
GRACE_ROOT="${GRACE_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$GRACE_ROOT"

# Refuse to run if someone hard-pointed DATABASE_URL at a protected DB.
if [[ "${DATABASE_URL:-}" =~ (prod|production|gold|live) ]]; then
  echo "[safe_pytest] REFUSING: DATABASE_URL points at a protected database." >&2
  exit 78
fi

PY="${GRACE_ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="python3"

echo "[safe_pytest] test-DB isolation active (conftest auto-redirect to the _test sibling). Running..."
exec "$PY" -m pytest "$@"
