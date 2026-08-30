#!/usr/bin/env bash
# One-command reset before/after every demo run. Clears both halves of the
# in-memory state so a red -> green walkthrough is repeatable:
#   - the auth lab's scenario-C state (back to AT_RISK)
#   - the API's cached scan results
set -euo pipefail

LAB_URL="${KEYPER_LAB_URL:-http://localhost:8090}"
API_URL="${KEYPER_API_URL:-http://localhost:8000}"

echo "Resetting auth lab at $LAB_URL ..."
curl -s -X POST "$LAB_URL/reset" -o /dev/null -w "  lab -> HTTP %{http_code}\n"

echo "Clearing API scan cache at $API_URL ..."
curl -s -X POST "$API_URL/reset" -o /dev/null -w "  api -> HTTP %{http_code}\n" || \
  echo "  (API not running or not reachable — that's fine if it's stopped)"

echo "Done. Re-run the flow to confirm the red -> green transition."
