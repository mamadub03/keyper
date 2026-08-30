"""The Keyper continuity agent.

One Strands agent, driven entirely by prompts.py + the generic tools in
tools.py, plus AWS's AgentCore Browser tool for real web interaction. This
module is imported directly for local testing (agent/local_dev.py) and
wrapped by agent/runtime_entrypoint.py for AgentCore Runtime deployment.

Do not add per-service branches here. If you need a new capability, it goes
in tools.py as a generic tool — never as an `if service_url == ...` check.
"""
from __future__ import annotations

import os

from strands import Agent
from strands.models import BedrockModel
from strands_tools.browser import AgentCoreBrowser

from .prompts import SYSTEM_PROMPT, build_fix_task, build_scan_task
from .schemas import FixRequest, ScanRequest, ScanResult
from .tools import EvidenceLog, make_tools

AWS_REGION = os.environ.get("KEYPER_AWS_REGION", "us-west-2")

# Prefer an available Claude Sonnet model through Bedrock. Verify the exact
# model ID enabled in your account/region with:
#   aws bedrock list-foundation-models --region $KEYPER_AWS_REGION \
#     --query "modelSummaries[?contains(modelId, 'claude-sonnet')].modelId"
# and override via the KEYPER_BEDROCK_MODEL_ID env var if this default isn't
# enabled for you.
BEDROCK_MODEL_ID = os.environ.get(
    "KEYPER_BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)


def _build_agent(log: EvidenceLog) -> Agent:
    model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION, temperature=0.2)
    browser_tool = AgentCoreBrowser(region=AWS_REGION)
    tools = [browser_tool.browser, *make_tools(log)]
    return Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)


def _run_structured(agent: Agent, task_prompt: str) -> ScanResult:
    """Run the agent's full browsing loop and get its answer back as a ScanResult.

    Confirmed against strands-agents 1.54.0 (see the SDK's ``Agent.__call__``
    and ``AgentResult`` definitions):

      - Passing ``structured_output_model=`` to the agent call runs the
        normal tool-use loop first — the agent drives the AgentCore browser
        and records evidence exactly as it would without structured output —
        and then projects the finished conversation onto the schema in the
        *same* invocation. That keeps it to one pass (cheaper) while still
        leaving the browser reasoning fully observable.
      - The parsed model lands on ``AgentResult.structured_output``.

    Fallback: if the loop ends without a schema-valid answer (it stopped at a
    human checkpoint, or a tool errored), do one explicit structuring pass
    over whatever conversation exists — ``Agent.structured_output(model)``
    with no prompt reads the existing history — so the caller always gets a
    ScanResult rather than ``None``.
    """
    result = agent(task_prompt, structured_output_model=ScanResult)
    if result.structured_output is None:
        return agent.structured_output(ScanResult)
    return result.structured_output


def run_scan(request: ScanRequest) -> ScanResult:
    log = EvidenceLog()
    agent = _build_agent(log)
    task_prompt = build_scan_task(
        request.institutional_identity, request.institutional_aliases, request.service_url
    )
    result = _run_structured(agent, task_prompt)

    # Belt-and-suspenders: if the model's own evidence list came back thin
    # but the record_evidence tool captured more, merge them in rather than
    # silently dropping observations.
    if len(log.items) > len(result.evidence):
        from .schemas import Evidence

        result.evidence = [Evidence(**item) for item in log.as_evidence_dicts()]

    if log.human_checkpoint and not result.human_action_required:
        result.human_action_required = True

    return result


def run_fix(request: FixRequest, prior_result_summary: str) -> ScanResult:
    if not request.approved:
        raise ValueError("run_fix called without explicit user approval")

    log = EvidenceLog()
    agent = _build_agent(log)
    task_prompt = build_fix_task(
        request.institutional_identity,
        request.institutional_aliases,
        request.service_url,
        prior_result_summary,
    )
    result = _run_structured(agent, task_prompt)

    if log.human_checkpoint and not result.human_action_required:
        result.human_action_required = True

    return result
