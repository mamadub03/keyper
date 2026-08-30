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

See `keyper_engineering_kickoff.md` for the full product/engineering
source of truth this repo was built from, and `architecture/architecture.md`
for the system diagram.

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
├── api/               FastAPI BFF
├── web/                Vite + React + TS UI
├── auth-lab/          Controlled test scenarios (deploy this publicly)
├── scripts/           prereq check, deploy, reset
├── tests/              pytest — unit tests for the lab + integration tests for the agent
├── architecture/       system diagram
├── CLAUDE.md          briefing file for Claude Code sessions working in this repo
└── RUNBOOK.md         step-by-step commands to go from zero to a working demo
```

## Getting started

**Start with `RUNBOOK.md`** — it has the exact commands, in order, starting
with the AWS prerequisite check. Short version:

```bash
# 1. Confirm AWS/Bedrock/AgentCore access
bash scripts/prereq_check.sh

# 2. Install Python deps
pip install -e ".[dev]" --break-system-packages   # or inside a venv

# 3. Sanity-check the auth lab with zero AWS dependency
pip install -r auth-lab/requirements.txt --break-system-packages
uvicorn auth-lab.app:app --reload --port 8090 &
pytest tests/test_auth_lab.py -v

# 4. First real agent run, once the lab has a public URL (see scripts/deploy_lab.sh)
python -m agent.local_dev --identity student@g.school.edu --url <public lab url>/scenario-a

# 5. API + UI
uvicorn api.main:app --reload --port 8000 &
cd web && npm install && npm run dev
```

## License

MIT — see `LICENSE`.
