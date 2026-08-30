"""Scenario A should come back SAFE.

These tests hit the real agent (and therefore real Bedrock + real AgentCore
Browser) against your deployed auth lab — they are integration tests, not
unit tests, and will not run without AWS credentials and a public
KEYPER_LAB_URL. That's intentional: the whole point of this project is that
the agent reasons over a real page, so there's no meaningful way to test it
with a mock.
"""
import os

import pytest

from agent.agent import run_scan
from agent.schemas import ScanRequest

LAB_URL = os.environ.get("KEYPER_LAB_URL")

pytestmark = pytest.mark.skipif(
    not LAB_URL, reason="Set KEYPER_LAB_URL to your deployed auth lab's public URL to run integration tests."
)


def test_scenario_a_is_safe():
    request = ScanRequest(
        institutional_identity="student@g.school.edu",
        institutional_aliases=["student@school.edu"],
        service_url=f"{LAB_URL}/scenario-a",
    )
    result = run_scan(request)
    assert result.status == "SAFE"
    assert result.authentication.independent_method_found
    assert result.recovery.independent_method_found
    assert len(result.evidence) > 0
