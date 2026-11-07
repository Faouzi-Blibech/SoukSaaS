"""SoukSaaS owner console (run: streamlit run dashboard/app.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from dashboard import (
    page_approvals,
    page_feed,
    page_insights,
    page_overview,
    page_qa,
    page_security,
)

PAGES = {
    "Overview": page_overview.render,
    "Live feed": page_feed.render,
    "Approvals": page_approvals.render,
    "Q&A manager": page_qa.render,
    "Insights": page_insights.render,
    "Security & Evals": page_security.render,
    "Simulator": page_security.render_simulator,
}


def main() -> None:
    st.set_page_config(page_title="SoukSaaS owner console", layout="wide")
    st.sidebar.title("SoukSaaS")
    choice = st.sidebar.radio("Page", list(PAGES))
    PAGES[choice]()


main()
