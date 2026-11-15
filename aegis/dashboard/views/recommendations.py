"""Recommendations view — prioritized improvement plan with projected uplift."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from aegis.dashboard import data

_TIER_CONFIG = {
    "P0": {"label": "P0 — Critical (fix immediately)", "color": "#e74c3c", "icon": "🔴"},
    "quick_win": {
        "label": "Quick Wins (high impact, low effort)",
        "color": "#2ecc71",
        "icon": "🟢",
    },
    "strategic": {
        "label": "Strategic (high effort, significant uplift)",
        "color": "#3498db",
        "icon": "🔵",
    },
    "hygiene": {"label": "Hygiene (lower priority)", "color": "#95a5a6", "icon": "⚪"},
}
_TIER_ORDER = ["P0", "quick_win", "strategic", "hygiene"]

_HORIZON = {"P0": "30 days", "quick_win": "30 days", "strategic": "90 days", "hygiene": "60 days"}


def _uplift_chart(items: list[dict]) -> go.Figure:
    items_sorted = sorted(items, key=lambda x: -x["projected_uplift"])[:8]
    fig = go.Figure(
        go.Bar(
            x=[i["projected_uplift"] for i in items_sorted],
            y=[i["title"][:35] for i in items_sorted],
            orientation="h",
            marker_color=[
                _TIER_CONFIG.get(i["tier"], {}).get("color", "#95a5a6") for i in items_sorted
            ],
            text=[f"+{i['projected_uplift']:.1f} pts" for i in items_sorted],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Top Actions by Projected Uplift",
        xaxis=dict(title="Avg index uplift (points)"),
        height=300,
        margin=dict(l=20, r=60, t=40, b=20),
    )
    return fig


def render(run_id: str) -> None:
    items = data.load_recommendations(run_id)

    if not items:
        st.success("No failing tests found — nothing to recommend.")
        return

    # Summary banner
    tier_counts = {tier: sum(1 for i in items if i["tier"] == tier) for tier in _TIER_ORDER}
    col_total, col_p0, col_qw, col_strat, col_hyg = st.columns(5)
    col_total.metric("Total", len(items))
    col_p0.metric("P0", tier_counts["P0"])
    col_qw.metric("Quick Wins", tier_counts["quick_win"])
    col_strat.metric("Strategic", tier_counts["strategic"])
    col_hyg.metric("Hygiene", tier_counts["hygiene"])

    st.plotly_chart(_uplift_chart(items), use_container_width=True)

    # Tier sections
    for tier in _TIER_ORDER:
        tier_items = [i for i in items if i["tier"] == tier]
        if not tier_items:
            continue
        cfg = _TIER_CONFIG[tier]
        st.markdown(
            f"### {cfg['icon']} {cfg['label']}",
        )

        for item in tier_items:
            scope = "org-wide" if item["org_wide_fix"] else ", ".join(item["systems_affected"])
            with st.expander(
                f"**{item['title']}** · `{item['test_id']}` · {item['pillar']} · "
                f"Effort {item['effort']} · +{item['projected_uplift']:.1f} pts"
            ):
                col_meta, col_uplift = st.columns([2, 1])
                with col_meta:
                    st.markdown(
                        f"| | |\n|---|---|\n"
                        f"| **Severity** | {item['severity']} |\n"
                        f"| **Effort** | {item['effort']} |\n"
                        f"| **Owner** | {item['owner_role']} |\n"
                        f"| **Scope** | {scope} |\n"
                        f"| **Priority score** | {item['priority']} |\n"
                        f"| **Target horizon** | {_HORIZON.get(item['tier'], '60 days')} |"
                    )

                with col_uplift:
                    st.markdown("**Before → After:**")
                    for sid in item["systems_affected"]:
                        cur = item["current_scores"].get(sid, 0.0)
                        proj = item["projected_scores"].get(sid, cur)
                        delta = proj - cur
                        sign = "+" if delta >= 0 else ""
                        st.markdown(f"- `{sid}`: {cur:.1f} → {proj:.1f} ({sign}{delta:.1f})")

                if item["steps"]:
                    st.markdown("**Steps:**")
                    for i, step in enumerate(item["steps"], 1):
                        st.markdown(f"{i}. {step}")

    # 30/60/90 roadmap
    st.divider()
    st.subheader("30 / 60 / 90-day Roadmap")
    buckets: dict[str, list[str]] = {"30 days": [], "60 days": [], "90 days": []}
    for item in items:
        buckets[_HORIZON.get(item["tier"], "60 days")].append(item["title"])

    road_cols = st.columns(3)
    for col, (horizon, titles) in zip(road_cols, buckets.items()):
        with col:
            st.markdown(f"**{horizon}**")
            if titles:
                for t in titles:
                    st.markdown(f"- {t}")
            else:
                st.markdown("—")
