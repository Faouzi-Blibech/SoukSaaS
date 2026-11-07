"""Deterministic KPIs (spec 6.4). No LLM in get_kpis; narrative_summary is display-only."""
from collections import Counter, defaultdict

from sqlmodel import Session, select

from app.llm import chat
from app.models import Interaction, Payment, Recommendation, SecurityAlert
from app.schemas import KPIs, Objection

INTERESTED_LEVELS = ("medium", "high")
TOP_OBJECTIONS = 5
EXAMPLES_PER_OBJECTION = 3


def _prospect_interactions(session: Session) -> list[Interaction]:
    stmt = select(Interaction).where(Interaction.role == "prospect").order_by(Interaction.ts, Interaction.id)
    return list(session.exec(stmt))


def _who(i: Interaction) -> str:
    """Identity of a prospect: prospect_id when known, else the anonymous session."""
    return i.prospect_id or f"session:{i.session_id}"


def _interested_ids(rows: list[Interaction]) -> set[str]:
    """Interested = distinct prospects (or anonymous sessions) with >=1 prospect message
    whose interest_level is medium or high."""
    return {_who(i) for i in rows if i.interest_level in INTERESTED_LEVELS}


def _paid_ids(session: Session) -> set[str]:
    return {p.prospect_id for p in session.exec(select(Payment).where(Payment.status == "succeeded"))}


def get_kpis(session: Session) -> KPIs:
    rows = _prospect_interactions(session)
    interested = _interested_ids(rows)
    paid = _paid_ids(session)
    conversion = len(paid) / len(interested) if interested else 0.0

    obj_ids: dict[str, list[str]] = defaultdict(list)
    for i in rows:
        if i.objection:
            obj_ids[i.objection].append(i.id)
    ranked = sorted(obj_ids.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:TOP_OBJECTIONS]
    objections = [Objection(label=k, count=len(v), example_interaction_ids=v[:EXAMPLES_PER_OBJECTION])
                  for k, v in ranked]

    payments = list(session.exec(select(Payment)))
    by_status = dict(Counter(p.status for p in payments))
    revenue = sum(p.amount for p in payments if p.status == "succeeded")

    ratings = [i.rating for i in session.exec(select(Interaction)) if i.rating is not None]
    sat = sum(ratings) / len(ratings) if ratings else None

    alerts = list(session.exec(select(SecurityAlert)))
    recs = session.exec(select(Recommendation).order_by(Recommendation.created_at.desc(),
                                                        Recommendation.id).limit(5))
    return KPIs(
        interactions_count=len(rows),
        interested_prospects=len(interested),
        paid_prospects=len(paid),
        conversion_rate=conversion,
        top_objections=objections,
        payments_by_status=by_status,
        simulated_revenue=float(revenue),
        satisfaction_avg=sat,
        security_alerts_count=len(alerts),
        security_alerts_by_type=dict(Counter(a.alert_type for a in alerts)),
        latest_recommendations=[
            {"id": r.id, "title": r.title, "action": r.action, "rationale": r.rationale,
             "evidence": r.evidence, "impact": r.impact, "effort": r.effort,
             "created_at": r.created_at.isoformat()} for r in recs],
    )


def revenue_over_time(session: Session) -> list[dict]:
    """Succeeded revenue per day, ascending: [{date: 'YYYY-MM-DD', revenue: float}]."""
    per_day: dict[str, float] = defaultdict(float)
    for p in session.exec(select(Payment).where(Payment.status == "succeeded")):
        per_day[p.created_at.date().isoformat()] += p.amount
    return [{"date": d, "revenue": float(per_day[d])} for d in sorted(per_day)]


def funnel(session: Session) -> dict[str, int]:
    rows = _prospect_interactions(session)
    return {
        "interactions": len(rows),
        "interested": len(_interested_ids(rows)),
        "payment_attempts": len({p.prospect_id for p in session.exec(select(Payment))}),
        "paid": len(_paid_ids(session)),
    }


def narrative_summary(kpis: KPIs) -> str:
    def mock() -> str:
        top = kpis.top_objections[0] if kpis.top_objections else None
        label = top.label if isinstance(top, Objection) else (top or {}).get("label")
        obj = f"The most common objection is {label}." if label else "No objections were recorded."
        return (f"There were {kpis.interactions_count} prospect messages, with "
                f"{kpis.interested_prospects} interested prospects and {kpis.paid_prospects} paid "
                f"(conversion {kpis.conversion_rate:.0%}). {obj} Simulated revenue is "
                f"{kpis.simulated_revenue:g} with {kpis.security_alerts_count} security alerts.")

    return chat("Write exactly 3 sentences summarising these KPIs for a business owner. Use only the numbers given.",
                kpis.model_dump_json(), task="kpi_narrative", mock=mock)
