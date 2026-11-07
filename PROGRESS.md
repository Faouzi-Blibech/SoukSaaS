# PROGRESS / HANDOFF

Single source of truth for where the project stands. Updated after every step.
Anyone continuing (Claude Code, OpenCode, a human): read `AGENTS.md`, then this file, then only the
spec sections you need. Last updated: 2026-11-08.

## 1. What we are building
SoukSaaS: a prototype "Autonomous FinTech Team" for the TechX ENIT x ENICarthage 14h hackathon
(brief: `Cahier_des_Charges_The_Autonomous_FinTech_Team_TechX.pdf`, local only, not in the repo).
Cooperating AI agents sell an AI training course end to end: product page + chat (Sales Agent),
simulated payment with human approval (Payment Agent), KPIs (Analytics), evidence-backed
recommendations and outreach drafts (Insights), all behind a security gateway with a hash-chained
audit log. Full technical spec: `IMPLEMENTATION_SPEC.md`. Internal contracts: `docs/API_CONTRACT.md`.

## 2. How to run (Windows, macOS, Linux)
```
uv sync                         # install
cp .env.example .env            # then set LLM_API_KEY (OpenAI) and OWNER_TOKEN; LLM_MODE=mock needs no key
uv run python tasks.py seed     # synthetic data into data/app.db
uv run python tasks.py test     # pytest
uv run python tasks.py run      # FastAPI on :8000 (available after step S4)
uv run python tasks.py dashboard  # Streamlit owner console
```
`make <target>` works too where make exists (it calls tasks.py).

## 3. Step status (each step = one stacked PR, merge in order)
| Step | Content | Status | PR |
|---|---|---|---|
| S0 | Scaffolding, models, schemas, seed, tasks.py | done | #1 |
| SD | ARCHITECTURE.md, SECURITY.md, attacks.jsonl, Jinja templates | done | #2 |
| S3 | Streamlit owner console (7 pages) vs owner API contract | done | #3 |
| SH | AGENTS.md + this file | done | #4 |
| S2 | `app/llm.py`, `services/qa.py`, `payments_sandbox.py`, `analytics.py`; seed Q&A from `generate_qa` (ids qa_price, qa_features, qa_schedule, qa_refund, qa_prerequisites, qa_certificate, qa_audience, qa_plans, qa_contact) | done | #5 |
| S1 | `app/audit.py`, `permissions.py`, `gateway/` (filters, classifier, fraud) | in progress | - |
| S3b | Futuristic dashboard redesign (three.js agent network, HUD theme, mock owner API in `tests/fixtures/`) | in progress | - |
| S4 | `orchestrator.py`, `agents/base.py`, `agents/sales.py`, `agents/payment.py`, `routers/public.py`, `routers/owner.py`, wire `main.py`, integration tests | blocked on S1+S2 | - |
| S5 | `agents/insights.py` (analyze + opportunities), `services/outreach.py`, owner endpoints for them | blocked on S4 | - |
| S6 | `scripts/run_evals.py`, `tests/evals/qa_questions.jsonl`, `/owner/simulate`, `make demo`, failure-injection tests, eval results into SECURITY.md | blocked on S4+S5 | - |
| S7 | README, pitch outline (`docs/PITCH.md`), revenue forecast bonus, final end-to-end browser check, review pass | blocked on S6 | - |

## 4. Next actions (in order)
1. Finish S1 and S2, verify, open their PRs.
2. S4: the core workflow. Must follow `docs/API_CONTRACT.md` sections 2-4 exactly (the dashboard and
   chat widget already call those shapes). Render `GET /` with `product=Product.model_dump()`.
3. S5, then S6, then S7 (see table).

## 5. Cahier (brief) coverage and gaps
Covered by the spec: 6 agent roles (Customer Intelligence + Business Strategy merged into the Insights
agent with 2 modes; Financial Analyst = deterministic analytics service; Security = gateway), all
section 4 dashboard KPIs, section 5 data rules (synthetic only, no card data, simulated payments,
documented limits), most section 6 bonuses (prompt-injection demo, fraud rules, human-in-the-loop,
live event feed, browser voice simulation).
Gaps added to the plan:
- Section 7 deliverable "Presentation du projet" (problem, solution, technical choices, value,
  security measures, future work): not in the spec -> S7 `docs/PITCH.md` outline.
- Section 6 bonus "ML forecast of sales/revenue": not in the spec -> S7, small linear trend on
  `analytics.revenue_over_time`, shown on the dashboard.
- Section 8 is missing from the brief itself (numbering jumps 7 -> 9). Ask the organizers.
Judging (sections 9-10): communication, originality, feasible architecture, AI/FinTech relevance,
security and trust, prototype quality, impact. The 3D agent-network dashboard targets originality.

## 6. Decisions
See `docs/DECISIONS.md`. Plus: PRs are stacked (`step/<n>-<name>`, each based on the previous step
branch) and never merged by the agent; the repo owner merges in order.

## 7. Known issues
- Q&A TF-IDF threshold 0.37 (`app/services/qa.py`), narrow margin: worst off-topic 0.34 vs weakest paraphrase 0.39. Embeddings path untested (optional extra).
- Dashboard `eval_results.json` shape fixed in API_CONTRACT.md section 5; S6 must write exactly that.
- Browser JS of the chat widget not yet exercised (done in S7 end-to-end check).
