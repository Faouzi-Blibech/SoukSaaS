"""Orchestrator (spec 6.1): agent registry, envelope validation, permission check, timeout, retries, fallback.

`dispatch` never raises. Every agent-to-agent message (and each reply) is written to the audit log as an
`agent_message` event so the dashboard live feed shows the collaboration.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session

from app import audit
from app.agents.base import BaseAgent
from app.config import settings
from app.gateway import SecurityGateway
from app.schemas import AgentMessage, Ctx

log = logging.getLogger(__name__)

ORCHESTRATOR = "orchestrator"
DEFAULT_FALLBACK = {"reply": "Sorry, something went wrong. Please retry."}


class Orchestrator:
    def __init__(self, session: Session, *, timeout_s: float | None = None, retries: int | None = None,
                 gateway: SecurityGateway | None = None):
        self.session = session
        self.timeout_s = settings.orchestrator_timeout_s if timeout_s is None else timeout_s
        self.retries = settings.orchestrator_retries if retries is None else retries
        self.gateway = gateway or SecurityGateway(session)
        self.agents: dict[str, BaseAgent] = {}

    # ---- registry --------------------------------------------------------------------------
    def register(self, agent: BaseAgent) -> BaseAgent:
        agent.orchestrator = self
        self.agents[agent.name] = agent
        return agent

    # ---- audit helpers ---------------------------------------------------------------------
    def _log_message(self, msg: AgentMessage, *, reply: bool = False) -> None:
        audit.log_event(
            self.session, trace_id=msg.trace_id, actor=msg.sender, event_type="agent_message",
            payload={"sender": msg.sender, "recipient": msg.recipient, "type": msg.type,
                     "reply": reply, "message_id": msg.id, "payload": msg.payload},
        )

    def record(self, msg: AgentMessage) -> None:
        """Log a notification that has no handler (e.g. sales -> orchestrator `interest_recorded`)."""
        self._log_message(msg)

    def _error(self, msg: AgentMessage, reason: str, attempts: int, *, decision: str = "error") -> AgentMessage:
        audit.log_event(
            self.session, trace_id=msg.trace_id, actor=msg.recipient or ORCHESTRATOR, event_type="agent_error",
            decision=decision, reasons=[reason],
            payload={"sender": msg.sender, "recipient": msg.recipient, "type": msg.type, "attempts": attempts},
        )
        agent = self.agents.get(msg.recipient)
        payload = dict(agent.fallback_payload if agent else DEFAULT_FALLBACK)
        payload.update({"fallback": True, "error": reason})
        return AgentMessage(trace_id=msg.trace_id or "none", sender=msg.recipient or ORCHESTRATOR,
                            recipient=msg.sender or ORCHESTRATOR, type="agent_error", payload=payload)

    # ---- dispatch --------------------------------------------------------------------------
    def dispatch(self, msg: AgentMessage | dict[str, Any]) -> AgentMessage:
        """Deliver `msg` to its recipient and return the reply envelope (or a fallback). Never raises."""
        try:
            return self._dispatch(msg)
        except Exception as exc:  # last-resort guard: the workflow must not crash
            log.exception("orchestrator failure")
            base = msg if isinstance(msg, AgentMessage) else AgentMessage(
                trace_id="none", sender=ORCHESTRATOR, recipient=ORCHESTRATOR, type="unknown")
            try:
                return self._error(base, f"orchestrator:{type(exc).__name__}", 0)
            except Exception:  # noqa: BLE001  audit itself failing: still return something safe
                return AgentMessage(trace_id=base.trace_id, sender=ORCHESTRATOR, recipient=base.sender,
                                    type="agent_error", payload={**DEFAULT_FALLBACK, "fallback": True})

    def _dispatch(self, msg: AgentMessage | dict[str, Any]) -> AgentMessage:
        if not isinstance(msg, AgentMessage):
            try:
                msg = AgentMessage.model_validate(msg)
            except ValidationError:
                bad = AgentMessage(trace_id="none", sender=ORCHESTRATOR, recipient=ORCHESTRATOR, type="invalid")
                return self._error(bad, "invalid_envelope", 0, decision="block")
        agent = self.agents.get(msg.recipient)
        if agent is None:
            return self._error(msg, f"unknown_recipient:{msg.recipient}", 0, decision="block")
        if msg.sender != ORCHESTRATOR:
            # Same permission matrix as tool calls: message.send.<recipient> (denied -> audited + alert).
            ctx = Ctx(trace_id=msg.trace_id, actor=msg.sender)
            if self.gateway.check_tool_call(f"message.send.{msg.recipient}", {}, ctx).action != "allow":
                return self._error(msg, f"permission_denied:{msg.sender}->{msg.recipient}", 0, decision="block")
        self._log_message(msg)

        attempts = 1 + max(0, self.retries)
        last = "unknown"
        for attempt in range(1, attempts + 1):
            pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"agent-{agent.name}")
            try:
                result = pool.submit(agent.handle, msg).result(timeout=self.timeout_s)
            except FutureTimeout:
                last = f"timeout>{self.timeout_s}s"
            except Exception as exc:  # noqa: BLE001  agent bug: retry, then fall back
                last = f"{type(exc).__name__}"
            else:
                reply = self._as_message(msg, result)
                self._log_message(reply, reply=True)
                return reply
            finally:
                pool.shutdown(wait=False)  # a timed-out worker is abandoned, not joined
            log.warning("agent %s attempt %d/%d failed: %s", agent.name, attempt, attempts, last)
        return self._error(msg, last, attempts)

    @staticmethod
    def _as_message(msg: AgentMessage, result: AgentMessage | dict) -> AgentMessage:
        if isinstance(result, AgentMessage):
            return result
        return AgentMessage(trace_id=msg.trace_id, sender=msg.recipient, recipient=msg.sender,
                            type=f"{msg.type}_result", payload=dict(result))


def build_orchestrator(session: Session, *, timeout_s: float | None = None,
                       retries: int | None = None) -> Orchestrator:
    """Per-request orchestrator with the core agents registered."""
    from app.agents.payment import PaymentAgent
    from app.agents.sales import SalesAgent

    orch = Orchestrator(session, timeout_s=timeout_s, retries=retries)
    orch.register(SalesAgent(session, orch.gateway))
    orch.register(PaymentAgent(session, orch.gateway))
    return orch
