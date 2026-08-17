#!/usr/bin/env bash
# GrACE-Demo — one-time model prefetch (needs network ONCE).
#
# Downloads the small CPU cross-encoder used to rerank retrieval results
# (cross-encoder/ms-marco-MiniLM-L-6-v2, ~90 MB) into the local Hugging Face
# cache. The API runs with HF_HUB_OFFLINE=1 afterwards; if this model is not
# cached, retrieval still works but keeps plain fusion order (no rerank).
#
# Usage:  bash scripts/prefetch-models.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python"; else PY="python3"; fi

export HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0
"$PY" - <<'PY'
from sentence_transformers import CrossEncoder
name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CrossEncoder(name)
print(f"[prefetch] cached {name} — retrieval reranking enabled")
PY
