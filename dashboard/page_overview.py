"""Overview page: KPI cards and charts."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from dashboard import api
from dashboard.common import call


def _bar(labels: list, values: list, title: str, horizontal: bool = False) -> go.Figure:
    if horizontal:
        fig = go.Figure(go.Bar(x=values, y=labels, orientation="h"))
        fig.update_yaxes(autorange="reversed")
    else:
        fig = go.Figure(go.Bar(x=labels, y=values))
    fig.update_layout(title=title, height=300, margin={"l": 10, "r": 10, "t": 40, "b": 10})
    return fig


def render() -> None:
    st.header("Overview")
    ok, k = call(api.get, "/owner/kpis")
    if not ok:
        return
    c = st.columns(4)
    c[0].metric("Interactions", k.get("interactions_count", 0))
    c[1].metric("Interested", k.get("interested_prospects", 0))
    c[2].metric("Paid", k.get("paid_prospects", 0))
    c[3].metric("Conversion", f"{k.get('conversion_rate', 0) * 100:.1f} %")
    c = st.columns(3)
    c[0].metric("Revenue (TND)", f"{k.get('simulated_revenue', 0):.2f}")
    sat = k.get("satisfaction_avg")
    c[1].metric("Satisfaction (1-5)", "n/a" if sat is None else f"{sat:.2f}")
    c[2].metric("Security alerts", k.get("security_alerts_count", 0))

    left, right = st.columns(2)
    pay = k.get("payments_by_status") or {}
    left.plotly_chart(
        _bar(list(pay), list(pay.values()), "Payments by status"), use_container_width=True
    )
    funnel = go.Figure(
        go.Funnel(
            y=["Interactions", "Interested", "Paid"],
            x=[
                k.get("interactions_count", 0),
                k.get("interested_prospects", 0),
                k.get("paid_prospects", 0),
            ],
        )
    )
    funnel.update_layout(
        title="Conversion funnel", height=300, margin={"l": 10, "r": 10, "t": 40, "b": 10}
    )
    right.plotly_chart(funnel, use_container_width=True)

    left, right = st.columns(2)
    obj = [o for o in (k.get("top_objections") or []) if isinstance(o, dict)]
    left.plotly_chart(
        _bar(
            [o.get("label", "?") for o in obj],
            [o.get("count", 0) for o in obj],
            "Top objections",
            True,
        ),
        use_container_width=True,
    )
    al = k.get("security_alerts_by_type") or {}
    right.plotly_chart(
        _bar(list(al), list(al.values()), "Alerts by type"), use_container_width=True
    )

    st.subheader("Latest recommendations")
    recs = k.get("latest_recommendations") or []
    if not recs:
        st.info("No recommendations yet. Run an analysis on the Insights page.")
    for r in recs:
        st.markdown(f"- **{r.get('title', '?')}**: {r.get('action', '')}")

    st.subheader("Narrative summary")
    if st.button("Generate narrative summary"):
        ok, n = call(api.get, "/owner/kpis/narrative")
        if ok:
            st.write(n.get("text", ""))
