"""Approvals page."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.common import call, fmt_reasons


def render() -> None:
    st.header("Approvals")
    ok, items = call(api.get, "/owner/approvals", status="pending")
    if not ok:
        return
    if not items:
        st.success("No pending approvals.")
    for a in items:
        with st.container(border=True):
            st.markdown(
                f"**{a.get('kind')}** `{a.get('id')}` (ref `{a.get('ref_id')}`), created {a.get('created_at')}"
            )
            st.write("Reasons: " + fmt_reasons(a.get("reasons")))
            if a.get("payment"):
                st.json(a["payment"])
            c1, c2, _ = st.columns([1, 1, 4])
            for col, action, label in ((c1, "approve", "Approve"), (c2, "reject", "Reject")):
                if col.button(label, key=f"{action}_{a['id']}"):
                    ok, res = call(api.post, f"/owner/approvals/{a['id']}/{action}")
                    if ok:
                        st.session_state["approval_result"] = res
                        st.rerun()
    if "approval_result" in st.session_state:
        st.subheader("Last result")
        st.json(st.session_state["approval_result"])
