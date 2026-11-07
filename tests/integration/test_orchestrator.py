import time
from typing import Any, ClassVar

from sqlmodel import select

from app import audit
from app.agents.base import BaseAgent
from app.models import AuditEvent
from app.orchestrator import Orchestrator
from app.schemas import AgentMessage


class Slow(BaseAgent):
    fallback_payload: ClassVar[dict[str, Any]] = {"reply": "please retry", "source": "system"}

    def __init__(self, session, sleep_s, fail_first=0):
        super().__init__("sales", ("qa.search",), session)
        self.calls, self.sleep_s, self.fail_first = 0, sleep_s, fail_first

    def handle(self, msg):
        self.calls += 1
        if self.calls <= self.fail_first:
            raise RuntimeError("boom")
        time.sleep(self.sleep_s)
        return {"reply": "ok"}


def msg():
    return AgentMessage(trace_id="t1", sender="orchestrator", recipient="sales", type="chat_turn")


def types(db):
    db.expire_all()
    return [e.event_type for e in db.exec(select(AuditEvent).order_by(AuditEvent.seq))]


def test_timeout_retried_then_fallback_with_agent_error(db):
    orch = Orchestrator(db, timeout_s=0.05, retries=2)
    agent = orch.register(Slow(db, sleep_s=0.4))
    reply = orch.dispatch(msg())  # must not raise
    assert reply.type == "agent_error" and reply.payload["fallback"] is True
    assert reply.payload["reply"] == "please retry"
    time.sleep(0.6)  # let abandoned workers finish before touching the shared connection
    assert agent.calls == 3  # first try + 2 retries
    err = [e for e in db.exec(select(AuditEvent)) if e.event_type == "agent_error"]
    assert len(err) == 1 and err[0].payload["attempts"] == 3
    assert audit.verify_chain(db)["ok"]


def test_exception_then_success_on_retry(db):
    orch = Orchestrator(db, timeout_s=1, retries=2)
    agent = orch.register(Slow(db, sleep_s=0, fail_first=1))
    reply = orch.dispatch(msg())
    assert reply.payload == {"reply": "ok"} and reply.type == "chat_turn_result" and agent.calls == 2
    assert "agent_error" not in types(db)
    assert types(db).count("agent_message") == 2  # request + reply


def test_invalid_envelope_and_unknown_recipient_never_raise(db):
    orch = Orchestrator(db, timeout_s=0.1, retries=0)
    assert orch.dispatch({"garbage": True}).type == "agent_error"
    unknown = AgentMessage(trace_id="t", sender="orchestrator", recipient="nobody", type="x")
    assert orch.dispatch(unknown).type == "agent_error"
    assert types(db).count("agent_error") == 2
