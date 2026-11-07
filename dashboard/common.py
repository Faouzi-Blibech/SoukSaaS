"""Shared helpers for dashboard pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard import api


def call(fn, *args: Any, **kwargs: Any) -> tuple[bool, Any]:
    """Run an API call; on ApiError show st.error and return (False, None)."""
    try:
        return True, fn(*args, **kwargs)
    except api.ApiError as exc:
        st.error(str(exc))
        return False, None


def fmt_reasons(reasons: Any) -> str:
    if isinstance(reasons, list):
        return "; ".join(str(r) for r in reasons)
    return "" if reasons is None else str(reasons)
