# Keyper

**Disaster-recovery testing for your digital identity.**

Keyper uses an AI agent to test whether you can still access and recover
your accounts if your school or work identity disappears, then optionally
helps you fix the accounts that are at risk.

Built for the [Agents for Humans Hackathon](https://agentsforhumans.devpost.com/)
— 🏠 Everyday Agents track.

## The problem

Students and employees sign into third-party services (Notion, Figma,
Overleaf, dev tools, SaaS...) using an institution-controlled identity —
`student@g.school.edu`, a managed Google Workspace account, Microsoft
Entra, institutional SSO. That identity can disappear after graduation,
termination, or an org policy change. A user can look "safe" today while
quietly depending on an identity they don't control — including for
**account recovery**, which people forget to check.

## What Keyper does

1. You give it your institutional identity (+ known aliases) and 2-4
   service URLs.
2. A single, site-agnostic Strands agent — using a real, AWS-managed
   browser (AgentCore Browser) — investigates each service exactly like a
   careful human would: no per-site scripts, no hard-coded selectors.
3. It assumes your institutional identity is gone and asks two questions
   per service: can you still **authenticate**, and can you still
   **recover** the account?
4. You get an evidence-backed result: 🟢 SAFE, 🔴 AT RISK, or 🟡 UNKNOWN.
   A false SAFE is treated as worse than an honest UNKNOWN.
5. For anything AT RISK, you can click **Fix with Keyper**. The agent
   discovers whatever independent-access option that specific service
   actually offers, explains it, and — only after you approve — performs
   the non-secret setup steps. The moment a password, MFA code, OTP,
   recovery code, or security key is needed, it stops and hands the
   browser to you.
6. Once you complete that step, the agent re-tests from a fresh context
   (no institutional SSO) and the card flips 🔴 → 🟢.

See `architecture/architecture.md` for the system diagram.

## Stack

- **Agent framework:** [AWS Strands Agents SDK](https://strandsagents.com/) (Python)
- **Model provider:** Amazon Bedrock (Claude Sonnet)
- **Browser layer:** Amazon Bedrock AgentCore Browser
- **Agent hosting:** Amazon Bedrock AgentCore Runtime
- **API:** FastAPI
- **UI:** Vite + React + TypeScript
- **Test lab:** a small FastAPI app serving 4 differently-structured mock
  "account settings" pages, so the agent is provably reasoning over the
  page rather than pattern-matching

## Repo layout

```
keyper/
├── agent/            Strands agent, prompts, tools, schemas, Runtime entrypoint
├── api/              FastAPI BFF
├── web/              Vite + React + TS UI
├── auth-lab/         Controlled test scenarios (run locally; see below)
├── scripts/          prereq check, deploy, reset
├── tests/            pytest — unit tests for the lab + integration tests for the agent
└── architecture/     system diagram
```

## Getting started

Everything runs locally. The one piece that isn't on your machine is
Amazon Bedrock AgentCore Browser — it navigates from an AWS-managed
environment, so the target page has to be reachable from the internet. The
auth lab still runs locally; a short-lived tunnel exposes it just for the
duration of a run.

```bash
# 1. Confirm AWS / Bedrock / AgentCore access
bash scripts/prereq_check.sh

# 2. Install Python deps (use a venv if this is a shared machine)
pip install -e ".[dev]"

# 3. Sanity-check the auth lab with zero AWS dependency
uvicorn app:app --app-dir auth-lab --reload --port 8090 &
pytest tests/test_auth_lab.py -v

# 4. Expose the local lab, then do the first real agent run
#    (any tunnel works; cloudflared quick tunnels need no account)
cloudflared tunnel --url http://localhost:8090        # prints https://<name>.trycloudflare.com
export KEYPER_LAB_URL=https://<name>.trycloudflare.com
python -m agent.local_dev --identity student@g.school.edu --url "$KEYPER_LAB_URL/scenario-a"

# 5. API + UI
uvicorn api.main:app --reload --port 8000 &
cd web && npm install && npm run dev
```

A step-by-step local demo walkthrough lives in `SETUP.md`.

## License

MIT — see `LICENSE`.
