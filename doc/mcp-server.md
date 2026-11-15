# MCP Server

This document covers setting up the Aegis MCP server, the full tool reference, and example usage from Claude Code.

---

## What it is

The Aegis MCP server exposes 10 governance tools over the Model Context Protocol (stdio transport). Once configured, Claude Code (and any other MCP client) can run assessments, query scores, get failing tests, and retrieve recommendations conversationally — no CLI required.

This lets you use natural language to drive Aegis:

> "What are the critical governance failures across all my AI systems?"
> "Run a full assessment on the resume-screener and show me the improvement plan."
> "Which systems are Red and what's the fastest fix?"

---

## Setup

### Start the server manually

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # optional — only needed for repo scanner tools
uv run aegis mcp
```

The server listens on stdio and prints a startup message. Keep this process running while using it from an MCP client.

### Configure Claude Code

Add to `~/.claude/config.json` (or your project-level `.claude/config.json`):

```json
{
  "mcpServers": {
    "aegis": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/aegis", "run", "aegis", "mcp"]
    }
  }
}
```

Replace `/absolute/path/to/aegis` with the path to the directory containing `pyproject.toml`.

After saving, restart Claude Code. Type `/mcp` to verify the `aegis` server appears in the tool list.

---

## Tools reference

### `list_systems`

List all AI systems in the Aegis inventory.

**Parameters:** none

**Returns:** JSON array of systems with `id`, `name`, `risk_tier`, `model_type`, `lifecycle_stage`, `owner`, `business_unit`, `mock`.

---

### `seed_systems`

Seed the three mock AI systems (`credit-scoring-v3`, `support-chatbot`, `resume-screener`) into the inventory. Safe to call multiple times — it upserts.

**Parameters:** none

**Returns:** Confirmation string.

---

### `run_assessment`

Run a full governance assessment: seed systems if needed, execute all test cases, compute Aegis Index scores.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system_id` | string | No | Assess only this system. Leave empty for all systems. |

**Returns:** JSON with `run_id`, `systems[]` (each with `system_id`, `aegis_index`, `rag`, `maturity`, `fail`, `warn`), and `organisation` summary.

**Example return:**
```json
{
  "run_id": "a1b2c3d4-...",
  "systems": [
    {"system_id": "credit-scoring-v3", "aegis_index": 100.0, "rag": "Green", "maturity": 5, "fail": 0, "warn": 0},
    {"system_id": "support-chatbot",   "aegis_index": 67.2,  "rag": "Amber", "maturity": 4, "fail": 3, "warn": 5},
    {"system_id": "resume-screener",   "aegis_index": 20.6,  "rag": "Red",   "maturity": 2, "fail": 16,"warn": 2}
  ],
  "organisation": {"aegis_index": 62.0, "rag": "Red", "maturity": 4}
}
```

---

### `get_scores`

Get Aegis Index scores, optionally filtered by system or run.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system_id` | string | No | Filter to one system. |
| `run_id` | string | No | Specific run. Defaults to the latest run. |

**Returns:** JSON array of score objects with `scope`, `scope_id`, `pillar`, `score`, `maturity`, `rag`.

---

### `get_test_results`

Get test results for a specific AI system.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system_id` | string | Yes | System to query. |
| `status_filter` | string | No | Comma-separated statuses: `pass,warn,fail,na,error`. Leave empty for all. |
| `run_id` | string | No | Defaults to the latest run. |

**Returns:** JSON array with `test_id`, `name`, `pillar`, `type`, `severity`, `status`, `metric_value`, `threshold`, `message`, `evidence_uri`.

---

### `get_failing_tests`

Get all failing tests (status `fail` or `error`), optionally filtered.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system_id` | string | No | Filter to one system. |
| `severity` | string | No | Filter to one severity: `critical`, `high`, `medium`, `low`. |
| `run_id` | string | No | Defaults to the latest run. |

**Returns:** JSON array sorted by severity then system, with `system_id`, `test_id`, `name`, `pillar`, `severity`, `status`, `message`, `metric_value`.

---

### `get_pillar_breakdown`

Get the Aegis Index broken down by pillar for a specific system.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system_id` | string | Yes | System to query. |
| `run_id` | string | No | Defaults to the latest run. |

**Returns:** JSON with `overall` (score, maturity, rag) and `pillars[]` sorted by score ascending (weakest first).

---

### `get_recommendations`

Get the prioritised improvement plan for the latest (or specified) run.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | No | Defaults to the latest run. |

**Returns:** JSON array sorted by priority, each with `tier`, `title`, `test_id`, `pillar`, `severity`, `effort`, `owner_role`, `org_wide_fix`, `systems_affected[]`, `priority_score`, `projected_uplift_pts`, `steps[]`.

---

### `add_system`

Register a new AI system in the inventory.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | URL-safe slug, e.g. `loan-approval-v2` |
| `name` | string | Yes | Human-readable name |
| `owner` | string | Yes | Accountable person or team |
| `business_unit` | string | Yes | Business unit name |
| `purpose` | string | Yes | What the system does |
| `model_type` | string | Yes | `classification` \| `regression` \| `llm` \| `recommender` \| `other` |
| `risk_tier` | string | Yes | `unacceptable` \| `high` \| `limited` \| `minimal` |
| `lifecycle_stage` | string | No | `development` \| `testing` \| `production` \| `deprecated`. Default: `production` |
| `eval_dataset` | string | No | Path to CSV evaluation dataset |

**Returns:** Confirmation string.

---

### `validate_library`

Validate all test cases and remediations against their JSON schemas.

**Parameters:** none

**Returns:** JSON with `status` (PASS/FAIL), `tests` (count or error), `remediations` (count or error).

---

## Example Claude Code conversation

```
You: Seed the mock systems and run a full governance assessment.

Claude: [calls seed_systems, then run_assessment]
        Assessment complete. Results:
        - credit-scoring-v3: 100.0 / Green
        - support-chatbot: 67.2 / Amber (3 fail, 5 warn)
        - resume-screener: 20.6 / Red (16 fail, 2 warn)
        Organisation: 62.0 / Red

You: What critical failures does the resume-screener have?

Claude: [calls get_failing_tests with system_id="resume-screener", severity="critical"]
        2 critical failures:
        - FAIR-001: Disparate impact ratio 0.61 (threshold: ≥ 0.8) — resume screening
          shows significant gender bias in candidate selection
        - HUM-004: No algorithmic recourse or appeal process documented

You: What's the fastest fix that would have the biggest impact?

Claude: [calls get_recommendations]
        Top quick win: Implement FAIR-001 remediation (REM-FAIR-001)
        - Projected uplift: +18.4 Aegis Index points
        - Effort: M (1-2 weeks)
        - Owner: ML Lead
        Steps: [lists steps from the playbook]
```

---

## Transport and authentication

**Transport:** stdio only. The MCP server reads from stdin and writes to stdout. No HTTP listener is started.

**Authentication:** None in v0.1. The server relies on local filesystem access — whoever can run the `aegis mcp` command has full access to all tools. Restrict process access at the OS level if multi-user isolation is needed.

**v0.2 roadmap:** HTTP transport with API key authentication, allowing remote clients and CI pipelines to call Aegis tools.
