#!/usr/bin/env bash
# Deploy the Strands agent to Amazon Bedrock AgentCore Runtime.
#
# This is the one step that creates lasting AWS resources (an ECR image, an
# IAM execution role, a CDK bootstrap stack, and the Runtime itself). It is
# NOT needed for the local demo (`run.ps1` / `run.sh`) — do it only when you
# want the agent callable as a deployed endpoint (KEYPER_INVOKE_MODE=runtime).
#
# Tooling note: AWS is mid-migration here. The current CLI is the Node
# package `@aws/agentcore` (CDK-based). The older Python
# `bedrock-agentcore-starter-toolkit` is deprecated. Check `agentcore --help`
# and https://docs.aws.amazon.com/bedrock-agentcore/ before relying on the
# exact flags below.
set -euo pipefail
cd "$(dirname "$0")/.."

export AGENTCORE_SUPPRESS_RECOMMENDATION=1

echo "== 0. Prereqs =="
node --version || { echo "Install Node.js 20+ first."; exit 1; }
aws sts get-caller-identity >/dev/null || { echo "Run 'aws configure' first."; exit 1; }
command -v agentcore >/dev/null 2>&1 || {
  echo "Installing the AgentCore CLI (npm i -g @aws/agentcore)..."
  npm install -g @aws/agentcore
}

echo
echo "== 1. Local smoke test (no deploy) =="
echo "In another terminal:"
echo "    python -m agent.runtime_entrypoint"
echo "then:"
echo "    curl -s localhost:8080/ping"
echo "    curl -s -X POST localhost:8080/invocations -H 'content-type: application/json' \\"
echo "         -d '{\"institutional_identity\":\"student@g.school.edu\",\"service_url\":\"<public lab>/scenario-a\",\"mode\":\"SCAN\"}'"
echo "Confirm /ping is Healthy and /invocations returns a ScanResult JSON."
read -r -p "Press Enter once the local smoke test passes... "

echo
echo "== 2. Create / configure the AgentCore project =="
# Scaffolds agentcore.json + a Python runtime target. If it already exists
# this is a no-op. --build CodeZip avoids needing local Docker (the build
# runs in AWS CodeBuild).
if [ ! -f agentcore.json ]; then
  agentcore create \
    --project-name keyper \
    --framework Strands \
    --model-provider Bedrock \
    --language Python \
    --build CodeZip \
    --defaults --no-agent --json
  echo
  echo ">> Point the generated runtime entrypoint at agent/runtime_entrypoint.py"
  echo ">> (or copy its @app.entrypoint 'invoke' handler in), then re-run this script."
  exit 0
fi

echo
echo "== 3. Deploy (CDK) =="
echo "Creates: CDK bootstrap stack, ECR repo, IAM execution role, the Runtime."
echo "The execution role must allow bedrock:InvokeModel / Converse* AND the"
echo "bedrock-agentcore browser actions — if the first deployed invoke fails"
echo "with AccessDenied, add those to the role and redeploy."
read -r -p "Proceed with 'agentcore deploy'? [y/N] " ok
[ "$ok" = "y" ] || { echo "Aborted."; exit 0; }
agentcore deploy --yes --verbose

echo
echo "== 4. Runtime ARN -> .env =="
agentcore status --json | tee /tmp/agentcore_status.json
echo
echo "Copy the runtime ARN from the status output into a .env at the repo root:"
echo "    KEYPER_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:..."
echo "    KEYPER_AWS_REGION=us-west-2"
echo "    KEYPER_INVOKE_MODE=runtime"
echo
echo "Then start the API normally — it will call the deployed agent instead"
echo "of running it in-process. Set KEYPER_INVOKE_MODE=local to switch back."
