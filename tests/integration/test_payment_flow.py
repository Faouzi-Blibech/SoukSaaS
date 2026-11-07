import pytest
from sqlmodel import select

from app import audit
from app.models import ApprovalRequest, AuditEvent, Payment


def pay(client, plan="std", token="tok_success", sid="pay1"):
    r = client.post("/api/pay", json={"session_id": sid, "plan_id": plan, "test_token": token})
    assert r.status_code == 200, r.text
    return r.json()


def kpis(client, owner):
    return client.get("/owner/kpis", headers=owner).json()


def event_types(db):
    db.expire_all()
    return [e.event_type for e in db.exec(select(AuditEvent).order_by(AuditEvent.seq))]


@pytest.mark.parametrize("token, status", [
    ("tok_success", "succeeded"),
    ("tok_declined", "declined"),
    ("tok_pending", "pending"),
    ("tok_whatever", "declined"),  # unknown but well-formed token: sandbox says invalid_token
])
def test_standard_plan_outcomes(client, owner, db, token, status):
    before = kpis(client, owner)
    out = pay(client, token=token)
    assert out["status"] == status and out["payment_id"] and out["trace_id"]
    after = kpis(client, owner)
    assert after["payments_by_status"].get(status, 0) == before["payments_by_status"].get(status, 0) + 1
    expected = 250.0 if status == "succeeded" else 0.0
    assert after["simulated_revenue"] == before["simulated_revenue"] + expected
    assert "payment_created" in event_types(db)


def test_amount_comes_from_product_not_client(client, db):
    out = pay(client, plan="std")
    db.expire_all()
    assert db.get(Payment, out["payment_id"]).amount == 250.0


@pytest.mark.parametrize("extra", [{"amount": 1}, {"card_number": "4242424242424242"}, {"cvv": "123"}])
def test_extra_fields_rejected_with_422(client, extra):
    r = client.post("/api/pay", json={"session_id": "x", "plan_id": "std", "test_token": "tok_success", **extra})
    assert r.status_code == 422


def test_unknown_plan_and_malformed_token_rejected(client, db):
    assert pay(client, plan="platinum")["status"] == "rejected"
    out = pay(client, token="4242 4242 4242 4242")
    assert out["status"] == "rejected"
    assert "payment_rejected" in event_types(db)
    assert "4242 4242 4242 4242" not in str([e.payload for e in db.exec(select(AuditEvent))])


def test_pro_plan_held_then_approved_by_owner(client, owner, db):
    before = kpis(client, owner)
    out = pay(client, plan="pro", sid="big1")
    assert out["status"] == "held_for_approval"
    assert kpis(client, owner)["simulated_revenue"] == before["simulated_revenue"]  # nothing charged yet

    pending = client.get("/owner/approvals?status=pending", headers=owner).json()
    item = next(a for a in pending if a["ref_id"] == out["payment_id"])
    assert item["kind"] == "payment" and "amount_over_threshold" in item["reasons"]
    assert item["payment"]["amount"] == 450.0 and item["payment"]["status"] == "held_for_approval"

    res = client.post(f"/owner/approvals/{item['id']}/approve", headers=owner)
    assert res.status_code == 200
    body = res.json()
    assert body["approval"]["status"] == "approved" and body["payment"]["status"] == "succeeded"
    assert kpis(client, owner)["simulated_revenue"] == before["simulated_revenue"] + 450.0
    types = event_types(db)
    assert "payment_held" in types and "payment_approved" in types
    assert client.post(f"/owner/approvals/{item['id']}/approve", headers=owner).status_code == 409
    db.expire_all()
    assert audit.verify_chain(db)["ok"]


def test_held_payment_rejected_by_owner(client, owner, db):
    out = pay(client, plan="pro", sid="big2")
    item = next(a for a in client.get("/owner/approvals", headers=owner).json() if a["ref_id"] == out["payment_id"])
    body = client.post(f"/owner/approvals/{item['id']}/reject", headers=owner).json()
    assert body["approval"]["status"] == "rejected" and body["payment"]["status"] == "rejected"
    assert kpis(client, owner)["simulated_revenue"] == 0.0
    assert "payment_rejected" in event_types(db)
    assert not [a for a in client.get("/owner/approvals", headers=owner).json() if a["id"] == item["id"]]


def test_burst_of_attempts_is_held(client, owner):
    statuses = [pay(client, token="tok_declined", sid="burst")["status"] for _ in range(5)]
    assert statuses[:2] == ["declined"] * 2  # two declines, then the next attempt trips the fraud rules
    assert statuses[2] == "held_for_approval"
    assert any(a["kind"] == "payment" for a in client.get("/owner/approvals", headers=owner).json())


def test_approval_unknown_id_404(client, owner):
    assert client.post("/owner/approvals/nope/approve", headers=owner).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-Owner-Token": "wrong"}])
@pytest.mark.parametrize("path", ["/owner/kpis", "/owner/audit", "/owner/approvals", "/owner/qa"])
def test_owner_requires_token(client, headers, path):
    assert client.get(path, headers=headers).status_code == 401
    assert client.post("/owner/approvals/x/approve", headers=headers).status_code == 401


def test_owner_endpoints_shapes(client, owner):
    pay(client)
    audit_rows = client.get("/owner/audit?limit=3", headers=owner).json()
    assert len(audit_rows) == 3 and set(audit_rows[0]) == {
        "id", "ts", "trace_id", "actor", "event_type", "decision", "reasons", "payload"}
    assert audit_rows[0]["ts"] >= audit_rows[-1]["ts"]
    assert client.get("/owner/audit/verify", headers=owner).json()["ok"] is True
    assert client.get("/owner/alerts", headers=owner).status_code == 200
    assert client.get("/owner/evals", headers=owner).status_code == 200


def test_qa_moderation_flow(client, owner, db):
    gen = client.post("/owner/qa/generate", headers=owner).json()
    assert gen and all(e["status"] == "draft" for e in gen)
    eid = gen[0]["id"]
    assert client.post(f"/owner/qa/{eid}/approve", headers=owner).json()["status"] == "approved"
    assert "qa_approved" in event_types(db)
    edited = client.put(f"/owner/qa/{eid}", headers=owner,
                        json={"question": "q?", "answer": "a", "variants": ["v"]}).json()
    assert edited["status"] == "draft" and edited["question"] == "q?"
    assert client.post(f"/owner/qa/{eid}/reject", headers=owner).json()["status"] == "rejected"
    assert client.post("/owner/qa/missing/approve", headers=owner).status_code == 404


def test_home_page_renders_product(client):
    r = client.get("/")
    assert r.status_code == 200 and "AI Foundations Bootcamp" in r.text


def test_escalation_approvals_have_no_payment(client, owner, db):
    db.add(ApprovalRequest(kind="escalation", ref_id="i1", reasons=["classifier_unavailable"]))
    db.commit()
    item = client.get("/owner/approvals", headers=owner).json()[0]
    assert item["kind"] == "escalation" and item["payment"] is None
    approved = client.post(f"/owner/approvals/{item['id']}/approve", headers=owner).json()
    assert approved["payment"] is None and approved["approval"]["status"] == "approved"
