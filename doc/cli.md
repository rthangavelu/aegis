# CLI Reference

This document covers every Aegis CLI command, its flags, example output, and exit codes.

---

## Usage

```bash
uv run aegis <command> [options]
```

All commands print a spinner and use Rich for coloured output.

---

## `aegis validate`

Validate all YAML test cases and remediations against their JSON schemas.

```bash
uv run aegis validate
```

**Example output:**

```
✓ 41 test case(s) valid
✓ 17 remediation(s) valid
```

**Exit codes:** 0 = all valid; 1 = validation errors (details printed to stderr).

---

## `aegis seed`

Load the three mock AI systems into the local SQLite database (`aegis.db`).

```bash
uv run aegis seed
```

Safe to run multiple times — it upserts. Systems are marked `mock: true`.

**Example output:**

```
Seeded 3 AI system(s):
  credit-scoring-v3   High    production
  support-chatbot     Limited production
  resume-screener     High    production
```

**Exit codes:** 0 = success.

---

## `aegis inventory`

List all AI systems currently in the database.

```bash
uv run aegis inventory
```

**Example output:**

```
ID                   Name                    Risk       Type            Stage        Owner
credit-scoring-v3    Credit Scoring v3       High       classification  production   Risk Team
support-chatbot      Customer Support Bot    Limited    llm             production   CX Team
resume-screener      Resume Screener         High       classification  production   HR Tech
```

**Exit codes:** 0 = success; 1 = no database found (run `aegis seed` first).

---

## `aegis run`

Execute test cases and store results.

```bash
uv run aegis run --all
uv run aegis run --system <id>
```

**Flags:**

| Flag | Description |
|---|---|
| `--all` | Run against all systems in the inventory |
| `--system <id>` | Run against one system (use the slug from `aegis inventory`) |

**Example output:**

```
Running 41 test cases against 3 system(s)...
  credit-scoring-v3   32 applicable   32 pass   0 warn   0 fail   0 na
  support-chatbot     28 applicable    8 pass  10 warn   7 fail   3 na
  resume-screener     31 applicable    6 pass   2 warn  16 fail   7 na

Run ID: a1b2c3d4-5678-...
Finished in 4.2s
```

**Exit codes:** 0 = success (even if tests fail — test failures are results, not errors); 1 = execution error.

**CI usage:** To fail the pipeline on critical test failures, use:

```bash
uv run aegis run --all && uv run aegis score
# Then check exit code of score (non-zero if critical failures)
```

(GitHub Actions CI gate is on the v0.2 roadmap.)

---

## `aegis score`

Compute Aegis Index scores for a test run and print the summary.

```bash
uv run aegis score
uv run aegis score --run-id <uuid>
```

**Flags:**

| Flag | Description |
|---|---|
| `--run-id <uuid>` | Score a specific run. Defaults to the latest run. |

**Example output:**

```
System               Index   Maturity   RAG
credit-scoring-v3    100.0      5       Green
support-chatbot       67.2      4       Amber
resume-screener       20.6      2       Red

Organisation Aegis Index: 62.0 / 100   Red   Maturity 4/5
```

**Exit codes:** 0 = success; 1 = no runs found or scoring error.

---

## `aegis recommend`

Generate a prioritised improvement plan and write it to `improvement_plan.md`.

```bash
uv run aegis recommend
uv run aegis recommend --run-id <uuid>
```

**Flags:**

| Flag | Description |
|---|---|
| `--run-id <uuid>` | Use a specific run. Defaults to the latest run. |

**Output file:** `improvement_plan.md` in the working directory. Contains P0 items, quick wins, strategic items, hygiene items, projected uplifts, effort estimates, owner roles, and a 30/60/90-day roadmap.

**Exit codes:** 0 = success; 1 = no runs or no failing tests.

---

## `aegis dashboard`

Launch the Streamlit dashboard.

```bash
uv run aegis dashboard
```

Opens at `http://localhost:8501`. The dashboard auto-refreshes data every 30 seconds.

To use the **Scan Repo** tab, set the Anthropic API key before launching:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
uv run aegis dashboard
```

Or enter the key in the UI form on the Scan Repo tab.

**Exit codes:** Inherits Streamlit's exit code (0 on clean exit, 1 on error).

---

## `aegis mcp`

Start the Aegis MCP server over stdio transport.

```bash
uv run aegis mcp
```

The process reads JSON-RPC messages from stdin and writes responses to stdout. It is designed to be launched by an MCP client (e.g. Claude Code) rather than run interactively.

**Exit codes:** 0 = clean shutdown; 1 = startup error.

---

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | `aegis dashboard` (Scan Repo tab), `aegis mcp` | Anthropic API key for Claude-powered features. Can also be entered in the dashboard UI. |

---

## Database location

Aegis uses a SQLite database at `aegis.db` in the current working directory. Run all commands from the same directory to share state. To start fresh:

```bash
rm aegis.db && uv run aegis seed
```
