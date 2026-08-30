#!/usr/bin/env bash
# Expose the LOCAL auth lab on a public HTTPS URL.
#
# AgentCore Browser runs inside AWS and cannot reach localhost, so the lab
# has to be reachable from the internet. `run.ps1` / `run.sh` already do this
# automatically with a cloudflared quick tunnel. Use this script only if you
# started the stack with --no-tunnel and now want a tunnel by hand.
#
# The lab is NOT deployed anywhere — it keeps running locally; the tunnel is
# just a temporary wire and closes when you Ctrl+C.
set -euo pipefail

PORT="${1:-8090}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found."
  echo "  Windows:  winget install --id Cloudflare.cloudflared"
  echo "  macOS:    brew install cloudflared"
  echo "  Linux:    https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

echo "Tunnelling http://localhost:$PORT ..."
echo "Copy the https://<name>.trycloudflare.com URL below into KEYPER_LAB_URL,"
echo "then restart the API so /demo-config picks it up."
echo
exec cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate
