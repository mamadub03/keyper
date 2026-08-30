# Keyper — 3-minute demo script

## Start

```powershell
./run.ps1        # Windows   (./run.sh on macOS/Linux)
```

Wait for **"Keyper is up"**, then the browser opens at <http://localhost:5173>.
The form is already filled with a demo identity and four test-service URLs.

## The walkthrough

1. **Click "Test My Accounts."**
   Keyper scans the four services one at a time; a card appears as each finishes
   (~40–90s each). Expected result:

   | Service | Verdict | Why |
   |---|---|---|
   | Aurora Notes (A) | 🟢 **SAFE** | independent password + personal recovery email |
   | Fluxboard (B) | 🔴 **AT RISK** | SSO-only, recovery handled by the institution |
   | Pinwheel Docs (C) | 🔴 **AT RISK** | SSO-only, institutional recovery contact |
   | Cobalt Suite (D) | 🟡 **UNKNOWN** | page hides the relevant settings — Keyper won't guess |

2. **Click "View Evidence"** on any card — every verdict is backed by concrete
   observations the agent made on the page, with where it saw each one.

3. **Click "Fix with Keyper"** on **Pinwheel Docs (C)** → **Start Fix.**
   The agent re-inspects the service, adds an independent password sign-in,
   moves the recovery email to a personal address, re-reads the page, and
   re-runs the continuity test. The card flips 🔴 → 🟢 **SAFE**.

   > If a service asked for a real password / MFA / OTP, the agent would stop
   > and hand the browser to you instead — it never touches secrets.

## Reset between runs

```bash
bash scripts/reset_demo.sh
```

Puts Pinwheel Docs back to AT RISK and clears cached results, so the
red → green moment is repeatable.

## What it costs

Model calls + browser time, only while a scan runs. A full take (4 scans +
1 fix) is roughly **$0.60**. Nothing runs when you're idle.

## Talking points

- **One site-agnostic agent.** No per-service code — the same prompt and the
  same generic tools handle all four differently-built pages. (`agent/prompts.py`,
  `agent/tools.py`.)
- **Real browser, in AWS.** The agent drives Amazon Bedrock AgentCore Browser
  against the live pages — it's reading real DOM, not calling an API.
- **Evidence-backed, never optimistic.** A false SAFE is treated as worse than
  an honest UNKNOWN (see Cobalt Suite).
- **Human keeps the secrets.** Scans are read-only; fixes are opt-in; anything
  needing a password/MFA/OTP stops for a human.
