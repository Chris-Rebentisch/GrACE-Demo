#!/usr/bin/env bash
# GrACE-Demo pre-demo smoke. Exit 0 only if the local API is actually up.
# Does NOT touch the GOLD `grace` database. Does NOT call a paid LLM.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API="${GRACE_API_BASE_URL:-http://127.0.0.1:8000}"
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

echo "== GrACE-Demo smoke against ${API} =="

health="$(curl -fsS "${API}/api/health" || true)"
echo "$health" | grep -q '"status":"ok"' || fail "/api/health not ok: ${health:-unreachable}"
echo "$health" | grep -q GrACE-Demo || fail "/api/health missing product name"

code="$(curl -s -o /dev/null -w '%{http_code}' "${API}/metrics")"
[[ "$code" == "200" ]] || fail "/metrics HTTP ${code}"

graph="$(curl -s -o /tmp/grace-demo-graph-health.json -w '%{http_code}' "${API}/api/graph/health")"
[[ "$graph" == "200" ]] || fail "/api/graph/health HTTP ${graph} (is ArcadeDB up? ARCADE_DATABASE=grace_demo?)"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
elif command -v python3 >/dev/null; then
  PY="python3"
else
  fail "no python"
fi

echo "== embedding unit tests (mocked HTTP, no GPU) =="
PYTHONPATH="$ROOT" "$PY" -m pytest tests/shared/test_embeddings.py -q --tb=line

echo "SMOKE PASS"
