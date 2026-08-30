"""Keyper FastAPI BFF.

Responsibilities ONLY (Section 9 of the kickoff doc):
- accept UI test requests,
- validate institutional identities/service URLs,
- invoke the agent (locally in-process, or the deployed AgentCore Runtime),
- normalize/return structured results to the UI,
- initiate a Fix request after explicit user approval.

No continuity/risk/remediation business logic lives here — that is entirely
the agent's job. This file should stay boring on purpose.
"""
from __future__ import annotations

import os
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.schemas import FixRequest, ScanRequest, ScanResult

INVOKE_MODE = os.environ.get("KEYPER_INVOKE_MODE", "local")  # "local" | "runtime"

app = FastAPI(title="Keyper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("KEYPER_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tier-1 MVP persistence: in-memory only, per Section 9. Keyed by service_url
# so a Fix request can reference the scan that preceded it. Restarting the
# API clears this, which is fine for a hackathon demo.
_last_results: Dict[str, ScanResult] = {}


def _invoke(payload: dict) -> ScanResult:
    if INVOKE_MODE == "runtime":
        from api.agentcore_client import invoke_runtime

        raw = invoke_runtime(payload)
        return ScanResult.model_validate(raw)
    else:
        from agent.agent import run_fix, run_scan

        if payload.get("mode") == "FIX":
            request = FixRequest(**{k: v for k, v in payload.items() if k != "prior_result_summary"})
            return run_fix(request, prior_result_summary=payload.get("prior_result_summary", ""))
        request = ScanRequest(**payload)
        return run_scan(request)


@app.get("/health")
def health():
    return {"status": "ok", "invoke_mode": INVOKE_MODE}


@app.post("/scan", response_model=ScanResult)
def scan(request: ScanRequest):
    if not request.service_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="service_url must be a full http(s) URL")

    result = _invoke(request.model_dump())
    _last_results[request.service_url] = result
    return result


@app.post("/fix", response_model=ScanResult)
def fix(request: FixRequest):
    if not request.approved:
        raise HTTPException(status_code=400, detail="Fix requires explicit user approval (approved=true)")

    prior = _last_results.get(request.service_url)
    if prior is None:
        raise HTTPException(
            status_code=409,
            detail="No prior scan found for this service_url — run /scan before /fix",
        )

    payload = request.model_dump()
    payload["prior_result_summary"] = prior.summary
    result = _invoke(payload)
    _last_results[request.service_url] = result
    return result
