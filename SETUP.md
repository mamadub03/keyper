# Keyper — local setup & demo walkthrough

Everything in Keyper runs on your machine. The only thing that doesn't is
**Amazon Bedrock AgentCore Browser**: it drives a real browser from an
AWS-managed environment, so the page it visits must be reachable from the
public internet. The controlled auth lab still runs locally — a short-lived
tunnel exposes it only while a scan is running, and nothing is deployed.

The AWS calls Keyper makes are billed per use, not hourly:

| Service | When it's used | Rough cost |
|---|---|---|
| Amazon Bedrock (Claude Sonnet 4.5) | every agent run | ~$0.10–0.50 per scan |
| AgentCore Browser | every agent run | ~1–2¢ per scan |
| AgentCore Runtime | only after you deploy (step 6) | consumption per request; ~$0 idle |

Nothing runs when you're not actively scanning.

---

## 0. Prerequisites

- **Python 3.12+**
- **Node.js 20+** (only needed for the UI in step 7 and the Runtime deploy
  in step 6)
- **AWS CLI v2**, authenticated (`aws sts get-caller-identity` succeeds)
- An AWS account with **Bedrock access to an Anthropic Claude Sonnet model**
  in your region (`us-west-2` and `us-east-1` are safe choices)
- A tunnel tool for step 4 — [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
  is used in the examples (quick tunnels need no account); `ngrok` works too

Set your region once per shell:

```bash
export KEYPER_AWS_REGION=us-west-2          # bash / git-bash
$env:KEYPER_AWS_REGION = "us-west-2"        # PowerShell
```

---

## 1. Prerequisite check

```bash
bash scripts/prereq_check.sh
```

Confirms your AWS identity, region, Bedrock Claude Sonnet model access,
Python version, and that the Python packages import. Fix anything that
isn't `ok` before continuing — the rest of the stack depends on it.

> On plain Windows PowerShell the `.sh` scripts don't run directly. Use
> git-bash / WSL, or open the script and run its commands one at a time.

---

## 2. Install Python dependencies

```bash
pip install -e ".[dev]"
# or, on a shared machine, in a venv:
python -m venv .venv
source .venv/bin/activate        # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Re-run `bash scripts/prereq_check.sh` — all five checks should now print `ok`.

---

## 3. Auth lab — verify it locally

```bash
uvicorn app:app --app-dir auth-lab --reload --port 8090
```

`auth-lab/` has a hyphen in its name so it can't be imported as
`auth-lab.app` — `--app-dir` is how uvicorn finds it.

Open <http://localhost:8090>, click through all four scenarios, and confirm
Scenario C's "Add personal login" / "Update recovery email" forms flip its
state (the page updates after each submit).

Run the zero-AWS unit tests:

```bash
pytest tests/test_auth_lab.py -v
```

All five should pass.

---

## 4. Expose the lab and do the first real agent run

Leave the lab from step 3 running. In another terminal:

```bash
cloudflared tunnel --url http://localhost:8090
# -> prints a public URL like https://random-words.trycloudflare.com
```

Point Keyper at that URL and run one scan:

```bash
export KEYPER_LAB_URL=https://random-words.trycloudflare.com     # bash
$env:KEYPER_LAB_URL = "https://random-words.trycloudflare.com"   # PowerShell

python -m agent.local_dev --identity student@g.school.edu --url "$KEYPER_LAB_URL/scenario-a"
```

Expect a `ScanResult` JSON with `"status": "SAFE"`. This is the milestone
that proves the whole foundation: a Strands agent using AgentCore Browser
navigates a page it has never seen and returns a structured, evidence-backed
result. If Strands or AgentCore Browser errors here, stop and fix it before
going further.

Then confirm the same agent generalizes, with no code changes between runs:

```bash
python -m agent.local_dev --identity student@g.school.edu --url "$KEYPER_LAB_URL/scenario-b"   # AT_RISK
python -m agent.local_dev --identity student@g.school.edu --url "$KEYPER_LAB_URL/scenario-c"   # AT_RISK
python -m agent.local_dev --identity student@g.school.edu --url "$KEYPER_LAB_URL/scenario-d"   # UNKNOWN
```

---

## 5. Fix flow, end to end

Scenario C starts `AT_RISK` and can be walked to `SAFE`:

```bash
python - <<'PY'
from agent.agent import run_scan, run_fix
from agent.schemas import ScanRequest, FixRequest
import os

url = os.environ["KEYPER_LAB_URL"] + "/scenario-c"
first = run_scan(ScanRequest(institutional_identity="student@g.school.edu", service_url=url))
print("before:", first.status)

fixed = run_fix(
    FixRequest(institutional_identity="student@g.school.edu", service_url=url, approved=True),
    prior_result_summary=first.summary,
)
print("after:", fixed.status)
PY
```

Expect `before: AT_RISK` then `after: SAFE`. If the agent hits a step that
needs a real secret it will pause and signal a human checkpoint instead of
guessing — that's correct behavior.

Reset the lab between runs:

```bash
bash scripts/reset_demo.sh
```

---

## 6. Deploy the agent to AgentCore Runtime

```bash
bash scripts/deploy_agent.sh
```

Follow the prompts. When it finishes, copy the runtime ARN into a `.env`
file at the repo root:

```
KEYPER_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:...
KEYPER_AWS_REGION=us-west-2
KEYPER_INVOKE_MODE=runtime
```

With `KEYPER_INVOKE_MODE=runtime`, the API calls the deployed agent instead
of running it in-process. Set it back to `local` to go back to in-process.

---

## 7. API + UI

```bash
# terminal 1
uvicorn api.main:app --reload --port 8000

# terminal 2
cd web
npm install
npm run dev
```

Open <http://localhost:5173>, enter your identity and the four lab scenario
URLs, click **Test My Accounts**, and confirm the result cards match what
you saw in steps 4–5. Click **Fix with Keyper** on Scenario C and confirm it
flips to green.

---

## Before every demo run

```bash
bash scripts/reset_demo.sh
```

Then restart the `uvicorn api.main:app` process so in-memory scan results are
cleared, and run the flow once to confirm the red → green transition is
repeatable.
