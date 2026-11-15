"""Inventory heatmap — systems × pillars score grid."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aegis.dashboard import data

_PILLAR_SHORT = {
    "Governance & Accountability": "Governance",
    "Fairness": "Fairness",
    "Transparency": "Transparency",
    "Privacy & Data": "Privacy",
    "Safety & Security": "Safety",
    "Reliability": "Reliability",
    "Human Oversight": "Oversight",
    "GenAI": "GenAI",
    "Training & Culture": "Culture",
}

_PILLAR_ORDER = list(_PILLAR_SHORT.keys())

# Custom colorscale: 0=red, 60=amber, 80→100=green; -1=gray (N/A sentinel)
_COLORSCALE = [
    [0.0, "#e8e8e8"],  # -1 → gray (N/A)
    [0.01, "#e74c3c"],  # 0 → red
    [0.61, "#f39c12"],  # 60 → amber
    [0.80, "#2ecc71"],  # 80 → green
    [1.0, "#2ecc71"],  # 100 → green
]


def _build_heatmap(scores: list[dict], systems: list[dict]) -> go.Figure:
    sys_order = [s["id"] for s in sorted(systems, key=lambda s: s["id"])]
    pillar_scores = [s for s in scores if s["scope"] == "system" and s["pillar"] != "overall"]

    # Build matrix: rows=systems, cols=pillars
    pivot: dict[str, dict[str, float]] = {sid: {} for sid in sys_order}
    for s in pillar_scores:
        pivot.setdefault(s["scope_id"], {})[s["pillar"]] = s["score"]

    display_pillars = [p for p in _PILLAR_ORDER if any(p in pivot[sid] for sid in sys_order)]

    z_values = []
    text_values = []
    for sid in sys_order:
        row_z = []
        row_text = []
        for pillar in display_pillars:
            score = pivot[sid].get(pillar)
            if score is None:
                row_z.append(-1)
                row_text.append("N/A")
            else:
                row_z.append(score)
                row_text.append(f"{score:.1f}")
        z_values.append(row_z)
        text_values.append(row_text)

    short_pillars = [_PILLAR_SHORT.get(p, p) for p in display_pillars]

    fig = go.Figure(
        go.Heatmap(
            z=z_values,
            x=short_pillars,
            y=sys_order,
            text=text_values,
            texttemplate="%{text}",
            textfont={"size": 13, "color": "white"},
            colorscale=_COLORSCALE,
            zmin=-1,
            zmax=100,
            showscale=True,
            colorbar=dict(
                title="Score",
                tickvals=[0, 60, 80, 100],
                ticktext=["0", "60", "80", "100"],
            ),
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Pillar Scores by System",
        height=250 + len(sys_order) * 60,
        xaxis=dict(side="top"),
        margin=dict(l=20, r=20, t=80, b=20),
    )
    return fig


def render(run_id: str) -> None:
    scores = data.load_scores(run_id)
    systems = data.load_systems()

    st.subheader("Pillar Score Heatmap")
    st.caption("Green ≥ 80  ·  Amber 60–79  ·  Red < 60  ·  Gray = not applicable / all pending")

    fig = _build_heatmap(scores, systems)
    st.plotly_chart(fig, use_container_width=True)

    # System summary table
    st.subheader("System Inventory")
    system_overalls = {
        s["scope_id"]: s for s in scores if s["scope"] == "system" and s["pillar"] == "overall"
    }
    rows = []
    for s in systems:
        sc = system_overalls.get(s["id"], {})
        rows.append(
            {
                "ID": s["id"],
                "Name": s["name"],
                "Risk tier": s["risk_tier"].title(),
                "Model type": s["model_type"],
                "Owner": s["owner"],
                "BU": s["business_unit"],
                "Aegis Index": f"{sc.get('score', '—'):.1f}" if sc else "—",
                "RAG": sc.get("rag", "—"),
                "Maturity": sc.get("maturity", "—"),
                "Mock": "✓" if s["mock"] else "",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
