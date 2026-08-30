#!/usr/bin/env bash
# Run this FIRST, before touching any agent code (Section 16, 00:00-00:15).
# If any of these fail, stop and fix it before building anything else — the
# doc is explicit that this avoids building a whole product around an
# unavailable dependency.
#
# Works in bash/git-bash/WSL. On plain PowerShell, run the commands in
# RUNBOOK.md's "PowerShell equivalents" block instead.
set -euo pipefail

REGION="${KEYPER_AWS_REGION:-us-west-2}"

echo "== 1. Who am I? =="
aws sts get-caller-identity

echo
echo "== 2. Region =="
echo "Using region: $REGION (override with KEYPER_AWS_REGION)"

echo
echo "== 3. Bedrock Claude Sonnet model access in $REGION =="
aws bedrock list-foundation-models --region "$REGION" \
  --query "modelSummaries[?contains(modelId, 'claude-sonnet')].modelId" \
  --output table

echo
echo "== 4. Python version (need 3.12+) =="
python3 --version

echo
echo "== 5. Python packages import cleanly =="
python3 - <<'PY'
import importlib
for pkg in ["strands", "strands_tools", "bedrock_agentcore", "boto3", "pydantic", "fastapi", "nest_asyncio", "playwright"]:
    try:
        importlib.import_module(pkg)
        print(f"  ok: {pkg}")
    except ImportError as e:
        print(f"  MISSING: {pkg} ({e})")
PY

echo
echo "If everything above printed cleanly, continue to RUNBOOK.md step 2."
echo "If 'strands'/'bedrock_agentcore' are MISSING, run:"
echo "  pip install -e . --break-system-packages   # or inside a venv, drop the flag"
