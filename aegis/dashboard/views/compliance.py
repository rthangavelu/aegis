"""Compliance mapping view — tests × regulatory frameworks × status per system."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from aegis.dashboard import data

_FRAMEWORK_LABEL = {
    "NIST_AI_RMF": "NIST AI RMF",
    "ISO_42001": "ISO/IEC 42001",
    "EU_AI_ACT": "EU AI Act",
}

_STATUS_SYMBOL = {
    "pass": "✓",
    "warn": "⚠",
    "fail": "✗",
    "na": "—",
    "pending": "⏳",
    "error": "⚡",
}


def render(run_id: str) -> None:
    tests = data.load_tests()
    results = data.load_results(run_id)
    systems = data.load_systems()

    system_ids = sorted({s["id"] for s in systems})

    # Build result lookup: (system_id, test_id) → status
    result_map: dict[tuple[str, str], str] = {
        (r["system_id"], r["test_id"]): r["status"] for r in results
    }

    # Gather all frameworks present in the test library
    all_frameworks: set[str] = set()
    for t in tests:
        for m in t.get("mappings", []):
            all_frameworks.add(m["framework"])

    framework_order = [f for f in _FRAMEWORK_LABEL if f in all_frameworks]

    if not framework_order:
        st.info("No regulatory mappings found in the test library.")
        return

    st.subheader("Regulatory Coverage")
    st.caption(
        "Each row is a test case mapped to a regulatory clause. "
        "Status columns show how each system performed on that test."
    )

    tabs = st.tabs([_FRAMEWORK_LABEL.get(f, f) for f in framework_order])

    for tab, framework in zip(tabs, framework_order):
        with tab:
            # Collect tests that map to this framework
            mapped: list[dict] = []
            for t in tests:
                for m in t.get("mappings", []):
                    if m["framework"] == framework:
                        mapped.append({"test": t, "ref": m["ref"]})
                        break  # one entry per test per framework

            if not mapped:
                st.info(f"No tests mapped to {_FRAMEWORK_LABEL[framework]}.")
                continue

            mapped.sort(key=lambda x: x["ref"])

            rows = []
            for entry in mapped:
                t = entry["test"]
                row: dict = {
                    "Ref": entry["ref"],
                    "Test ID": t["id"],
                    "Name": t.get("name", ""),
                    "Pillar": t.get("pillar", ""),
                    "Severity": t.get("severity", ""),
                    "Type": t.get("type", ""),
                }
                for sid in system_ids:
                    status = result_map.get((sid, t["id"]), "—")
                    row[sid] = _STATUS_SYMBOL.get(status, status)
                rows.append(row)

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Coverage summary
            tested_count = sum(
                1
                for entry in mapped
                if any(
                    result_map.get((sid, entry["test"]["id"])) not in (None, "na", "pending")
                    for sid in system_ids
                )
            )
            st.caption(
                f"{tested_count} / {len(mapped)} controls tested across {len(system_ids)} system(s)"
            )
