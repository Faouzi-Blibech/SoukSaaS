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
| SH | AGENTS.md + this file | done | #4, #7 |
| S2 | `app/llm.py`, `services/qa.py`, `payments_sandbox.py`, `analytics.py`; seed Q&A ids qa_price, qa_features, qa_schedule, qa_refund, qa_prerequisites, qa_certificate, qa_audience, qa_plans, qa_contact | done | #6, #7 |
| S1 | `app/audit.py`, `permissions.py`, `gateway/` (filters, classifier, fraud) | done | #8 |
| S7a | README, `docs/PITCH.md` (FR), `analytics.forecast_revenue` | done | #9 |
| S6a | `scripts/run_evals.py`, `tests/evals/qa_questions.jsonl`, eval results in SECURITY.md | done | #10 |
| S5a | `app/services/insights.py`, `outreach.py` (logic only) | done | #11 |
| S3b | Futuristic dashboard (three.js agent network, HUD theme, `tests/fixtures/mock_owner_api.py`) | done | see PR list |
| S4 | Orchestrator, agents (base, sales, payment), public + owner routers, integration tests | done | see PR list |
| S2b | Q&A matcher fix (ambiguity guard, word+char scoring, richer variants) | done | see PR list |
| W | Wiring: `app/agents/insights.py` wrapper, owner endpoints insights/run, recommendations, drafts, mark_sent (dedupe drafts per lead), `/owner/simulate` (demo + attack), `python tasks.py demo`, dashboard actor-name check against real backend | next | - |
| F | Final: end-to-end browser check (product page chat + pay, dashboard on real backend), review pass, PITCH numbers | after W | - |

## 4. Next actions (in order)
1. W (wiring step above). Owner endpoints currently return 501 for insights/recommendations/drafts/simulate.
2. F (final checks).
3. Optional: held-out Q&A question set (current 100% is optimistic, see docs/SECURITY.md).

## Dev tips
- Dashboard without backend: `uv run uvicorn tests.fixtures.mock_owner_api:app --port 8001`, then
  `API_URL=http://127.0.0.1:8001 uv run streamlit run dashboard/app.py`.
- Delete `data/app.db` and reseed after model changes.

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
