# CLAUDE.md — Aegis

Read `INTENT.md` first. It is the source of truth for scope, scoring rules and acceptance criteria. If a request conflicts with it, ask before you deviate.

## Project

Aegis is an AI governance and ethics testing agent. It runs YAML test cases against AI systems, scores them into the Aegis Index, shows the results on a Streamlit dashboard, and produces prioritized recommendations.

## Commands

```bash
uv sync                          # install
uv run aegis validate            # validate testlib/ + remediation/ against schemas
uv run aegis seed                # load mock systems and data
uv run aegis run --all           # execute tests
uv run aegis score               # compute scores
uv run aegis recommend           # write improvement plan (Markdown)
uv run aegis dashboard           # launch Streamlit
uv run pytest -q                 # tests
uv run ruff check . && uv run ruff format .
```

## Project skills

Use the skills in `.claude/skills/`:

- `aegis-builder`: code architecture, data model, runners, scoring and build order
- `aegis-test-author`: writing test cases and remediations
- `aegis-report`: running assessments, the dashboard views and recommendations

## Conventions

- Python 3.11+. Use type hints everywhere and pydantic models for every schema.
- Keep weights, thresholds and RAG bands in `aegis/scoring/config.yaml`, never hardcoded.
- Store each test case at `aegis/testlib/<pillar>/<ID>.yaml` and each remediation at `aegis/remediation/<REM-ID>.yaml`.
- A runner exception produces an `error` result. It is never a `pass`.
- Wrap each metric library (fairlearn, evidently, etc.) in a function in `aegis/engine/checks/`.
- Use fixed random seeds and pinned mock datasets, so runs are deterministic.
- Label all mock data with `# MOCK DATA` or `mock: true`.
- Never invent regulatory clause references. Write `TODO-verify` if you are unsure.

## Workflow

- Build in milestone order (M1 → M5 in `INTENT.md`). Finish each milestone with passing tests before starting the next.
- After each milestone, run `validate`, `pytest` and `ruff`, and update the README quickstart.
- Make small commits with clear messages, one milestone step per commit.
