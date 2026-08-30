#!/usr/bin/env bash
# One-command reset before/after every demo rehearsal (Section 16, 01:55-02:00).
set -euo pipefail

LAB_URL="${KEYPER_LAB_URL:-http://localhost:8090}"

echo "Resetting auth lab state at $LAB_URL ..."
curl -s -X POST "$LAB_URL/reset" -o /dev/null -w "reset -> HTTP %{http_code}\n"

echo "Restart the API so in-memory scan results are cleared too:"
echo "  (Ctrl+C the running 'uvicorn api.main:app' process, then start it again)"
