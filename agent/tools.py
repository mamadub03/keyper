"""Generic tools for the Keyper continuity agent.

Per Section 12 of the kickoff doc, keep this tool surface small and generic:
- the browser (AgentCoreBrowser, wired up in agent.py — not here),
- a structured evidence recorder,
- a human-action signal,
- a small alias-format utility.

Nothing here is site-specific. If a tool needs to know about a particular
service's UI, it does not belong in this file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from strands import tool


@dataclass
class EvidenceLog:
    """Shared, per-run scratch space the agent's tools write into.

    A fresh instance is created for every scan/fix run (see agent.py) so
    concurrent runs never share state.
    """

    items: List[dict] = field(default_factory=list)
    human_checkpoint: dict | None = None

    def as_evidence_dicts(self) -> List[dict]:
        return list(self.items)


def make_tools(log: EvidenceLog):
    """Build tool functions bound to this run's EvidenceLog.

    Strands tools are plain functions; binding them via closure keeps each
    scan's evidence isolated without any global state.
    """

    @tool
    def record_evidence(observation: str, source: str) -> str:
        """Record a concrete, observed fact and where on the page you saw it.

        Call this every time you notice something relevant to authentication
        or recovery continuity — do NOT wait until the end and reconstruct
        evidence from memory. Only record things you actually observed.

        Args:
            observation: The concrete fact you observed, e.g. "Password login
                is configured" or "Recovery email field shows student@school.edu".
            source: Where you saw it, e.g. "Account > Security" or the page
                title/URL fragment.
        """
        log.items.append({"observation": observation, "source": source})
        return f"Recorded ({len(log.items)} total)."

    @tool
    def request_human_checkpoint(reason: str, secret_type: str) -> str:
        """Signal that you have hit a step only a human may perform, and stop.

        Call this instead of guessing whenever the service asks for a
        password, MFA code, OTP, recovery code, security key, CAPTCHA, or any
        other secret/sensitive confirmation. After calling this, do not
        attempt the step yourself — end your turn so a human can take over
        the browser session.

        Args:
            reason: What you were trying to do when you hit this wall.
            secret_type: The kind of secret being requested, e.g. "password",
                "MFA code", "OTP", "recovery code", "security key", "CAPTCHA".
        """
        log.human_checkpoint = {"reason": reason, "secret_type": secret_type}
        return (
            "Checkpoint recorded. Stop here — do not enter or guess this "
            "value. End your turn now; a human will complete this step and "
            "the run will resume."
        )

    @tool
    def validate_institutional_alias(email: str) -> bool:
        """Return True if `email` looks like a well-formed email address.

        Purely a formatting sanity check — this tool has no knowledge of any
        particular institution's domain and must not be used to decide
        whether an identity is institutional (that is a reasoning judgment,
        not a lookup).
        """
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))

    return [record_evidence, request_human_checkpoint, validate_institutional_alias]
