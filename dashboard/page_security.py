"""Security and evals page, plus the simulator page."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import api
from dashboard.common import call


def _pct(v) -> str:
    return f"{v * 100:.0f} %" if isinstance(v, int | float) and v <= 1 else str(v)


def _evals(ev: dict) -> None:
    st.subheader("Evaluation results")
    if not ev:
        st.info("No eval run yet.")
        return
    qa = ev.get("qa") if isinstance(ev.get("qa"), dict) else ev
    atk = ev.get("attacks") if isinstance(ev.get("attacks"), dict) else ev
    c = st.columns(3)
    c[0].metric("Q&A accuracy", _pct(qa.get("accuracy", qa.get("qa_accuracy", "n/a"))))
    c[1].metric("Refusal rate", _pct(qa.get("refusal_rate", qa.get("correct_refusal_rate", "n/a"))))
    blocked, total = atk.get("blocked"), atk.get("total", atk.get("n"))
    c[2].metric("Attacks blocked", f"{blocked}/{total}" if blocked is not None else "n/a")
    details = (
        atk.get("details")
        or atk.get("results")
        or (ev.get("attacks") if isinstance(ev.get("attacks"), list) else None)
    )
    if details:
        st.dataframe(pd.DataFrame(details), use_container_width=True)
    with st.expander("Raw eval JSON"):
        st.json(ev)


def render() -> None:
    st.header("Security and evals")
    ok, ver = call(api.get, "/owner/audit/verify")
    if ok:
        if ver.get("ok"):
            st.success(f"Log integrity: OK ({ver.get('checked')} events checked)")
        else:
            st.error(f"Log integrity: TAMPERED at {ver.get('first_bad_id')}")
    ok, alerts = call(api.get, "/owner/alerts", limit=100)
    if ok:
        counts: dict[str, int] = {}
        for a in alerts:
            counts[a.get("alert_type", "?")] = counts.get(a.get("alert_type", "?"), 0) + 1
        fig = go.Figure(go.Bar(x=list(counts), y=list(counts.values())))
        fig.update_layout(
            title="Alerts by type", height=300, margin={"l": 10, "r": 10, "t": 40, "b": 10}
        )
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Latest alerts")
        if alerts:
            st.dataframe(
                pd.DataFrame(alerts).drop(columns=["id"], errors="ignore"), use_container_width=True
            )
        else:
            st.info("No alerts.")
    ok, ev = call(api.get, "/owner/evals")
    if ok:
        _evals(ev)


def render_simulator() -> None:
    st.header("Simulator")
    st.caption("Runs a scripted scenario against the live backend.")
    c1, c2, _ = st.columns([1, 1, 3])
    for col, scenario, label in (
        (c1, "demo", "Run demo scenario"),
        (c2, "attack", "Run attack scenario"),
    ):
        if col.button(label):
            ok, res = call(api.post, "/owner/simulate", scenario=scenario)
            if ok:
                st.session_state["sim"] = (scenario, res)
    if "sim" in st.session_state:
        scenario, res = st.session_state["sim"]
        st.subheader(f"Steps ({scenario})")
        for i, s in enumerate(res.get("steps", []), 1):
            with st.expander(f"{i}. {s.get('step')}", expanded=True):
                st.json(s.get("result"))
