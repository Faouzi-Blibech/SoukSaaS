"""Visual system for the owner console: tokens, CSS, HTML helpers, Plotly template."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

STATIC = Path(__file__).resolve().parent / "static"

VOID = "#06080B"
PANEL = "#0B0F14"
LINE = "#1B242E"
LINE_HI = "#2A3744"
TEXT = "#DCE3EA"
DIM = "#7F8E9D"
FAINT = "#4B5866"
SIGNAL = "#46B4FF"
ALARM = "#FF5A36"
MONO = "JetBrains Mono, Consolas, monospace"
SANS = "Instrument Sans, Segoe UI, sans-serif"

FLAGGED = {"block", "escalate"}

# ---------------------------------------------------------------- plotly

_axis = {
    "gridcolor": LINE,
    "gridwidth": 1,
    "zeroline": False,
    "showline": True,
    "linecolor": LINE_HI,
    "ticks": "outside",
    "tickcolor": LINE_HI,
    "ticklen": 4,
    "automargin": True,
    "tickfont": {"family": MONO, "size": 11, "color": DIM},
    "title": {"font": {"family": SANS, "size": 12, "color": DIM}},
}

pio.templates["souk"] = go.layout.Template(
    layout={
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": SANS, "color": TEXT, "size": 12},
        "colorway": [SIGNAL, "#2F7FB8", "#1E5278", FAINT, DIM],
        "xaxis": _axis,
        "yaxis": _axis,
        "margin": {"l": 8, "r": 8, "t": 8, "b": 8},
        "hoverlabel": {
            "bgcolor": PANEL,
            "bordercolor": LINE_HI,
            "font": {"family": MONO, "size": 12, "color": TEXT},
        },
        "legend": {"font": {"family": SANS, "size": 12, "color": DIM}, "bgcolor": "rgba(0,0,0,0)"},
        "bargap": 0.45,
    }
)
pio.templates.default = "souk"


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def style_fig(fig: go.Figure, height: int = 260, **layout: Any) -> go.Figure:
    fig.update_layout(template="souk", height=height, **layout)
    return fig


def plot(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": False})


def bar_chart(
    labels: list, values: list, flagged: set | None = None, horizontal: bool = False, height: int = 260
) -> go.Figure:
    flagged = flagged or set()
    colors = [ALARM if lb in flagged else SIGNAL for lb in labels]
    fills = [rgba(c, 0.5) for c in colors]
    if horizontal:
        fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=fills))
        fig.update_yaxes(autorange="reversed", showgrid=False)
    else:
        fig = go.Figure(go.Bar(x=labels, y=values, marker_color=fills))
        fig.update_xaxes(showgrid=False)
    fig.update_traces(
        marker_line_color=colors, marker_line_width=1, hovertemplate="%{label}: %{value}<extra></extra>"
    )
    return style_fig(fig, height)


def funnel_chart(labels: list[str], values: list[float], height: int = 260) -> go.Figure:
    """Horizontal step bars with the stage-to-stage ratio annotated."""
    fig = go.Figure()
    top = max(values) if values and max(values) else 1
    for i, (lb, v) in enumerate(zip(labels, values, strict=True)):
        fig.add_trace(
            go.Bar(
                x=[v], y=[lb], orientation="h", marker_color=rgba(SIGNAL, 0.42 - i * 0.1),
                marker_line_color=SIGNAL, marker_line_width=1, showlegend=False,
                hovertemplate=f"{lb}: %{{x}}<extra></extra>",
            )
        )
        ratio = "" if i == 0 or not values[i - 1] else f"  {v / values[i - 1] * 100:.0f}%"
        fig.add_annotation(
            x=v, y=lb, text=f"{v:g}{ratio}", showarrow=False, xanchor="left", xshift=8,
            font={"family": MONO, "size": 12, "color": TEXT},
        )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(range=[0, top * 1.25], showgrid=True)
    return style_fig(fig, height, bargap=0.35)


# ---------------------------------------------------------------- css + html

def inject_css() -> None:
    css = "\n".join((STATIC / n).read_text(encoding="utf-8") for n in ("base.css", "components.css"))
    st.html(f"<style>{css}</style>")


def esc(v: Any) -> str:
    return escape("" if v is None else str(v))


def short_ts(ts: Any) -> str:
    s = str(ts or "")
    return s[11:19] if len(s) >= 19 else s


def pill(text: str, kind: str = "") -> str:
    return f'<span class="sc-pill {kind}">{esc(text)}</span>'


def page_head(title: str, sub: str = "", pills: list[str] | None = None) -> None:
    right = f'<div class="sc-right">{"".join(pills)}</div>' if pills else ""
    subtitle = f'<div class="sc-sub">{esc(sub)}</div>' if sub else ""
    st.html(f'<div class="sc-head"><div><h1>{esc(title)}</h1>{subtitle}</div>{right}</div>')


def section(title: str) -> None:
    st.html(f'<div class="sc-sec">{esc(title)}</div>')


def spark(values: list[float], alert: bool = False) -> str:
    if not values:
        return ""
    top = max(values) or 1
    bars = "".join(
        '<i class="z" style="height:2px"></i>' if not v else f'<i style="height:{max(8, v / top * 100):.0f}%"></i>'
        for v in values
    )
    return f'<div class="spark">{bars}</div>'


def kpi(
    label: str, value: Any, sub: str = "", *, unit: str = "", alert: bool = False,
    series: list[float] | None = None, meter: float | None = None, pips: int | None = None,
) -> None:
    extra = ""
    if meter is not None:
        extra = f'<div class="sc-meter"><b style="width:{max(0.0, min(1.0, meter)) * 100:.1f}%"></b></div>'
    if pips is not None:
        extra = '<div class="sc-pips">' + "".join(
            f'<i class="{"on" if i < pips else ""}"></i>' for i in range(5)
        ) + "</div>"
    unit_html = f"<small>{esc(unit)}</small>" if unit else ""
    st.html(
        f'<div class="sc-kpi{" alert" if alert else ""}"><div class="lb">{esc(label)}</div>'
        f'<div class="vl">{esc(value)}{unit_html}</div>{extra}'
        f'<div class="sb">{esc(sub)}</div>{spark(series or [], alert)}</div>'
    )


def decision_cell(decision: Any) -> str:
    d = str(decision or "")
    return f'<span class="dec-{esc(d)}">{esc(d) or "-"}</span>'


def html_table(columns: list[tuple[str, str]], rows: list[dict], *, mono: set[str] | None = None,
               flag_if: Any = None, raw: set[str] | None = None) -> None:
    """columns: (key, header). Cells are escaped unless the key is in `raw` (pre-escaped HTML)."""
    mono, raw = mono or set(), raw or set()
    head = "".join(f"<th>{esc(h)}</th>" for _k, h in columns)
    body = []
    for r in rows:
        cls = ' class="flag"' if flag_if and flag_if(r) else ""
        cells = "".join(
            f'<td class="{"m" if k in mono else ""}{" r" if k == "reasons" else ""}">'
            f"{r.get(k, '') if k in raw else esc(r.get(k))}</td>"
            for k, _h in columns
        )
        body.append(f"<tr{cls}>{cells}</tr>")
    st.html(
        f'<div class="sc-tablewrap"><table class="sc-table"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def embed_html(html: str, height: int) -> None:
    """Render an HTML document in an iframe (st.iframe on current Streamlit, components before)."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:  # pragma: no cover - older Streamlit
        import streamlit.components.v1 as components

        components.html(html, height=height)
