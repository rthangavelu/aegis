"""Claude-powered repo analysis, test case generation, and evidence evaluation."""

from __future__ import annotations

import json
import os

_MODEL = "claude-sonnet-4-6"
_client = None


def _client_instance():
    global _client
    if _client is None:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise RuntimeError("anthropic package not installed. Run: uv add anthropic") from e
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before running: export ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def _parse_json(text: str) -> object:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _call(prompt: str, max_tokens: int = 2000) -> str:
    client = _client_instance()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def analyze_repo(
    context: dict,
    extra_docs: list[dict] | None = None,
    business_context: str = "",
) -> dict:
    """
    Use Claude to understand what AI systems are in the repo, their risk profile,
    and applicable regulatory frameworks.

    extra_docs: additional documents (uploaded files, fetched URLs) as list of {path, content}
    business_context: free-text operator description of the business / system
    """
    files_text = "\n\n".join(f"=== {f['path']} ===\n{f['content']}" for f in context["files"][:20])
    tree_text = "\n".join(context["directory_tree"][:60])

    extra_section = ""
    if extra_docs:
        extra_section = (
            "\n\nAdditional business documents provided by the operator:\n"
            + "\n\n".join(f"=== {d['path']} ===\n{d['content']}" for d in extra_docs)
        )

    context_section = ""
    if business_context.strip():
        context_section = f"\n\nOperator-provided business context:\n{business_context.strip()}"

    prompt = f"""You are an AI governance auditor analyzing a code repository.

Directory structure:
{tree_text}

Key files extracted ({len(context["files"])} total):
{files_text}{extra_section}{context_section}

Analyze this repository and return a JSON object with:
- "business_domain": the industry/sector (e.g. "HR/hiring", "financial services/credit scoring", "healthcare diagnostics", "retail recommendation")
- "summary": 2-3 sentence description of what this repo does and its governance risk profile
- "ai_systems": list of AI/ML systems detected, each with:
  - "name": system name or description
  - "purpose": what it does in the business context
  - "model_type": classification|regression|llm|recommender|other
  - "risk_level": unacceptable|high|limited|minimal (based on impact on people's lives/rights)
  - "data_types": list of data types processed (e.g. ["personal data", "biometric", "financial", "health"])
  - "protected_attributes": attributes that could affect fairness (e.g. ["age", "gender", "race", "disability"])
  - "decision_impact": how decisions affect real people (e.g. "determines loan approval", "screens job candidates")
- "frameworks_detected": ML/AI frameworks found (e.g. ["scikit-learn", "pytorch", "huggingface", "openai"])
- "governance_gaps": list of specific concerns visible in the code/docs RIGHT NOW (e.g. "no bias testing found", "no model card present")
- "applicable_regulations": list from: EU_AI_ACT|GDPR|NIST_AI_RMF|ISO_42001|CCPA|HIPAA|FCRA|ECOA

Treat operator-provided business context and additional documents as authoritative descriptions of the business.
Return ONLY valid JSON, no other text."""

    return _parse_json(_call(prompt, max_tokens=2500))


def generate_test_cases(
    analysis: dict,
    context: dict,
    extra_docs: list[dict] | None = None,
    business_context: str = "",
) -> list[dict]:
    """
    Generate 12-15 AI governance test cases specific to the detected business context.
    Test cases reflect the actual AI systems, data types, risk profile, and any operator
    documents or business context provided.
    """
    systems_text = json.dumps(analysis.get("ai_systems", []), indent=2)
    gaps_text = "\n".join(f"- {g}" for g in analysis.get("governance_gaps", []))
    regs = ", ".join(analysis.get("applicable_regulations", []))
    domain = analysis.get("business_domain", "unknown")

    extra_section = ""
    if extra_docs:
        extra_section = (
            "\n\nAdditional business documents (use these to make tests more specific):\n"
            + "\n\n".join(f"--- {d['path']} ---\n{d['content'][:3000]}" for d in extra_docs)
        )

    context_section = ""
    if business_context.strip():
        context_section = f"\n\nOperator-provided business context:\n{business_context.strip()}"

    prompt = f"""You are an AI governance expert. Generate specific governance test cases for this codebase.

Business domain: {domain}
Summary: {analysis.get("summary", "")}

AI systems detected:
{systems_text}

Governance gaps already visible:
{gaps_text or "— none identified"}

Applicable regulations: {regs}{extra_section}{context_section}

Generate 12-15 governance test cases that are SPECIFIC to this business context.
Use the additional documents and operator context above to make tests even more precise —
e.g. if a DPA mentions specific data retention periods, test that the code implements them;
if a business brief mentions a specific vulnerable user group, test for protections for that group.

If this is a hiring system, test for gender/race bias in candidate ranking.
If it's a credit system, test for racial/age disparities in credit decisions.
If it's a healthcare system, test for outcome disparities across demographic groups.
Make every test case relevant to the ACTUAL domain and AI systems found.

Return a JSON array where each item has:
- "id": "GEN-001", "GEN-002", etc.
- "name": specific test name mentioning the actual domain/system (e.g. "Gender bias in candidate scoring" not "Fairness check")
- "description": what this test checks and why it matters for THIS business (2-3 sentences)
- "pillar": one of: Governance & Accountability|Fairness|Transparency|Privacy & Data|Safety & Security|Reliability|Human Oversight|GenAI|Training & Culture
- "type": evidence|attestation|process|technical
- "severity": critical|high|medium|low
- "check_method": HOW to check this — be specific (e.g. "Search for 'gender' or 'sex' feature in training code and check if it's excluded or fairness-tested", "Check if README contains 'Known Limitations' and 'Bias and Fairness' sections")
- "pass_criteria": what PASS looks like (concrete, specific to this repo)
- "fail_criteria": what FAIL looks like (concrete, specific to this repo)
- "why_it_matters": 1-2 sentences on the real-world harm if this fails (make it specific to the business domain)
- "how_to_improve": list of 3-4 concrete steps to address this
- "regulatory_ref": primary regulatory reference (e.g. "EU AI Act Art. 10", "NIST AI RMF MEASURE 2.11", "GDPR Art. 22")

Distribute across pillars. Prioritise: critical fairness issues for the specific domain, missing documentation, lack of human oversight for high-stakes decisions, privacy risks for the data types involved.

Return ONLY a valid JSON array, no other text."""

    result = _parse_json(_call(prompt, max_tokens=5000))
    return result if isinstance(result, list) else result.get("test_cases", [])


def evaluate_test(test: dict, context: dict) -> dict:
    """
    Use Claude to evaluate a single test case against the repo content.
    Returns status, finding, evidence location, explanation, and improvement steps.
    """
    files_text = "\n\n".join(f"=== {f['path']} ===\n{f['content']}" for f in context["files"][:18])

    prompt = f"""You are evaluating whether a code repository passes this AI governance test.

TEST ID: {test["id"]}
TEST NAME: {test["name"]}
Description: {test["description"]}
How to check: {test["check_method"]}
Pass criteria: {test["pass_criteria"]}
Fail criteria: {test["fail_criteria"]}

Repository content:
{files_text}

Carefully evaluate the repository against this test. Be thorough and honest.
If the evidence is ambiguous, lean toward "warn" rather than "pass".

Return JSON with:
- "status": "pass" | "warn" | "fail" | "na" (na only if the test genuinely doesn't apply)
- "finding": 1-2 sentences describing EXACTLY what you found (or didn't find) in the repo
- "evidence_location": specific file path and what was found there, or null if nothing found
- "explanation": why this matters for this specific AI system (2-3 sentences, make it concrete)
- "improvement_steps": list of 3-4 concrete, actionable steps to fix this if failing or warning

Return ONLY valid JSON."""

    try:
        result = _parse_json(_call(prompt, max_tokens=1200))
    except Exception as e:
        result = {
            "status": "error",
            "finding": f"Evaluation error: {e}",
            "evidence_location": None,
            "explanation": "Could not evaluate this test due to an API error.",
            "improvement_steps": [],
        }

    return {
        "test_id": test["id"],
        "test_name": test["name"],
        "pillar": test["pillar"],
        "severity": test["severity"],
        "type": test.get("type", "evidence"),
        "regulatory_ref": test.get("regulatory_ref", ""),
        "why_it_matters": test.get("why_it_matters", ""),
        "how_to_improve": test.get("how_to_improve", []),
        **result,
    }


def compute_scan_scores(results: list[dict]) -> dict:
    """Compute Aegis Index scores from scan results using the standard scoring rules."""
    _STATUS_POINTS = {"pass": 1.0, "warn": 0.5, "fail": 0.0, "error": 0.0}
    _SEV_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    _SCORED = {"pass", "warn", "fail", "error"}

    by_pillar: dict[str, list] = {}
    for r in results:
        if r["status"] not in _SCORED:
            continue
        by_pillar.setdefault(r["pillar"], []).append(r)

    pillar_scores = {}
    for pillar, items in by_pillar.items():
        total_w = sum(_SEV_WEIGHTS.get(r["severity"], 1) for r in items)
        if total_w == 0:
            continue
        total_pts = sum(
            _STATUS_POINTS.get(r["status"], 0) * _SEV_WEIGHTS.get(r["severity"], 1) for r in items
        )
        pillar_scores[pillar] = round(100 * total_pts / total_w, 1)

    overall = round(sum(pillar_scores.values()) / len(pillar_scores), 1) if pillar_scores else 0.0

    has_critical_fail = any(
        r["status"] in ("fail", "error") and r["severity"] == "critical" for r in results
    )

    if overall >= 80 and not has_critical_fail:
        rag = "Green"
    elif overall >= 60 and not has_critical_fail:
        rag = "Amber"
    else:
        rag = "Red"

    counts = {s: sum(1 for r in results if r["status"] == s) for s in _STATUS_POINTS}
    counts["na"] = sum(1 for r in results if r["status"] == "na")
    counts["pending"] = 0

    return {
        "overall": overall,
        "rag": rag,
        "pillar_scores": pillar_scores,
        "counts": counts,
        "has_critical_fail": has_critical_fail,
    }
