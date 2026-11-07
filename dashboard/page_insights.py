"""Insights page: analysis, opportunities, outreach drafts."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.common import call


def _analysis(res: dict) -> None:
    st.subheader("Needs")
    for n in res.get("needs", []):
        st.markdown(f"- {n.get('label')} ({n.get('count')})")
    st.subheader("Objections")
    for o in res.get("objections", []):
        ids = ", ".join(o.get("example_interaction_ids") or [])
        st.markdown(f"- {o.get('label')} ({o.get('count')}) examples: {ids or 'none'}")
    st.subheader("Recommendations")
    for r in res.get("recommendations", []):
        ev = r.get("evidence") or {}
        with st.container(border=True):
            st.markdown(
                f"**{r.get('title')}** (impact: {r.get('impact')}, effort: {r.get('effort')})"
            )
            st.write(r.get("action", ""))
            st.caption(r.get("rationale", ""))
            st.caption(
                f"Evidence KPI: {ev.get('kpi')} | interactions: {', '.join(ev.get('interaction_ids') or []) or 'none'}"
            )


def _drafts() -> None:
    st.subheader("Outreach drafts")
    ok, drafts = call(api.get, "/owner/drafts")
    if not ok:
        return
    if not drafts:
        st.info("No drafts yet.")
    for d in drafts:
        with st.container(border=True):
            st.markdown(
                f"**{d.get('first_name')}** | interest: {d.get('interest')} | score: {d.get('score')} | status: {d.get('status')}"
            )
            st.caption(d.get("reason", ""))
            st.code(d.get("draft_message", ""), language=None)
            if d.get("status") != "sent_manually" and st.button(
                "Mark as sent manually", key=f"sent_{d['id']}"
            ):
                ok, _res = call(api.post, f"/owner/drafts/{d['id']}/mark_sent")
                if ok:
                    st.rerun()


def render() -> None:
    st.header("Insights")
    st.info(
        "Nothing is ever sent by the system. Copy a draft and send it yourself, then mark it as sent."
    )
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button("Run analysis"):
        ok, res = call(api.post, "/owner/insights/run", mode="analyze")
        if ok:
            st.session_state["analysis"] = res
    if c2.button("Find opportunities"):
        ok, res = call(api.post, "/owner/insights/run", mode="opportunities")
        if ok:
            st.success(f"{len(res)} opportunity drafts created.")
    if "analysis" in st.session_state:
        _analysis(st.session_state["analysis"])
    _drafts()
