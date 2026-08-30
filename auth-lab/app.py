"""Controlled authentication lab.

Four tiny, publicly-servable "account settings" pages the agent has never
seen before. Per Section 11 of the kickoff doc, each one uses different
wording, DOM structure, and navigation so the agent genuinely has to reason
about the page rather than pattern-match on markup it was tuned against.

Run locally:
    uvicorn auth-lab.app:app --reload --port 8090

Then deploy somewhere with a public HTTPS URL (see scripts/deploy_lab.sh and
RUNBOOK.md) — AgentCore Browser runs in an AWS-managed environment and
cannot reach localhost.

State is in-memory only (Section 9: "Tier-1 MVP" — no database). Scenario C
is the only one that mutates: it starts AT_RISK and flips to SAFE once its
two non-secret setup steps are completed, so a fix -> re-test demo has
something real to observe. POST /reset puts everything back for the next
demo run.
"""
from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Keyper Auth Lab")


# ---------------------------------------------------------------------------
# Mutable state (Scenario C only)
# ---------------------------------------------------------------------------

def _initial_state() -> dict:
    return {
        "independent_login_added": False,
        "recovery_email": "student@school.edu",  # institutional — the risk
    }


state = _initial_state()


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; }} h2 {{ font-size: 1.1rem; margin-top: 1.5rem; }}
  .tile {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; margin: 10px 0; }}
  dt {{ font-weight: 600; margin-top: 10px; }} dd {{ margin: 2px 0 0 0; color: #444; }}
  button {{ padding: 8px 14px; border-radius: 6px; border: 1px solid #333; background: #fff; cursor: pointer; }}
  nav a {{ margin-right: 14px; }}
</style></head>
<body>
<nav><a href="/">Lab index</a></nav>
{body}
</body></html>""")


# ---------------------------------------------------------------------------
# Lab index
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return _page(
        "Keyper Auth Lab",
        """
<h1>Keyper controlled authentication lab</h1>
<p>Four independent test services, each with a different account-settings
layout. Feed any of these URLs into Keyper as a "service to test".</p>
<ul>
  <li><a href="/scenario-a">Scenario A — Aurora Notes</a></li>
  <li><a href="/scenario-b">Scenario B — Fluxboard</a></li>
  <li><a href="/scenario-c">Scenario C — Pinwheel Docs</a></li>
  <li><a href="/scenario-d">Scenario D — Cobalt Suite</a></li>
</ul>
<form method="post" action="/reset"><button type="submit">Reset demo state</button></form>
""",
    )


@app.post("/reset")
def reset():
    global state
    state = _initial_state()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------------
# Scenario A — SAFE. Definition-list layout, "Account & Security" sidebar.
# ---------------------------------------------------------------------------

@app.get("/scenario-a", response_class=HTMLResponse)
def scenario_a():
    return _page(
        "Aurora Notes — Account & Security",
        """
<h1>Aurora Notes</h1>
<h2>Account &amp; Security</h2>
<dl>
  <dt>Connected identity providers</dt>
  <dd>Institution Google Workspace (student@g.school.edu) — connected</dd>
  <dt>Password sign-in</dt>
  <dd>Enabled — an independent password is set on this account</dd>
  <dt>Account recovery email</dt>
  <dd>personal.mail@example.com (verified)</dd>
  <dt>Two-factor method</dt>
  <dd>Authenticator app, not tied to any identity provider</dd>
</dl>
""",
    )


# ---------------------------------------------------------------------------
# Scenario B — AT RISK, no easy fix. Card-grid layout, "Access & Recovery".
# ---------------------------------------------------------------------------

@app.get("/scenario-b", response_class=HTMLResponse)
def scenario_b():
    return _page(
        "Fluxboard — Access & Recovery",
        """
<h1>Fluxboard</h1>
<h2>Access &amp; Recovery</h2>
<div class="tile">
  <strong>Sign-in method</strong><br>
  Organization single sign-on only (managed by g.school.edu). No password
  or alternate provider is configured for this workspace member.
</div>
<div class="tile">
  <strong>Recovery</strong><br>
  Account recovery is handled entirely by your organization administrator
  through the institutional identity provider. There is no personal
  recovery contact on file.
</div>
""",
    )


# ---------------------------------------------------------------------------
# Scenario C — AT RISK, fixable. Tabbed/details layout, "Sign-in Options".
# Mutates `state` when the two setup forms are submitted.
# ---------------------------------------------------------------------------

@app.get("/scenario-c", response_class=HTMLResponse)
def scenario_c():
    login_line = (
        "Personal login is configured and active."
        if state["independent_login_added"]
        else "Institutional SSO (g.school.edu) is currently the only sign-in method."
    )
    recovery_line = (
        f"Recovery contact: {state['recovery_email']} (personal)"
        if state["recovery_email"] != "student@school.edu"
        else "Recovery contact: student@school.edu (institutional)"
    )

    add_login_block = "" if state["independent_login_added"] else """
<details open>
  <summary>Sign-in</summary>
  <p>You can add a personal login method so this account no longer depends
  solely on institutional SSO.</p>
  <form method="post" action="/scenario-c/add-login">
    <button type="submit">Add personal login</button>
  </form>
</details>"""

    change_recovery_block = "" if state["recovery_email"] != "student@school.edu" else """
<details open>
  <summary>Recovery</summary>
  <p>Update the email used to recover this account if you're ever locked
  out.</p>
  <form method="post" action="/scenario-c/set-recovery">
    <label>New recovery email
      <input type="email" name="recovery_email" placeholder="you@personal-example.com" required>
    </label>
    <button type="submit">Update recovery email</button>
  </form>
</details>"""

    return _page(
        "Pinwheel Docs — Sign-in Options",
        f"""
<h1>Pinwheel Docs</h1>
<h2>Sign-in Options</h2>
<p>{login_line}</p>
<p>{recovery_line}</p>
{add_login_block}
{change_recovery_block}
""",
    )


@app.post("/scenario-c/add-login")
def scenario_c_add_login():
    state["independent_login_added"] = True
    return RedirectResponse("/scenario-c", status_code=303)


@app.post("/scenario-c/set-recovery")
def scenario_c_set_recovery(recovery_email: str = Form(...)):
    state["recovery_email"] = recovery_email
    return RedirectResponse("/scenario-c", status_code=303)


# ---------------------------------------------------------------------------
# Scenario D — UNKNOWN. Deliberately withholds enough evidence either way.
# ---------------------------------------------------------------------------

@app.get("/scenario-d", response_class=HTMLResponse)
def scenario_d():
    return _page(
        "Cobalt Suite — Manage account",
        """
<h1>Cobalt Suite</h1>
<h2>Manage account</h2>
<p>Some account settings are managed by your organization and are not shown
here. For sign-in or recovery changes, contact your workspace
administrator.</p>
<p><em>(This page intentionally exposes limited detail — a correct agent
should return UNKNOWN rather than guess.)</em></p>
""",
    )
