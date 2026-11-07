from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.config import settings
from app.models import Interaction, Payment, Recommendation, SecurityAlert
from app.services import analytics


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "mock")
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        yield s


def _i(id, role="prospect", pid=None, sid="s", level="none", obj=None, rating=None):
    return Interaction(id=id, session_id=sid, prospect_id=pid, role=role, text="t",
                       interest_level=level, objection=obj, rating=rating,
                       ts=datetime(2026, 1, 1, 10, 0, int(id[1:]) if id[1:].isdigit() else 0))


def _pay(id, pid, status, amount, day):
    return Payment(id=id, prospect_id=pid, plan_id="std", amount=amount, status=status,
                   created_at=datetime(2026, 1, day, 12))


@pytest.fixture
def data(session):
    session.add_all([
        _i("i1", pid="A", sid="sa", level="high", obj="price"),
        _i("i2", pid="A", sid="sa", level="medium", obj="price"),   # same prospect, counted once
        _i("i3", pid="B", sid="sb", level="medium", obj="schedule"),
        _i("i4", pid=None, sid="anon", level="high", obj="price"),   # anonymous session
        _i("i5", pid="C", sid="sc", level="low", obj="trust"),
        _i("i6", role="agent", pid="A", sid="sa", rating=5),
        _i("i7", pid="B", sid="sb", level="none", rating=2),
        _pay("p1", "A", "succeeded", 250, 1),
        _pay("p2", "A", "succeeded", 450, 1),
        _pay("p3", "B", "declined", 250, 2),
        _pay("p4", "C", "held_for_approval", 450, 3),
        _pay("p5", "B", "succeeded", 250, 3),
        SecurityAlert(id="a1", alert_type="injection"),
        SecurityAlert(id="a2", alert_type="injection"),
        SecurityAlert(id="a3", alert_type="fraud"),
        Recommendation(id="r1", title="old", action="a", rationale="r", created_at=datetime(2026, 1, 1)),
        Recommendation(id="r2", title="new", action="a", rationale="r", created_at=datetime(2026, 1, 5)),
    ])
    session.commit()


def test_exact_kpis(session, data):
    k = analytics.get_kpis(session)
    assert k.interactions_count == 6  # prospect-role only
    assert k.interested_prospects == 3  # A, B, anon (C is low)
    assert k.paid_prospects == 2  # A, B
    assert k.conversion_rate == pytest.approx(2 / 3)
    top = k.top_objections
    assert [(o.label, o.count) for o in top] == [("price", 3), ("schedule", 1), ("trust", 1)]
    assert top[0].example_interaction_ids == ["i1", "i2", "i4"]
    assert k.payments_by_status == {"succeeded": 3, "declined": 1, "held_for_approval": 1}
    assert k.simulated_revenue == 950.0
    assert k.satisfaction_avg == 3.5
    assert k.security_alerts_count == 3
    assert k.security_alerts_by_type == {"injection": 2, "fraud": 1}
    assert [r["id"] for r in k.latest_recommendations] == ["r2", "r1"]


def test_empty_db_is_safe(session):
    k = analytics.get_kpis(session)
    assert k.conversion_rate == 0.0 and k.satisfaction_avg is None and k.simulated_revenue == 0.0


def test_revenue_and_funnel(session, data):
    assert analytics.revenue_over_time(session) == [
        {"date": "2026-01-01", "revenue": 700.0}, {"date": "2026-01-03", "revenue": 250.0}]
    assert analytics.funnel(session) == {"interactions": 6, "interested": 3,
                                         "payment_attempts": 3, "paid": 2}


def test_narrative_mock_is_deterministic(session, data):
    k = analytics.get_kpis(session)
    text = analytics.narrative_summary(k)
    assert "3 interested" in text and "price" in text and text == analytics.narrative_summary(k)
