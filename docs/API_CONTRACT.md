# Internal contracts

Shared by parallel work streams. Change only with the orchestrator's agreement.

## 1. LLM client (`app/llm.py`)

```python
class LLMError(Exception): ...

def chat(system: str, user: str, *, task: str, mock: Callable[[], str]) -> str
def chat_json(system: str, user: str, schema: type[T], *, task: str,
              mock: Callable[[], dict | T]) -> T          # T is a Pydantic model
call_count: dict[str, int]                                # live+mock calls per task; reset_counts()
```

- `LLM_MODE=mock`: no network. Returns `mock()` (validated through `schema` for `chat_json`).
  Each caller owns its own deterministic mock, so mocks can reflect the real input.
- `LLM_MODE=live`: LiteLLM `completion(model=LLM_MODEL, api_key=LLM_API_KEY or OPENAI_API_KEY)`,
  `response_format={"type": "json_object"}` for `chat_json`, output validated with the schema.
  One retry on invalid output, then `LLMError`. Timeout 20 s. Never log the key.
- Task names: `sales_fallback`, `interest`, `qa_generate`, `injection_classifier`,
  `insights_analyze`, `insights_opportunities`, `kpi_narrative`.

## 2. Owner HTTP API (header `X-Owner-Token`, 401 if wrong)

All responses JSON. Timestamps ISO 8601.

| Method + path | Response |
|---|---|
| `GET /owner/kpis` | `KPIs` schema (`app/schemas.py`) |
| `GET /owner/kpis/narrative` | `{"text": str}` |
| `GET /owner/audit?limit=100` | `[{id, ts, trace_id, actor, event_type, decision, reasons, payload}]` newest first (`payload` is the redacted payload) |
| `GET /owner/audit/verify` | `{"ok": bool, "checked": int, "first_bad_id": str or null}` |
| `GET /owner/alerts?limit=100` | `[{id, ts, trace_id, alert_type, severity, detail}]` newest first |
| `GET /owner/qa` | `[{id, question, variants, answer, status, hits}]` |
| `POST /owner/qa/generate` | list of created draft entries |
| `POST /owner/qa/{id}/approve` / `.../reject` | the entry |
| `PUT /owner/qa/{id}` body `{question, answer, variants}` | the entry (status back to draft) |
| `GET /owner/approvals?status=pending` | `[{id, kind, ref_id, reasons, status, created_at, payment: {id, prospect_id, plan_id, amount, currency, risk_score, status} or null}]` |
| `POST /owner/approvals/{id}/approve` / `.../reject` | `{approval, payment}` (payment after the sandbox call, or null) |
| `POST /owner/insights/run?mode=analyze` | `InsightsAnalysis` |
| `POST /owner/insights/run?mode=opportunities` | `[{draft_id, lead_id, first_name, score, reason, draft_message}]` |
| `GET /owner/recommendations` | `[{id, title, action, rationale, evidence, impact, effort, created_at}]` |
| `GET /owner/drafts` | `[{id, lead_id, first_name, interest, score, reason, draft_message, status, created_at}]` |
| `POST /owner/drafts/{id}/mark_sent` | the draft |
| `GET /owner/evals` | contents of `data/eval_results.json`, or `{}` |
| `POST /owner/simulate?scenario=demo` or `attack` | `{"steps": [{"step": str, "result": dict}]}` |

## 3. Public HTTP API

| Method + path | Body | Response |
|---|---|---|
| `GET /` | | product page HTML |
| `POST /api/chat` | `ChatRequest` | `{reply, source, interest_level, blocked: bool, trace_id}` |
| `POST /api/pay` | `PayRequest` (extra fields -> 422) | `{status, message, payment_id, trace_id}` |
| `POST /api/rating` | `RatingRequest` | `{ok: true}` |

## 4. Template rendering
`GET /` renders `product_page.html` with `product=Product.model_dump()` (a dict; `policies` must be iterable with `.items()`).
