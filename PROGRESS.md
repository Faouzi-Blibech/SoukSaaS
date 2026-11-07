# PROGRESS

Spec: `IMPLEMENTATION_SPEC.md`. Repo: github.com/Faouzi-Blibech/SoukSaaS (origin/main).

## Steps (dependency graph; each step = one stacked PR, branch `step/<n>-<name>`)
- S0 scaffolding + shared models/schemas - IN PROGRESS
- SD docs (ARCHITECTURE, SECURITY), attacks.jsonl, Jinja templates - IN PROGRESS (no deps)
- S1 gateway/audit/permissions/fraud/classifier - needs S0
- S2 llm.py + qa + payments_sandbox + analytics services - needs S0
- S3 Streamlit dashboard against owner API contract (spec 8.2) - needs S0
- S4 orchestrator, agents/base, sales + payment agents, public + owner routers, integration tests - needs S1, S2
- S5 insights agent + outreach - needs S4
- S6 run_evals, qa_questions.jsonl, simulator, demo, README - needs S4, S5
- Final: review pass on combined result

## Decisions
See `docs/DECISIONS.md`. Owner asked (2026-11-08): push every step as a PR, stacked in completion order. PRs are not merged by Claude.

## Known issues
- none yet
