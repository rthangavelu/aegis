"""Test results view — per-system drill-down with evidence."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aegis.dashboard import data

_STATUS_EMOJI = {
    "pass": "✓ pass",
    "warn": "⚠ warn",
    "fail": "✗ fail",
    "na": "— n/a",
    "pending": "⏳ pending",
    "error": "⚡ error",
}
_STATUS_COLOR = {
    "pass": "#2ecc71",
    "warn": "#f39c12",
    "fail": "#e74c3c",
    "error": "#e74c3c",
    "na": "#bdc3c7",
    "pending": "#3498db",
}


def render(run_id: str) -> None:
    results = data.load_results(run_id)
    tests = data.load_tests()
    test_map = {t["id"]: t for t in tests}

    system_ids = sorted({r["system_id"] for r in results})
    if not system_ids:
        st.warning("No test results found for this run.")
        return

    col_sys, col_status = st.columns([2, 3])
    with col_sys:
        selected_system = st.selectbox("System", system_ids)
    with col_status:
        all_statuses = ["pass", "warn", "fail", "na", "pending", "error"]
        selected_statuses = st.multiselect(
            "Filter by status",
            all_statuses,
            default=["pass", "warn", "fail", "error"],
        )

    sys_results = [
        r for r in results if r["system_id"] == selected_system and r["status"] in selected_statuses
    ]
    sys_results.sort(key=lambda r: (r["status"], r["test_id"]))

    # Status summary counts
    all_sys_results = [r for r in results if r["system_id"] == selected_system]
    counts = {s: sum(1 for r in all_sys_results if r["status"] == s) for s in all_statuses}
    metric_cols = st.columns(len(all_statuses))
    for col, status in zip(metric_cols, all_statuses):
        col.metric(_STATUS_EMOJI[status], counts[status])

    st.divider()

    # Main results table
    rows = []
    for r in sys_results:
        t = test_map.get(r["test_id"], {})
        rows.append(
            {
                "Test ID": r["test_id"],
                "Name": t.get("name", ""),
                "Pillar": t.get("pillar", ""),
                "Type": t.get("type", ""),
                "Severity": t.get("severity", ""),
                "Status": _STATUS_EMOJI.get(r["status"], r["status"]),
                "Value": f"{r['metric_value']:.4f}" if r["metric_value"] is not None else "",
                "Threshold": r["threshold"],
                "Message": r["message"][:120],
            }
        )

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No results match the selected filters.")

    # Evidence drill-down
    with_evidence = [r for r in sys_results if r["evidence_uri"]]
    if with_evidence:
        st.subheader("Evidence")
        for r in with_evidence:
            with st.expander(f"{r['test_id']} · {_STATUS_EMOJI.get(r['status'], r['status'])}"):
                st.write(f"**URI:** `{r['evidence_uri']}`")
                if r["evidence_hash"]:
                    st.write(f"**SHA-256:** `{r['evidence_hash']}`")
                if r["message"]:
                    st.write(f"**Message:** {r['message']}")
