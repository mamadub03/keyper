#!/usr/bin/env bash
# Deploy the Strands agent to Amazon Bedrock AgentCore Runtime (Section 8.3).
#
# AWS's AgentCore CLI is actively evolving — verify these commands against
# `agentcore --help` and
# https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html
# before relying on them; the exact flags below were confirmed by fetching
# that page while this repo was scaffolded, but this is a fast-moving SDK.
set -euo pipefail

echo "== 0. Prereqs =="
echo "This needs Node.js 20+ (for the agentcore CLI) in addition to Python."
node --version || { echo "Install Node.js 20+ first."; exit 1; }

if ! command -v agentcore >/dev/null 2>&1; then
  echo "Installing AgentCore CLI globally..."
  npm install -g @aws/agentcore
fi

echo
echo "== 1. Local dev server (sanity check before deploying) =="
echo "In another terminal, run:"
echo "  cd agent && python -m runtime_entrypoint"
echo "Then: curl -X POST http://localhost:8080/invocations -H 'Content-Type: application/json' \\"
echo "    -d '{\"institutional_identity\":\"student@g.school.edu\",\"service_url\":\"<your lab URL>/scenario-a\",\"mode\":\"SCAN\"}'"
echo "Confirm you get a ScanResult JSON back before continuing."
read -p "Press Enter once the local smoke test above works..."

echo
echo "== 2. Deploy =="
agentcore deploy || {
  echo "If 'agentcore deploy' isn't available in your installed CLI version,"
  echo "try 'agentcore launch' instead (older CLI generations used that verb)."
  exit 1
}

echo
echo "== 3. Get the runtime ARN =="
agentcore status

echo
echo "Copy the runtime ARN above into your .env as KEYPER_AGENT_RUNTIME_ARN,"
echo "then set KEYPER_INVOKE_MODE=runtime so api/main.py calls the deployed"
echo "agent instead of running it in-process."
