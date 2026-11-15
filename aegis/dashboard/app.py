"""Aegis Streamlit dashboard — 5 views."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Aegis — AI Governance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from aegis.dashboard import data  # noqa: E402  (must come after set_page_config)
from aegis.dashboard.views import (  # noqa: E402
    compliance,
    executive,
    inventory,
    recommendations,
    test_results,
)

# MOCK DATA warning — always visible
st.warning(
    "⚠️ **MOCK DATA** — All systems, results and scores are simulated. "
    "This output is an assessment, not legal or compliance advice."
)

st.title("🛡️ Aegis — AI Governance Dashboard")

# Load run
run_id = data.latest_run_id()
if not run_id:
    st.error(
        "No test runs found. Run the following from the CLI first:\n\n"
        "```\naegis seed && aegis run --all && aegis score\n```"
    )
    st.stop()

data.ensure_scored(run_id)
st.caption(f"Run: `{run_id}`")

# 5-tab navigation
tab_exec, tab_inv, tab_tests, tab_comp, tab_recs = st.tabs(
    ["Executive", "Inventory", "Test Results", "Compliance", "Recommendations"]
)

with tab_exec:
    executive.render(run_id)

with tab_inv:
    inventory.render(run_id)

with tab_tests:
    test_results.render(run_id)

with tab_comp:
    compliance.render(run_id)

with tab_recs:
    recommendations.render(run_id)

st.divider()
st.caption("Aegis v0.1 · Output is an assessment, not legal advice · © 2026 Flowwolf")
