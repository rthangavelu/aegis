"""Repo Scanner view — scan a git repo, generate governance tests, execute and show results."""

from __future__ import annotations

import shutil
import time

import plotly.graph_objects as go
import streamlit as st

_RAG_COLOR = {"Green": "#2ecc71", "Amber": "#f39c12", "Red": "#e74c3c"}
_STATUS_COLOR = {
    "pass": "#2ecc71",
    "warn": "#f39c12",
    "fail": "#e74c3c",
    "na": "#bdc3c7",
    "error": "#e74c3c",
}
_STATUS_EMOJI = {"pass": "✓", "warn": "⚠", "fail": "✗", "na": "—", "error": "⚡", "pending": "⏳"}
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_PILLAR_ORDER = [
    "Governance & Accountability",
    "Fairness",
    "Transparency",
    "Privacy & Data",
    "Safety & Security",
    "Reliability",
    "Human Oversight",
    "GenAI",
    "Training & Culture",
]


def _pillar_gauge(scores: dict) -> go.Figure:
    ordered = [(p, scores.get(p)) for p in _PILLAR_ORDER if scores.get(p) is not None]
    if not ordered:
        return go.Figure()
    pillars = [p[:12] for p, _ in ordered]
    values = [v for _, v in ordered]
    colors = [_RAG_COLOR.get("Green" if v >= 80 else "Amber" if v >= 60 else "Red") for v in values]
    fig = go.Figure(
        go.Bar(
            x=pillars,
            y=values,
            marker_color=colors,
            text=[f"{v:.0f}" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Score by Pillar",
        yaxis=dict(range=[0, 115]),
        height=320,
        margin=dict(l=10, r=10, t=40, b=60),
    )
    return fig


def _run_scan(
    repo_input: str,
    branch: str,
    extra_docs: list[dict],
    business_context: str,
) -> None:
    """Execute the full scan pipeline with live progress updates in st.status."""
    from aegis.scan.analyzer import (
        analyze_repo,
        compute_scan_scores,
        evaluate_test,
        generate_test_cases,
    )
    from aegis.scan.repo import clone_repo, extract_context

    is_temp = False
    repo_path = None

    with st.status("Running AI governance scan…", expanded=True) as status:
        # Stage 1: Clone / read repo
        st.write("**Stage 1 of 5** — Accessing repository…")
        t0 = time.time()
        try:
            repo_path, is_temp = clone_repo(repo_input.strip(), branch.strip())
        except Exception as e:
            status.update(label="Failed to access repository", state="error")
            st.error(f"Could not access repo: {e}")
            return
        st.write(f"  ✓ Repository ready in {time.time() - t0:.1f}s")

        # Stage 2: Extract context
        st.write("**Stage 2 of 5** — Extracting AI-relevant files…")
        t0 = time.time()
        context = extract_context(repo_path)
        n_files = len(context["files"])
        n_extra = len(extra_docs)
        st.write(
            f"  ✓ Extracted {n_files} repo file(s)"
            + (f" + {n_extra} supplementary document(s)" if n_extra else "")
            + f" ({context['total_chars_extracted']:,} chars) in {time.time() - t0:.1f}s"
        )
        if n_files == 0 and n_extra == 0:
            status.update(label="No readable files found", state="error")
            st.error("No readable files extracted. Check the path or permissions.")
            if is_temp and repo_path:
                shutil.rmtree(repo_path, ignore_errors=True)
            return

        # Stage 3: Analyse with Claude
        st.write("**Stage 3 of 5** — Analysing AI systems with Claude…")
        t0 = time.time()
        try:
            analysis = analyze_repo(
                context, extra_docs=extra_docs, business_context=business_context
            )
        except RuntimeError as e:
            status.update(label="Claude API error", state="error")
            st.error(str(e))
            if is_temp and repo_path:
                shutil.rmtree(repo_path, ignore_errors=True)
            return
        n_systems = len(analysis.get("ai_systems", []))
        domain = analysis.get("business_domain", "unknown")
        st.write(
            f"  ✓ Identified {n_systems} AI system(s) in domain **{domain}** ({time.time() - t0:.1f}s)"
        )

        # Stage 4: Generate test cases
        st.write("**Stage 4 of 5** — Generating governance test cases…")
        t0 = time.time()
        test_cases = generate_test_cases(
            analysis, context, extra_docs=extra_docs, business_context=business_context
        )
        st.write(f"  ✓ Generated {len(test_cases)} test cases ({time.time() - t0:.1f}s)")

        # Stage 5: Execute tests
        st.write(f"**Stage 5 of 5** — Executing {len(test_cases)} governance tests…")
        results = []
        progress = st.progress(0.0)
        for i, test in enumerate(test_cases):
            st.write(f"  Running: `{test['id']}` {test['name'][:55]}…")
            result = evaluate_test(test, context)
            results.append(result)
            progress.progress((i + 1) / len(test_cases))

        scores = compute_scan_scores(results)
        status.update(
            label=f"Scan complete — Aegis Index {scores['overall']:.1f} / 100 · {scores['rag']}",
            state="complete",
            expanded=False,
        )

    # Clean up temp clone
    if is_temp and repo_path:
        shutil.rmtree(repo_path, ignore_errors=True)

    st.session_state["scan_analysis"] = analysis
    st.session_state["scan_results"] = results
    st.session_state["scan_scores"] = scores
    st.session_state["scan_repo"] = repo_input
    st.session_state["scan_extra_docs"] = extra_docs


def _show_results() -> None:
    analysis = st.session_state["scan_analysis"]
    results = st.session_state["scan_results"]
    scores = st.session_state["scan_scores"]
    repo_label = st.session_state.get("scan_repo", "")
    extra_docs = st.session_state.get("scan_extra_docs", [])

    st.divider()

    # --- Header metrics ---
    rag = scores["rag"]
    color = _RAG_COLOR.get(rag, "#95a5a6")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Aegis Index", f"{scores['overall']:.1f} / 100")
    c2.markdown(
        f"**RAG**<br/><span style='background:{color};color:white;padding:3px 10px;"
        f"border-radius:4px;font-weight:bold'>{rag}</span>",
        unsafe_allow_html=True,
    )
    cnts = scores["counts"]
    c3.metric("Pass", cnts.get("pass", 0))
    c4.metric("Warn", cnts.get("warn", 0))
    c5.metric("Fail", cnts.get("fail", 0))

    # --- System summary ---
    st.subheader(f"Analysis — {analysis.get('business_domain', 'Unknown domain')}")
    st.caption(analysis.get("summary", ""))

    if extra_docs:
        st.caption(
            f"Supplementary documents used: {', '.join(d['path'].split('/')[-1] for d in extra_docs)}"
        )

    ai_systems = analysis.get("ai_systems", [])
    if ai_systems:
        sys_cols = st.columns(min(len(ai_systems), 3))
        for col, sys in zip(sys_cols, ai_systems):
            risk = sys.get("risk_level", "unknown")
            rc = _RAG_COLOR.get(
                {"high": "Red", "unacceptable": "Red", "limited": "Amber", "minimal": "Green"}.get(
                    risk, "Amber"
                ),
                "#95a5a6",
            )
            with col:
                st.markdown(
                    f'<div style="border-left:4px solid {rc};padding:8px 12px;background:#f9f9f9;border-radius:4px">'
                    f"<b>{sys.get('name', 'AI System')}</b><br/>"
                    f"<small>{sys.get('purpose', '')}</small><br/>"
                    f"<small><b>Risk:</b> {risk} · <b>Type:</b> {sys.get('model_type', '')}</small><br/>"
                    f"<small><b>Impact:</b> {sys.get('decision_impact', '')}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # --- Pillar bar chart ---
    if scores["pillar_scores"]:
        st.plotly_chart(_pillar_gauge(scores["pillar_scores"]), use_container_width=True)

    # --- Governance gaps ---
    gaps = analysis.get("governance_gaps", [])
    if gaps:
        st.subheader("Governance Gaps Detected")
        for g in gaps:
            st.markdown(f"- {g}")

    # --- Test results ---
    st.subheader("Governance Test Results")

    col_status, col_sev, col_pillar = st.columns(3)
    with col_status:
        status_filter = st.multiselect(
            "Filter by status",
            ["pass", "warn", "fail", "na", "error"],
            default=["fail", "warn", "error"],
        )
    with col_sev:
        sev_filter = st.multiselect(
            "Filter by severity",
            ["critical", "high", "medium", "low"],
            default=["critical", "high", "medium", "low"],
        )
    with col_pillar:
        all_pillars = sorted({r["pillar"] for r in results})
        pillar_filter = st.multiselect("Filter by pillar", all_pillars, default=all_pillars)

    visible = [
        r
        for r in results
        if r["status"] in status_filter
        and r["severity"] in sev_filter
        and r["pillar"] in pillar_filter
    ]
    visible.sort(key=lambda r: (_SEV_ORDER.get(r["severity"], 9), r["status"] != "fail"))

    if not visible:
        st.info("No results match the selected filters.")
        return

    for r in visible:
        sc = _STATUS_COLOR.get(r["status"], "#95a5a6")
        emoji = _STATUS_EMOJI.get(r["status"], "?")
        label = f"{emoji} **{r['test_id']}** — {r['test_name']} · `{r['severity']}` · {r['pillar']}"
        with st.expander(label):
            col_verdict, col_meta = st.columns([2, 1])
            with col_verdict:
                st.markdown(
                    f'<div style="border-left:4px solid {sc};padding:8px 12px;'
                    f'background:#fafafa;border-radius:4px;margin-bottom:8px">'
                    f"<b>Finding:</b> {r.get('finding', '')}</div>",
                    unsafe_allow_html=True,
                )
                if r.get("evidence_location"):
                    st.markdown(f"**Evidence:** `{r['evidence_location']}`")
                if r.get("explanation"):
                    st.markdown(f"**Why it matters:** {r['explanation']}")

            with col_meta:
                st.markdown(
                    f"**Status:** {emoji} {r['status'].upper()}  \n"
                    f"**Severity:** {r['severity']}  \n"
                    f"**Type:** {r.get('type', '')}  \n"
                    f"**Ref:** {r.get('regulatory_ref', '—')}"
                )

            steps = r.get("improvement_steps") or r.get("how_to_improve") or []
            if steps:
                st.markdown("**How to improve:**")
                if isinstance(steps, list):
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"{i}. {step}")
                else:
                    st.markdown(steps)

    st.caption(
        "⚠️ AI-GENERATED — Test cases were generated by Claude based on repo content"
        + (f" and {len(extra_docs)} supplementary document(s)" if extra_docs else "")
        + f". This is an assessment, not a compliance certification. Repo: `{repo_label}`"
    )


def render() -> None:
    st.subheader("Scan Repository for AI Governance Issues")
    st.markdown(
        "Point Aegis at any git repository. Claude will read the code and documentation, "
        "generate governance test cases specific to your AI system, execute them, and score the results."
    )

    with st.form("scan_form"):
        # --- Repo input ---
        repo_input = st.text_input(
            "Repository URL or local path",
            placeholder="https://github.com/org/repo  or  /path/to/local/repo",
        )
        col_branch, col_key = st.columns(2)
        with col_branch:
            branch = st.text_input("Branch (optional)", placeholder="main")
        with col_key:
            api_key_input = st.text_input(
                "Anthropic API key (or set ANTHROPIC_API_KEY env var)",
                type="password",
                placeholder="sk-ant-…",
            )

        st.divider()

        # --- Supplementary business documents ---
        st.markdown(
            "**Supplementary business documents** *(optional — helps Claude understand the business deeply)*"
        )
        st.caption(
            "Upload any documents that describe the business: data processing agreements, model risk policies, "
            "product briefs, compliance checklists, architecture diagrams, or anything that explains WHAT the "
            "AI system does and WHO it affects. Claude will use these to generate more precise test cases."
        )
        uploaded_files = st.file_uploader(
            "Upload documents",
            type=["pdf", "docx", "txt", "md"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        doc_url = st.text_input(
            "Or fetch a document from a URL (Confluence page, public wiki, model card URL…)",
            placeholder="https://…",
        )

        business_context = st.text_area(
            "Or paste / type business context directly",
            placeholder=(
                "e.g. 'This system predicts employee attrition for HR teams in the UK financial sector. "
                "It processes age, tenure, salary band and performance ratings. Decisions inform redundancy "
                "planning and affect approximately 5,000 employees. We are subject to UK GDPR and the "
                "Equality Act 2010.'"
            ),
            height=120,
        )

        submitted = st.form_submit_button("Scan & Assess", type="primary", use_container_width=True)

    if submitted:
        import os

        from aegis.scan.repo import extract_uploaded_files, fetch_url_content

        if not repo_input.strip():
            st.error("Please enter a repository URL or path.")
            return
        if api_key_input.strip():
            os.environ["ANTHROPIC_API_KEY"] = api_key_input.strip()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("Anthropic API key is required. Enter it above or set ANTHROPIC_API_KEY.")
            return

        # Build extra_docs from uploads + URL
        extra_docs: list[dict] = []
        if uploaded_files:
            with st.spinner(f"Reading {len(uploaded_files)} uploaded file(s)…"):
                extra_docs.extend(extract_uploaded_files(uploaded_files))
            st.success(f"Loaded: {', '.join(d['path'].split('/')[-1] for d in extra_docs)}")

        if doc_url.strip():
            with st.spinner(f"Fetching {doc_url.strip()}…"):
                try:
                    extra_docs.append(fetch_url_content(doc_url.strip()))
                    st.success(f"Fetched: {doc_url.strip()}")
                except Exception as e:
                    st.warning(f"Could not fetch URL ({e}) — continuing without it.")

        # Clear previous results
        for key in ("scan_analysis", "scan_results", "scan_scores", "scan_repo", "scan_extra_docs"):
            st.session_state.pop(key, None)

        _run_scan(repo_input, branch, extra_docs, business_context)

    if "scan_results" in st.session_state:
        _show_results()
