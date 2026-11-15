"""Executive view — Aegis Index, RAG status, top risks."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from aegis.dashboard import data

_RAG_COLOR = {"Green": "#2ecc71", "Amber": "#f39c12", "Red": "#e74c3c"}
_STATUS_EMOJI = {
    "pass": "✓",
    "warn": "⚠",
    "fail": "✗",
    "na": "—",
    "pending": "⏳",
    "error": "⚡",
}
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _rag_badge(rag: str) -> str:
    color = _RAG_COLOR.get(rag, "#95a5a6")
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:4px;font-weight:bold">{rag}</span>'
    )


def _gauge(value: float, rag: str) -> go.Figure:
    bar_color = _RAG_COLOR.get(rag, "#95a5a6")
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": " / 100", "font": {"size": 28}},
            title={"text": "Organisation Aegis Index", "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": bar_color, "thickness": 0.3},
                "steps": [
                    {"range": [0, 60], "color": "#fadbd8"},
                    {"range": [60, 80], "color": "#fdebd0"},
                    {"range": [80, 100], "color": "#d5f5e3"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 3},
                    "thickness": 0.75,
                    "value": value,
                },
            },
        )
    )
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=0))
    return fig


def _system_bars(system_scores: list[dict]) -> go.Figure:
    sorted_systems = sorted(system_scores, key=lambda s: s["score"])
    names = [s["scope_id"] for s in sorted_systems]
    scores = [s["score"] for s in sorted_systems]
    colors = [_RAG_COLOR.get(s["rag"], "#95a5a6") for s in sorted_systems]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{v:.1f}" for v in scores],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="System Aegis Index",
        xaxis=dict(range=[0, 110], title="Score"),
        height=200,
        margin=dict(l=20, r=40, t=40, b=20),
    )
    return fig


def render(run_id: str) -> None:
    scores = data.load_scores(run_id)
    systems = data.load_systems()
    results = data.load_results(run_id)
    tests = data.load_tests()
    test_map = {t["id"]: t for t in tests}
    sys_map = {s["id"]: s for s in systems}

    org = next((s for s in scores if s["scope"] == "org" and s["pillar"] == "overall"), None)
    system_scores = [s for s in scores if s["scope"] == "system" and s["pillar"] == "overall"]

    # --- Org headline ---
    st.subheader("Organisation Overview")
    if org:
        col_gauge, col_systems = st.columns([1, 1])
        with col_gauge:
            st.plotly_chart(_gauge(org["score"], org["rag"]), use_container_width=True)
            st.markdown(
                f"**RAG:** {_rag_badge(org['rag'])}  &nbsp; **Maturity:** {org['maturity']}/5",
                unsafe_allow_html=True,
            )
        with col_systems:
            st.plotly_chart(_system_bars(system_scores), use_container_width=True)

    # --- System cards ---
    st.subheader("Systems at a Glance")
    cols = st.columns(len(system_scores) or 1)
    for col, sc in zip(cols, sorted(system_scores, key=lambda s: -s["score"])):
        sys_info = sys_map.get(sc["scope_id"], {})
        color = _RAG_COLOR.get(sc["rag"], "#95a5a6")
        with col:
            st.markdown(
                f"""<div style="border-left:4px solid {color};padding:8px 12px;
                background:#f9f9f9;border-radius:4px">
                <b>{sc["scope_id"]}</b><br/>
                <span style="font-size:28px;font-weight:bold">{sc["score"]:.1f}</span> / 100<br/>
                {_rag_badge(sc["rag"])} &nbsp; Maturity {sc["maturity"]}/5<br/>
                <small>{sys_info.get("risk_tier", "").title()} risk · {sys_info.get("model_type", "")}</small>
                </div>""",
                unsafe_allow_html=True,
            )

    # --- Top failures ---
    st.subheader("Top Failures")
    failures = [
        r
        for r in results
        if r["status"] in ("fail", "error")
        and test_map.get(r["test_id"], {}).get("severity") in ("critical", "high")
    ]
    failures.sort(
        key=lambda r: (
            _SEV_ORDER.get(test_map.get(r["test_id"], {}).get("severity", "low"), 3),
            r["system_id"],
        )
    )
    if not failures:
        st.success("No critical or high failures found.")
    else:
        rows = []
        for r in failures:
            t = test_map.get(r["test_id"], {})
            rows.append(
                {
                    "System": r["system_id"],
                    "Test": r["test_id"],
                    "Name": t.get("name", ""),
                    "Pillar": t.get("pillar", ""),
                    "Severity": t.get("severity", ""),
                    "Message": r["message"][:80],
                }
            )
        import pandas as pd

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
