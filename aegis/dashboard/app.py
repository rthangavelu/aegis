"""Aegis Streamlit dashboard — 6 views (5 governance + repo scanner)."""

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
    scanner,
    test_results,
)

st.title("🛡️ Aegis — AI Governance Dashboard")

# 6-tab navigation — Scanner first so it's the entry point for the repo workflow
tab_scan, tab_exec, tab_inv, tab_tests, tab_comp, tab_recs = st.tabs(
    ["Scan Repo", "Executive", "Inventory", "Test Results", "Compliance", "Recommendations"]
)

with tab_scan:
    scanner.render()

# The other 5 tabs require a seeded test run — guard with a banner inside each tab
with tab_exec:
    run_id = data.latest_run_id()
    if not run_id:
        st.warning(
            "No test runs found. Run `aegis seed && aegis run --all && aegis score` "
            "or use the **Scan Repo** tab to scan a repository."
        )
    else:
        data.ensure_scored(run_id)
        st.caption(f"Run: `{run_id}`")
        executive.render(run_id)

with tab_inv:
    run_id = data.latest_run_id()
    if not run_id:
        st.warning("No test runs found. See the **Executive** tab for setup instructions.")
    else:
        data.ensure_scored(run_id)
        inventory.render(run_id)

with tab_tests:
    run_id = data.latest_run_id()
    if not run_id:
        st.warning("No test runs found. See the **Executive** tab for setup instructions.")
    else:
        test_results.render(run_id)

with tab_comp:
    run_id = data.latest_run_id()
    if not run_id:
        st.warning("No test runs found. See the **Executive** tab for setup instructions.")
    else:
        compliance.render(run_id)

with tab_recs:
    run_id = data.latest_run_id()
    if not run_id:
        st.warning("No test runs found. See the **Executive** tab for setup instructions.")
    else:
        data.ensure_scored(run_id)
        recommendations.render(run_id)

st.divider()
st.caption("Aegis v0.1 · Output is an assessment, not legal advice · © 2026 Flowwolf")
