"""Quick local smoke test for the agent, before wiring up FastAPI or Runtime.

This is the very first thing to run once AWS prerequisites are confirmed
(see RUNBOOK.md step 1). It exercises the exact same run_scan() path the
API and the deployed Runtime entrypoint use, so if this works, the rest of
the stack has a solid foundation under it.

Usage:
    python -m agent.local_dev --identity student@g.school.edu --url https://example.com
    python -m agent.local_dev --identity student@g.school.edu --alias student@school.edu --url https://example.com
"""
from __future__ import annotations

import argparse
import json

from .agent import run_scan
from .schemas import ScanRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Keyper continuity scan locally.")
    parser.add_argument("--identity", required=True, help="Primary institutional email")
    parser.add_argument("--alias", action="append", default=[], help="Known alias (repeatable)")
    parser.add_argument("--url", required=True, help="Service URL to test")
    args = parser.parse_args()

    request = ScanRequest(
        institutional_identity=args.identity,
        institutional_aliases=args.alias,
        service_url=args.url,
    )

    print(f"Scanning {args.url} ...\n")
    result = run_scan(request)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
