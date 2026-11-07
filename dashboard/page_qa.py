"""Q&A manager page."""

from __future__ import annotations

import streamlit as st

from dashboard import api
from dashboard.common import call


def render() -> None:
    st.header("Q&A manager")
    top = st.columns([2, 1, 3])
    status = top[0].selectbox("Status", ["all", "draft", "approved", "rejected"])
    if top[1].button("Generate"):
        ok, created = call(api.post, "/owner/qa/generate")
        if ok:
            st.success(f"Created {len(created)} draft entries.")
    ok, entries = call(api.get, "/owner/qa")
    if not ok:
        return
    if status != "all":
        entries = [e for e in entries if e.get("status") == status]
    if not entries:
        st.info("No entries.")
    for e in entries:
        eid = e["id"]
        with st.expander(f"[{e.get('status')}] {e.get('question')} (hits: {e.get('hits', 0)})"):
            c1, c2, _ = st.columns([1, 1, 4])
            for col, action, label in ((c1, "approve", "Approve"), (c2, "reject", "Reject")):
                if col.button(label, key=f"{action}_{eid}"):
                    ok, _res = call(api.post, f"/owner/qa/{eid}/{action}")
                    if ok:
                        st.rerun()
            with st.form(f"edit_{eid}"):
                q = st.text_input("Question", e.get("question", ""))
                a = st.text_area("Answer", e.get("answer", ""))
                v = st.text_area("Variants (one per line)", "\n".join(e.get("variants") or []))
                if st.form_submit_button("Save (returns to draft)"):
                    body = {
                        "question": q,
                        "answer": a,
                        "variants": [x.strip() for x in v.splitlines() if x.strip()],
                    }
                    ok, _res = call(api.put, f"/owner/qa/{eid}", body)
                    if ok:
                        st.rerun()
