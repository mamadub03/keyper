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
import sys

from strands import Agent
from strands.models import BedrockModel
from strands.types.agent import Limits
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

# Per-1M-token USD rates for the cost estimate printed when
# KEYPER_DEBUG_METRICS is set. Defaults are Claude Sonnet 4.5 on Bedrock
# (input / output / cache-read / cache-write); override if you point
# KEYPER_BEDROCK_MODEL_ID at a different model.
_PRICE_PER_MTOK = {
    "in": float(os.environ.get("KEYPER_PRICE_IN", "3.0")),
    "out": float(os.environ.get("KEYPER_PRICE_OUT", "15.0")),
    "cache_read": float(os.environ.get("KEYPER_PRICE_CACHE_READ", "0.30")),
    "cache_write": float(os.environ.get("KEYPER_PRICE_CACHE_WRITE", "3.75")),
}


def _log_run_cost(label: str, result) -> None:
    """Print token usage + a rough Bedrock cost for one agent invocation.

    Only fires when KEYPER_DEBUG_METRICS is set, and never raises — a
    metrics-shape change in the SDK must not break a scan.
    """
    if not os.environ.get("KEYPER_DEBUG_METRICS"):
        return
    try:
        u = result.metrics.accumulated_usage
        i, o = int(u.get("inputTokens", 0)), int(u.get("outputTokens", 0))
        cr, cw = int(u.get("cacheReadInputTokens", 0)), int(u.get("cacheWriteInputTokens", 0))
        cost = (
            i / 1e6 * _PRICE_PER_MTOK["in"]
            + o / 1e6 * _PRICE_PER_MTOK["out"]
            + cr / 1e6 * _PRICE_PER_MTOK["cache_read"]
            + cw / 1e6 * _PRICE_PER_MTOK["cache_write"]
        )
        cycles = getattr(result.metrics, "cycle_count", "?")
        print(
            f"[keyper cost] {label}: {cycles} cycles | "
            f"in={i} out={o} cache_read={cr} cache_write={cw} tok "
            f"| ~${cost:.4f} (model inference only; AgentCore Browser billed separately)",
            file=sys.stderr,
        )
    except Exception as exc:  # pragma: no cover - diagnostics must never break a run
        print(f"[keyper cost] ({label}) metrics unavailable: {exc}", file=sys.stderr)


# Per-invocation runaway guards. A well-behaved scan of any of the demo
# scenarios finishes in well under 15 cycles; anything past TURN_LIMIT is the
# agent thrashing (e.g. re-loading a deliberately sparse page over and over),
# which just burns tokens without improving the answer. When a limit trips
# the loop stops cleanly and _run_structured() falls back to an explicit
# structuring pass. Override via env for debugging.
TURN_LIMIT = int(os.environ.get("KEYPER_MAX_TURNS", "16"))
TOTAL_TOKEN_LIMIT = int(os.environ.get("KEYPER_MAX_TOKENS", "300000"))


def _build_agent(log: EvidenceLog) -> Agent:
    # cache_config="auto" + cache_tools puts Bedrock prompt-cache checkpoints
    # on the (large, unchanging) system prompt and tool definitions. Across a
    # multi-cycle browsing loop those are re-sent every turn, so caching them
    # drops their input cost from $3.00 to $0.30 per million tokens — the
    # single biggest lever on per-scan cost.
    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name=AWS_REGION,
        temperature=0.2,
        cache_config={"strategy": "auto"},
        cache_tools="default",
    )
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
    result = agent(
        task_prompt,
        structured_output_model=ScanResult,
        limits=Limits(turns=TURN_LIMIT, total_tokens=TOTAL_TOKEN_LIMIT),
    )
    _log_run_cost("scan/fix", result)
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
