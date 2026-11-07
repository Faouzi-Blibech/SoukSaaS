"""Live feed page: newest audit events, refreshed every 5 s via st.fragment."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard import api
from dashboard.common import call, fmt_reasons

_FLAGGED = {"block", "escalate"}


def _color(row: pd.Series) -> list[str]:
    bad = str(row.get("decision")) in _FLAGGED
    return ["background-color: #ffd6d6" if bad else ""] * len(row)


@st.fragment(run_every=5)
def _feed() -> None:
    ok, events = call(api.get, "/owner/audit", limit=100)
    if not ok:
        return
    if not events:
        st.info("No audit events yet.")
        return
    rows = [
        {
            "ts": e.get("ts"),
            "actor": e.get("actor"),
            "event_type": e.get("event_type"),
            "decision": e.get("decision"),
            "reasons": fmt_reasons(e.get("reasons")),
            "trace_id": e.get("trace_id"),
        }
        for e in events
    ]
    st.dataframe(
        pd.DataFrame(rows).style.apply(_color, axis=1), use_container_width=True, height=600
    )


def render() -> None:
    st.header("Live feed")
    st.caption(
        "Newest 100 audit events, refreshed every 5 seconds. Block and escalate rows are highlighted."
    )
    _feed()
