"""Structured data contracts for Keyper.

These Pydantic models are the ONLY interface between the Strands agent and
everything else (FastAPI, the React UI, tests). The agent must never return
free-form prose as its final answer — it returns a ScanResult, always.

See keyper_engineering_kickoff.md Section 13 for the source-of-truth schema.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Mode(str, Enum):
    SCAN = "SCAN"
    FIX = "FIX"


class ContinuityStatus(str, Enum):
    SAFE = "SAFE"
    AT_RISK = "AT_RISK"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    """One service check. institutional_identity + aliases together form the
    'institutional identity family' — every member is treated as unavailable
    for the duration of the test (Section 4)."""

    institutional_identity: str = Field(..., description="Primary institutional email, e.g. student@g.school.edu")
    institutional_aliases: List[str] = Field(default_factory=list, description="Other known aliases for the same identity family")
    service_url: str = Field(..., description="Public URL of the service to test")
    mode: Mode = Mode.SCAN


class FixRequest(ScanRequest):
    mode: Mode = Mode.FIX
    approved: bool = Field(..., description="User has explicitly approved remediation for this service")


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


class Evidence(BaseModel):
    observation: str
    source: str = Field(..., description="Where this was observed, e.g. 'Account > Security'")


class AuthenticationFindings(BaseModel):
    institutional_methods_found: List[str] = Field(default_factory=list)
    independent_method_found: bool = False
    independent_method: Optional[str] = None
    verified: bool = False


class RecoveryFindings(BaseModel):
    institutional_dependency_found: bool = False
    independent_method_found: bool = False
    verified: bool = False


class RemediationOption(BaseModel):
    action: str = Field(..., description="Human-readable description of an available fix, e.g. 'Set an independent password'")
    requires_secret_input: bool = Field(
        default=True,
        description="True if a human must supply a password/MFA/OTP/recovery code/security key to complete this step",
    )


class ScanResult(BaseModel):
    service_name: str
    service_url: str
    status: ContinuityStatus
    authentication: AuthenticationFindings
    recovery: RecoveryFindings
    dependencies: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    remediation_options: List[RemediationOption] = Field(default_factory=list)
    human_action_required: bool = False
    summary: str

    class Config:
        use_enum_values = True
