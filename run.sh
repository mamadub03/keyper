#!/usr/bin/env bash
# Keyper — one-command local launcher (macOS / Linux).
#
# Brings up the whole stack and opens the browser:
#
#   auth lab (uvicorn :8090)
#     -> cloudflared quick tunnel   (public URL, so AgentCore Browser can reach the lab)
#   API / BFF (uvicorn :8000)       (KEYPER_INVOKE_MODE=local -> agent runs in-process)
#   web UI (vite :5173)             (form pre-filled with the 4 demo scenarios)
#
# The only prerequisite is AWS credentials configured once with `aws configure`
# (or SSO). Nothing is typed into the app. Ctrl+C tears everything down.
#
# Usage:  ./run.sh              # full demo (lab + tunnel + API + UI)
#         ./run.sh --no-tunnel  # skip lab+tunnel; UI form starts blank
set -euo pipefail
cd "$(dirname "$0")"

NO_TUNNEL=0
[ "${1:-}" = "--no-tunnel" ] && NO_TUNNEL=1

PY=$(command -v python3 || command -v python || true)
[ -n "$PY" ] || { echo "python3 not found (need 3.12+)."; exit 1; }

if [ "$NO_TUNNEL" -eq 0 ] && ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Install it (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)"
  echo "or run ./run.sh --no-tunnel and type service URLs into the form yourself."
  exit 1
fi

echo "Checking AWS credentials..."
aws sts get-caller-identity >/dev/null 2>&1 || {
  echo "AWS credentials not working. Run 'aws configure' (or 'aws sso login') first."; exit 1;
}
export KEYPER_AWS_REGION="${KEYPER_AWS_REGION:-us-west-2}"

# deps — install once
"$PY" -c "import strands, fastapi" >/dev/null 2>&1 || {
  echo "Installing Python dependencies (one-time)..."; "$PY" -m pip install -e ".[dev]";
}
[ -d web/node_modules ] || { echo "Installing web dependencies (one-time)..."; (cd web && npm install); }

pids=()
cleanup() {
  echo
  echo "Shutting down..."
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ "$NO_TUNNEL" -eq 0 ]; then
  echo "Starting auth lab on :8090..."
  "$PY" -m uvicorn app:app --app-dir auth-lab --port 8090 --log-level warning & pids+=($!)

  echo "Opening cloudflared tunnel..."
  tlog=$(mktemp)
  cloudflared tunnel --url http://localhost:8090 --no-autoupdate --logfile "$tlog" & pids+=($!)

  LAB_URL=""
  for _ in $(seq 1 40); do
    sleep 0.75
    LAB_URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$tlog" | head -1 || true)
    [ -n "$LAB_URL" ] && break
  done
  [ -n "$LAB_URL" ] || { echo "Tunnel did not report a URL in time (see $tlog)."; exit 1; }
  export KEYPER_LAB_URL="$LAB_URL"
  echo "  lab reachable at $LAB_URL"
fi

echo "Starting API on :8000..."
"$PY" -m uvicorn api.main:app --port 8000 --log-level warning & pids+=($!)

echo "Starting web UI on :5173..."
(cd web && npm run dev -- --host 127.0.0.1 --strictPort) & pids+=($!)

sleep 3
( command -v open >/dev/null && open http://localhost:5173 ) || \
( command -v xdg-open >/dev/null && xdg-open http://localhost:5173 ) || true

echo
echo "Keyper is up. Open http://localhost:5173  —  Ctrl+C to stop."
echo
wait
