"""Scenario D deliberately withholds evidence — must come back UNKNOWN, not
a guessed SAFE. A false SAFE is worse than UNKNOWN (Section 0, rule 9)."""
import os

import pytest

from agent.agent import run_scan
from agent.schemas import ScanRequest

LAB_URL = os.environ.get("KEYPER_LAB_URL")

pytestmark = pytest.mark.skipif(
    not LAB_URL, reason="Set KEYPER_LAB_URL to your deployed auth lab's public URL to run integration tests."
)


def test_scenario_d_is_unknown_not_safe():
    request = ScanRequest(
        institutional_identity="student@g.school.edu",
        institutional_aliases=["student@school.edu"],
        service_url=f"{LAB_URL}/scenario-d",
    )
    result = run_scan(request)
    assert result.status in ("UNKNOWN", "AT_RISK")  # never a guessed SAFE
    assert result.status != "SAFE"
