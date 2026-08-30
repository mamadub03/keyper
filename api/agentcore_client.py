"""boto3 wrapper for invoking the deployed AgentCore Runtime agent.

Only used when KEYPER_INVOKE_MODE=runtime. Until you've deployed
(RUNBOOK.md step 5), leave KEYPER_INVOKE_MODE=local and api/main.py will
call the agent in-process instead — same request/response shape either way,
so switching later is a one-line env var change, not a rewrite.
"""
from __future__ import annotations

import json
import os
import uuid

import boto3

AWS_REGION = os.environ.get("KEYPER_AWS_REGION", "us-west-2")
AGENT_RUNTIME_ARN = os.environ.get("KEYPER_AGENT_RUNTIME_ARN", "")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)
    return _client


def invoke_runtime(payload: dict) -> dict:
    if not AGENT_RUNTIME_ARN:
        raise RuntimeError(
            "KEYPER_AGENT_RUNTIME_ARN is not set. Deploy the agent first "
            "(see RUNBOOK.md step 5) and copy the runtime ARN from "
            "`agentcore status` / `agentcore deploy` output into your .env."
        )

    client = _get_client()
    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_RUNTIME_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps(payload).encode(),
        qualifier="DEFAULT",
    )

    chunks = []
    for chunk in response.get("response", []):
        chunks.append(chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else chunk)
    return json.loads("".join(chunks))
