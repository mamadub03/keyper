# Keyper — local setup

The whole stack runs on your machine with one command. The only thing that
isn't local is **Amazon Bedrock AgentCore Browser** — it drives a real
browser from inside AWS, so the launcher opens a short-lived
[cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
tunnel to the local demo lab while it's running. Nothing is deployed; the
tunnel closes when you stop the app.

## Prerequisites (one-time)

| Need | Check |
|---|---|
| Python 3.12+ | `python --version` |
| Node.js 20+ | `node --version` |
| AWS CLI v2, authenticated | `aws sts get-caller-identity` |
| `cloudflared` | `cloudflared --version` — install: `winget install --id Cloudflare.cloudflared` (Windows) or your package manager |
| Bedrock access to **Claude Sonnet 4.5** in your region | see below |

**AWS credentials** are the only thing Keyper needs that you configure
yourself, and you do it once, outside the app: `aws configure` (or
`aws sso login`). Keyper reads them from the standard AWS credential chain —
there is no key field anywhere in the app.

**Bedrock model access:** the first time an AWS account uses an Anthropic
model you must submit a short use-case form. Go to the Bedrock console →
**Model catalog** → open **Claude Sonnet 4.5** → *Request model access* →
fill the form. Access is usually granted within a few minutes. (To point
Keyper at a different model instead, set `KEYPER_BEDROCK_MODEL_ID`.)

## Run it

```powershell
./run.ps1        # Windows
```

```bash
./run.sh         # macOS / Linux
```

That starts the auth lab, the tunnel, the API, and the web UI, wires them
together, and opens <http://localhost:5173>. The form comes up pre-filled
with the four demo scenarios — click **Test My Accounts**, then **Fix with
Keyper** on the at-risk one. `Ctrl+C` stops everything.

First run installs Python and web dependencies automatically (~1–2 min).

### Without the demo lab

```powershell
./run.ps1 -NoTunnel
```

```bash
./run.sh --no-tunnel
```

Skips the lab and tunnel; the form starts blank so you can point Keyper at
your own service URLs. (Those URLs still have to be reachable from AWS.)

## What it costs

Only Bedrock model calls and AgentCore Browser session-time, and only while
a scan is actually running:

- a scan: roughly **$0.15–0.35** in model tokens + ~1–2¢ browser time
- a fix (discover → act → re-test): about **1.5–2×** a scan
- idle: **$0** — nothing runs between scans

Set `KEYPER_DEBUG_METRICS=1` to print per-run token counts and an estimated
cost. A `$20/month` AWS Budgets alert is a good backstop.

## Deploying the agent to AgentCore Runtime (optional)

The local demo runs the agent in-process (`KEYPER_INVOKE_MODE=local`) and
needs no deployment. To also run it as a deployed AgentCore Runtime endpoint
(the "it's actually deployed" milestone):

```bash
bash scripts/deploy_agent.sh
```

This creates lasting AWS resources (an ECR image, an IAM execution role, a
CDK bootstrap stack, the Runtime) and costs a few dollars one-time for the
build plus pennies/month for image storage. The runtime itself is
consumption-billed like a local scan. After deploy, put the runtime ARN in
a `.env` at the repo root:

```ini
KEYPER_AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:...
KEYPER_AWS_REGION=us-west-2
KEYPER_INVOKE_MODE=runtime
```

The API then calls the deployed agent instead of running it in-process;
`KEYPER_INVOKE_MODE=local` switches back. The request/response shape is
identical either way.

Local smoke test of the Runtime entrypoint (no deploy):

```bash
python -m agent.runtime_entrypoint          # serves :8080
curl -s localhost:8080/ping                 # -> {"status":"Healthy",...}
```

## Tests

```bash
pytest tests/test_auth_lab.py -v     # zero AWS — lab logic only
```

The other test files under `tests/` are integration tests that need a
reachable lab (`KEYPER_LAB_URL`) and hit real AWS; they skip themselves
otherwise.
