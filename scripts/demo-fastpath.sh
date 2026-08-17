#!/usr/bin/env bash
# GrACE-Demo — fast path: run the WHOLE document → graph → answer loop with the
# shipped sample artifacts (no chat-LLM calls). Use it to prove the stack works
# before you let the student's LLM author its own CQs / ontology / extractions.
#
#   bash scripts/demo-fastpath.sh            # process, import samples, query
#   bash scripts/demo-fastpath.sh --reset    # ALSO wipe + recreate the grace_demo
#                                            # databases first (Postgres + ArcadeDB)
#
# Prereqs: INSTALL.md steps 1–7 done and the API running on :8000
# (uvicorn src.api.main:app --port 8000). Never touches any database other
# than the one named in .env (DATABASE_URL / ARCADE_DATABASE = grace_demo).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GRACE_ROOT="$ROOT"
API="${GRACE_API_BASE_URL:-http://127.0.0.1:8000}"
S="$ROOT/grace-claude-skills/scripts"
SAMPLES="$ROOT/data/demo-corpus/samples"
if [[ -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python"; else PY="python3"; fi
fail() { echo "FASTPATH FAIL: $*" >&2; exit 1; }
step() { echo; echo "== $* =="; }

# --- read the target DB names from .env (never assume) ----------------------
envval() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'"; }
DB_URL="$(envval DATABASE_URL)"; ARCADE_DB="$(envval ARCADE_DATABASE)"
ARCADE_USER="$(envval ARCADE_USERNAME)"; ARCADE_PASS="$(envval ARCADE_PASSWORD)"
ARCADE_HOST="$(envval ARCADE_HOST)"; ARCADE_PORT="$(envval ARCADE_PORT)"
[[ -n "$DB_URL" ]] || fail ".env has no DATABASE_URL (cp .env.example .env first)"
PG_DB="${DB_URL##*/}"; PG_DB="${PG_DB%%\?*}"
: "${ARCADE_DB:=grace_demo}"; : "${ARCADE_USER:=root}"; : "${ARCADE_PASS:=gracedev}"
: "${ARCADE_HOST:=localhost}"; : "${ARCADE_PORT:=2480}"
case "$PG_DB" in
  grace|*gold*|*prod*) fail "refusing to run against database '$PG_DB' — this script is for the demo DB only";;
esac

if [[ "${1:-}" == "--reset" ]]; then
  step "reset: recreate Postgres '$PG_DB' and ArcadeDB '$ARCADE_DB'"
  read -r -p "This DROPS both '$PG_DB' databases. Type the database name to continue: " confirm
  [[ "$confirm" == "$PG_DB" ]] || fail "aborted"
  dropdb --if-exists "$PG_DB" && createdb "$PG_DB"
  curl -fsS -u "$ARCADE_USER:$ARCADE_PASS" -X POST "http://$ARCADE_HOST:$ARCADE_PORT/api/v1/server" \
    -H 'Content-Type: application/json' -d "{\"command\":\"drop database $ARCADE_DB\"}" >/dev/null 2>&1 || true
  curl -fsS -u "$ARCADE_USER:$ARCADE_PASS" -X POST "http://$ARCADE_HOST:$ARCADE_PORT/api/v1/server" \
    -H 'Content-Type: application/json' -d "{\"command\":\"create database $ARCADE_DB\"}" >/dev/null
  "$ROOT/.venv/bin/alembic" upgrade head >/dev/null 2>&1 || alembic upgrade head
  echo "databases recreated + migrated. RESTART the API now (it caches indexes), then re-run without --reset."
  exit 0
fi

step "0. API + graph reachable ($API)"
curl -fsS "$API/api/health" | grep -q GrACE-Demo || fail "API not up at $API — start: uvicorn src.api.main:app --port 8000"
code="$(curl -s -o /dev/null -w '%{http_code}' "$API/api/graph/health")"
[[ "$code" == "200" ]] || fail "/api/graph/health HTTP $code — is ArcadeDB up and database '$ARCADE_DB' created?"

step "1. process sample documents -> Postgres (Docling; no LLM)"
"$PY" -m src.discovery.batch_runner --source-dir data/demo-corpus/documents 2>&1 | grep -E "batch_complete|rror" || true

step "2. export corpus text for the LLM to read (workspace/corpus/)"
"$PY" "$S/export_corpus.py" 2>/dev/null

step "3. import sample competency questions"
"$PY" "$S/import_cqs.py" --in "$SAMPLES/cqs.json" --domain insurance 2>/dev/null

step "4. map CQ coverage + auto-accept the sample ontology (ratify + ArcadeDB DDL)"
cp "$SAMPLES/seed_schema.json" workspace/seed_schema.json
"$PY" "$S/map_coverage.py" --in workspace/seed_schema.json --domain insurance 2>/dev/null
"$PY" "$S/auto_accept.py" --in workspace/seed_schema.json --api-base "$API" --reviewer "auto-accept (fastpath)"

step "5. import sample extractions -> graph"
for f in "$SAMPLES"/extraction_*.json; do
  doc="$(basename "$f")"; doc="${doc#extraction_}"; doc="${doc%.json}.txt"
  "$PY" "$S/import_extraction.py" --in "$f" --doc-file "$doc" --module insurance --api-base "$API" 2>/dev/null | grep -E "^\[extract\] (resolved|phase|DONE|WARN|REVIEW)"
done

step "6. ask the graph (POST /api/retrieval/query)"
curl -fsS -X POST "$API/api/retrieval/query" -H 'Content-Type: application/json' -H 'X-Graph-Scope: all' \
  -d '{"query_text":"What is the exception process for overnight courier claims?","top_k":6}' \
  | "$PY" -c '
import json, sys
d = json.load(sys.stdin)
res = d.get("results") or []
mode = d.get("retrieval_mode")
strategies = sorted((d.get("strategy_contributions") or {}).keys())
print(str(len(res)) + " results (mode=" + str(mode) + "); strategies=" + str(strategies))
for r in res:
    print("  -", r.get("entity_type"), "|", r.get("name"))
ok = any("exception process" in (r.get("name") or "").lower() for r in res)
sys.exit(0 if ok else 1)
' || fail "retrieval did not surface the Exception process entity"

echo
echo "FASTPATH PASS — the graph is populated and answering. Next: docs/ONBOARDING.md (let the student's LLM do steps 2–6 itself), then intent Q&A."
