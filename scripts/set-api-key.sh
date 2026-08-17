#!/usr/bin/env bash
# Sets LLM_API_KEY (the student's cloud LLM key — any vendor) in the project's .env.
# Resolves the project root from this script's own location, so it works
# regardless of where the repo is checked out. Portable sed (macOS + GNU).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

echo ""
echo "=== GrACE-Demo API key setup ==="
echo ""
echo "Paste the cloud LLM API key GrACE should use (Anthropic, OpenAI, DeepSeek, Groq, ...)"
echo "and press Enter. It is written ONLY to .env (gitignored) and never echoed."
echo ""
read -r -s -p "API key: " api_key
echo ""

if [[ -z "$api_key" ]]; then
    echo "No key entered. Nothing changed."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "No .env found at $ENV_FILE — run: cp .env.example .env"
    exit 1
fi

tmp="$(mktemp)"
if grep -q "^LLM_API_KEY=" "$ENV_FILE"; then
    awk -v key="$api_key" 'BEGIN{done=0} /^LLM_API_KEY=/ && !done {print "LLM_API_KEY=" key; done=1; next} {print}' "$ENV_FILE" > "$tmp"
else
    cat "$ENV_FILE" > "$tmp"; printf '\nLLM_API_KEY=%s\n' "$api_key" >> "$tmp"
fi
mv "$tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE" 2>/dev/null || true
echo "LLM_API_KEY updated in .env. Now set provider/model/base_url in config/discovery.yaml"
echo "(or POST /api/llm/config) to match that vendor — see docs/LLM_OPERATOR.md Session 0."
