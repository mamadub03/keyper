"""Scenarios B and C should both come back AT_RISK on a first scan."""
import os

import pytest

from agent.agent import run_fix, run_scan
from agent.schemas import FixRequest, ScanRequest

LAB_URL = os.environ.get("KEYPER_LAB_URL")

pytestmark = pytest.mark.skipif(
    not LAB_URL, reason="Set KEYPER_LAB_URL to your deployed auth lab's public URL to run integration tests."
)


def test_scenario_b_is_at_risk_with_no_fix_offered():
    request = ScanRequest(
        institutional_identity="student@g.school.edu",
        institutional_aliases=["student@school.edu"],
        service_url=f"{LAB_URL}/scenario-b",
    )
    result = run_scan(request)
    assert result.status == "AT_RISK"


def test_scenario_c_fix_flow_ends_safe():
    scan_request = ScanRequest(
        institutional_identity="student@g.school.edu",
        institutional_aliases=["student@school.edu"],
        service_url=f"{LAB_URL}/scenario-c",
    )
    first = run_scan(scan_request)
    assert first.status == "AT_RISK"

    fix_request = FixRequest(
        institutional_identity="student@g.school.edu",
        institutional_aliases=["student@school.edu"],
        service_url=f"{LAB_URL}/scenario-c",
        approved=True,
    )
    fixed = run_fix(fix_request, prior_result_summary=first.summary)
    assert fixed.status == "SAFE"
