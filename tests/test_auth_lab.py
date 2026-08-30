"""Unit tests for the auth lab itself — no AWS, no agent, just the FastAPI
app. Run these FIRST after `pip install`, before anything AWS-related, as a
zero-dependency sanity check that the lab pages and the fix state machine
behave correctly on their own.
"""
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "auth-lab"))
lab = importlib.import_module("app")

client = TestClient(lab.app)


def setup_function():
    client.post("/reset")


def test_scenario_a_mentions_independent_password_and_personal_recovery():
    res = client.get("/scenario-a")
    assert res.status_code == 200
    assert "independent password" in res.text.lower()
    assert "personal.mail@example.com" in res.text


def test_scenario_b_is_sso_only_with_institutional_recovery():
    res = client.get("/scenario-b")
    assert "single sign-on only" in res.text.lower()
    assert "administrator" in res.text.lower()


def test_scenario_c_starts_at_risk_and_flips_to_safe_after_both_fixes():
    before = client.get("/scenario-c")
    assert "institutional sso" in before.text.lower()
    assert "student@school.edu" in before.text

    client.post("/scenario-c/add-login")
    client.post("/scenario-c/set-recovery", data={"recovery_email": "personal@example.com"})

    after = client.get("/scenario-c")
    assert "password sign-in" in after.text.lower()
    assert "personal@example.com" in after.text
    assert "student@school.edu" not in after.text


def test_scenario_c_rejects_blank_and_institutional_recovery_email():
    # The fix must move recovery OFF the institutional identity, so the lab
    # only accepts a real personal address.
    client.post("/scenario-c/set-recovery", data={"recovery_email": ""})
    client.post("/scenario-c/set-recovery", data={"recovery_email": "someone@g.school.edu"})
    res = client.get("/scenario-c")
    assert "student@school.edu (institutional" in res.text

    client.post("/scenario-c/set-recovery", data={"recovery_email": "me@personal.com"})
    res = client.get("/scenario-c")
    assert "me@personal.com" in res.text


def test_scenario_d_withholds_detail():
    res = client.get("/scenario-d")
    assert "administrator" in res.text.lower()
    assert "password" not in res.text.lower()


def test_reset_restores_scenario_c_to_at_risk():
    client.post("/scenario-c/add-login")
    client.post("/reset")
    res = client.get("/scenario-c")
    assert "institutional sso" in res.text.lower()
