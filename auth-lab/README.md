# Keyper — controlled authentication lab

Four tiny "account settings" pages used as the agent's test targets. Each
one has a different DOM structure, wording, and layout on purpose — see
`app.py` docstring — so a passing scan proves the agent is actually reading
the page, not matching a pattern it was tuned on.

| Route          | Product name  | Expected result   |
|----------------|---------------|--------------------|
| `/scenario-a`  | Aurora Notes  | `SAFE`             |
| `/scenario-b`  | Fluxboard     | `AT_RISK` (no fix) |
| `/scenario-c`  | Pinwheel Docs | `AT_RISK` → fixable → re-test `SAFE` |
| `/scenario-d`  | Cobalt Suite  | `UNKNOWN`           |

## Run locally (for iterating on the pages themselves)

```bash
cd auth-lab
pip install -r requirements.txt
uvicorn app:app --reload --port 8090
```

Open http://localhost:8090 — this is fine for eyeballing the HTML, but
**AgentCore Browser cannot reach localhost.** Before you can scan these
pages with the real agent, deploy the lab somewhere with a public HTTPS URL
(`../scripts/deploy_lab.sh` has a starting point — App Runner or a small
Lambda Function URL both work well here per Section 9 of the kickoff doc).

## Resetting between demo runs

`POST /reset` (or the button on `/`) puts Scenario C back to its initial
AT_RISK state — always hit this before recording/re-running the demo so the
red → green transition is repeatable.
