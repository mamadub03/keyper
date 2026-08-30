"""AgentCore Runtime entrypoint.

Wraps agent.run_scan / agent.run_fix behind the BedrockAgentCoreApp HTTP
contract so `agentcore deploy` (or the older `agentcore launch`, depending on
which CLI generation you have installed — see RUNBOOK.md) can host this on
Amazon Bedrock AgentCore Runtime. AgentCore Runtime always POSTs to
/invocations and expects GET /ping to answer for health checks; app.run()
wires both of those up for you.

Expected payload shape (mirrors schemas.ScanRequest / FixRequest):

    {
      "institutional_identity": "student@g.school.edu",
      "institutional_aliases": ["student@school.edu"],
      "service_url": "https://example.com",
      "mode": "SCAN"
    }

    {
      "institutional_identity": "student@g.school.edu",
      "institutional_aliases": ["student@school.edu"],
      "service_url": "https://example.com",
      "mode": "FIX",
      "approved": true,
      "prior_result_summary": "AT_RISK: institutional SSO only login."
    }

Local smoke test (no deployment needed):
    python -m agent.runtime_entrypoint
    # in another terminal:
    curl -X POST http://localhost:8080/invocations \\
      -H "Content-Type: application/json" \\
      -d '{"institutional_identity":"student@g.school.edu","service_url":"https://example.com","mode":"SCAN"}'
"""
from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from .agent import run_fix, run_scan
from .schemas import FixRequest, Mode, ScanRequest

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    mode = payload.get("mode", Mode.SCAN.value)

    if mode == Mode.FIX.value:
        request = FixRequest(**{k: v for k, v in payload.items() if k != "prior_result_summary"})
        result = run_fix(request, prior_result_summary=payload.get("prior_result_summary", ""))
    else:
        request = ScanRequest(**payload)
        result = run_scan(request)

    return result.model_dump()


if __name__ == "__main__":
    app.run()
