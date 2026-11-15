"""Aegis CLI — aegis validate | seed | run | score | recommend | dashboard."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="aegis", help="AI governance and ethics testing agent.", add_completion=False
)
console = Console()

_PKG = Path(__file__).parent
_TESTLIB_DIR = _PKG / "testlib"
_REMEDIATION_DIR = _PKG / "remediation"
_SEED_SYSTEMS = _PKG / "seed" / "systems.yaml"


@app.command()
def validate() -> None:
    """Validate all test cases and remediations against their schemas."""
    from aegis.engine.loader import load_remediations, load_test_library

    errors: list[str] = []

    console.print("[bold]Validating test library...[/bold]")
    try:
        tests = load_test_library(_TESTLIB_DIR)
        console.print(f"  [green]✓[/green] {len(tests)} test case(s) valid")
    except Exception as exc:
        errors.append(str(exc))
        console.print(f"  [red]✗[/red] {exc}")

    console.print("[bold]Validating remediations...[/bold]")
    try:
        remediations = load_remediations(_REMEDIATION_DIR)
        console.print(f"  [green]✓[/green] {len(remediations)} remediation(s) valid")
    except Exception as exc:
        errors.append(str(exc))
        console.print(f"  [red]✗[/red] {exc}")

    if errors:
        console.print(f"\n[red bold]{len(errors)} error(s). Fix them and re-run.[/red bold]")
        raise typer.Exit(1)

    console.print("\n[green bold]All valid.[/green bold]")


@app.command()
def seed() -> None:
    """Load mock AI systems into the database."""
    from aegis.inventory.store import seed_inventory

    n = seed_inventory()
    if n:
        console.print(f"[green]✓[/green] Seeded {n} system(s).")
    else:
        console.print("[yellow]Systems already seeded (no changes).[/yellow]")


@app.command()
def inventory() -> None:
    """List all AI systems in the inventory."""
    from aegis.db import init_db
    from aegis.inventory.store import list_systems

    init_db()
    systems = list_systems()
    if not systems:
        console.print("[yellow]No systems found. Run `aegis seed` first.[/yellow]")
        return

    table = Table(title="AI System Inventory")
    for col in ["ID", "Name", "Risk Tier", "Model Type", "Owner", "Mock"]:
        table.add_column(col)
    for s in systems:
        mock_label = "[yellow]MOCK[/yellow]" if s.mock else ""
        table.add_row(s.id, s.name, s.risk_tier.value, s.model_type.value, s.owner, mock_label)
    console.print(table)


@app.command()
def run(
    all_systems: bool = typer.Option(False, "--all", help="Run against all systems"),
    system: str = typer.Option("", "--system", help="Run against a single system ID"),
) -> None:
    """Execute test cases against AI systems."""
    from sqlmodel import select

    from aegis.db import get_session, init_db
    from aegis.engine.executor import execute_run
    from aegis.engine.loader import load_test_library
    from aegis.inventory.store import get_system, list_systems
    from aegis.models import TestResult, TestStatus

    if not all_systems and not system:
        console.print("[red]Specify --all or --system <id>[/red]")
        raise typer.Exit(1)

    init_db()
    tests = load_test_library(_TESTLIB_DIR)
    systems = [get_system(system)] if system else list_systems()
    systems = [s for s in systems if s is not None]

    if not systems:
        console.print("[yellow]No systems found. Run `aegis seed` first.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Running {len(tests)} tests against {len(systems)} system(s)...[/bold]\n")

    status_color = {
        TestStatus.pass_: "green",
        TestStatus.warn: "yellow",
        TestStatus.fail: "red",
        TestStatus.na: "dim",
        TestStatus.pending: "blue",
        TestStatus.error: "red bold",
    }

    with get_session() as session:
        test_run = execute_run(systems, tests, session)
        run_id = test_run.id
        results = session.exec(select(TestResult).where(TestResult.run_id == run_id)).all()
        results = list(results)

    for sys_obj in systems:
        sys_results = [r for r in results if r.system_id == sys_obj.id]
        console.print(
            f"[bold]{sys_obj.id}[/bold]  ({sys_obj.risk_tier.value}-risk {sys_obj.model_type.value})"
        )
        tbl = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        tbl.add_column("Test", style="dim", width=12)
        tbl.add_column("Status", width=9)
        tbl.add_column("Value", width=8)
        tbl.add_column("Message")
        for r in sorted(sys_results, key=lambda x: x.test_id):
            color = status_color.get(r.status, "white")
            val = f"{r.metric_value:.3f}" if r.metric_value is not None else ""
            msg = (r.message or "")[:80]
            tbl.add_row(r.test_id, f"[{color}]{r.status.value}[/{color}]", val, msg)
        console.print(tbl)
        console.print()

    console.print("[bold]Summary[/bold]")
    for sys_obj in systems:
        sys_results = [r for r in results if r.system_id == sys_obj.id]
        counts = {s: sum(1 for r in sys_results if r.status == s) for s in TestStatus}
        critical_test_ids = {t["id"] for t in tests if t.get("severity") == "critical"}
        critical_fails = any(
            r.status == TestStatus.fail and r.test_id in critical_test_ids for r in sys_results
        )
        flag = "  [red bold]→ CRITICAL FAIL[/red bold]" if critical_fails else ""
        console.print(
            f"  {sys_obj.id}: "
            f"[green]{counts[TestStatus.pass_]} pass[/green]  "
            f"[yellow]{counts[TestStatus.warn]} warn[/yellow]  "
            f"[red]{counts[TestStatus.fail]} fail[/red]  "
            f"[blue]{counts[TestStatus.pending]} pending[/blue]  "
            f"[dim]{counts[TestStatus.na]} n/a[/dim]" + flag
        )

    console.print(f"\n[dim]Run ID: {run_id}[/dim]")


@app.command()
def score(
    run_id: str = typer.Option("", "--run-id", help="Run ID to score (default: latest run)."),
) -> None:
    """Compute Aegis Index scores from a test run."""
    from sqlmodel import select

    from aegis.db import get_session, init_db
    from aegis.models import Score, TestRun
    from aegis.scoring.engine import compute_scores

    init_db()
    with get_session() as session:
        if run_id:
            target_run = session.get(TestRun, run_id)
            if not target_run:
                console.print(f"[red]Run {run_id!r} not found.[/red]")
                raise typer.Exit(1)
        else:
            runs = session.exec(select(TestRun).order_by(TestRun.started_at.desc())).all()
            if not runs:
                console.print("[red]No test runs found. Run `aegis run --all` first.[/red]")
                raise typer.Exit(1)
            target_run = runs[0]

        display_run_id = target_run.id  # capture before session closes

        # Clear existing scores for this run to avoid duplicates on re-score
        existing = session.exec(select(Score).where(Score.run_id == display_run_id)).all()
        for s in existing:
            session.delete(s)
        session.commit()

        scored = compute_scores(display_run_id, session)
        # Detach score data before session closes
        scored_data = [
            {
                "scope": s.scope,
                "scope_id": s.scope_id,
                "pillar": s.pillar,
                "score": s.score,
                "maturity": s.maturity,
                "rag": s.rag,
            }
            for s in scored
        ]

    # Display system-level overall scores
    console.print(f"\n[bold]Aegis Index — Run {display_run_id}[/bold]\n")

    _RAG_COLOUR = {"Green": "green", "Amber": "yellow", "Red": "red"}

    tbl = Table(show_header=True, header_style="bold")
    tbl.add_column("System", style="bold")
    tbl.add_column("Index", justify="right")
    tbl.add_column("Maturity", justify="center")
    tbl.add_column("RAG", justify="center")

    system_overalls = [
        s for s in scored_data if s["scope"] == "system" and s["pillar"] == "overall"
    ]
    system_overalls.sort(key=lambda s: s["score"], reverse=True)
    for s in system_overalls:
        colour = _RAG_COLOUR.get(s["rag"].value, "white")
        tbl.add_row(
            s["scope_id"],
            f"{s['score']:.1f}",
            str(s["maturity"]),
            f"[{colour}]{s['rag'].value}[/{colour}]",
        )
    console.print(tbl)

    # Org roll-up
    org = next((s for s in scored_data if s["scope"] == "org" and s["pillar"] == "overall"), None)
    if org:
        colour = _RAG_COLOUR.get(org["rag"].value, "white")
        console.print(
            f"\n[bold]Organisation Aegis Index:[/bold] {org['score']:.1f} / 100  "
            f"[{colour}]{org['rag'].value}[/{colour}]  Maturity {org['maturity']}/5\n"
        )

    # Per-system pillar breakdown
    console.print("[bold]Pillar breakdown[/bold]")
    pillar_tbl = Table(show_header=True, header_style="bold")
    pillar_tbl.add_column("System")
    pillar_tbl.add_column("Pillar")
    pillar_tbl.add_column("Score", justify="right")
    pillar_tbl.add_column("Maturity", justify="center")
    pillar_tbl.add_column("RAG", justify="center")

    pillar_rows = [s for s in scored_data if s["scope"] == "system" and s["pillar"] != "overall"]
    pillar_rows.sort(key=lambda s: (s["scope_id"], s["score"]))
    for s in pillar_rows:
        colour = _RAG_COLOUR.get(s["rag"].value, "white")
        pillar_tbl.add_row(
            s["scope_id"],
            s["pillar"],
            f"{s['score']:.1f}",
            str(s["maturity"]),
            f"[{colour}]{s['rag'].value}[/{colour}]",
        )
    console.print(pillar_tbl)


@app.command()
def recommend(
    run_id: str = typer.Option("", "--run-id", help="Run ID to recommend from (default: latest)."),
    output: str = typer.Option(
        "improvement_plan.md", "--output", "-o", help="Markdown output file."
    ),
) -> None:
    """Generate a prioritized improvement plan from a scored run."""
    from sqlmodel import select

    from aegis.db import get_session, init_db
    from aegis.models import Score, TestRun
    from aegis.recommend.engine import build_recommendations, render_markdown
    from aegis.scoring.engine import compute_scores

    _TIER_LABEL = {
        "P0": "[red bold]P0[/red bold]",
        "quick_win": "[green]Quick Win[/green]",
        "strategic": "[blue]Strategic[/blue]",
        "hygiene": "[dim]Hygiene[/dim]",
    }

    init_db()
    with get_session() as session:
        if run_id:
            target_run = session.get(TestRun, run_id)
            if not target_run:
                console.print(f"[red]Run {run_id!r} not found.[/red]")
                raise typer.Exit(1)
        else:
            runs = session.exec(select(TestRun).order_by(TestRun.started_at.desc())).all()
            if not runs:
                console.print("[red]No test runs found. Run `aegis run --all` first.[/red]")
                raise typer.Exit(1)
            target_run = runs[0]

        display_run_id = target_run.id

        # Ensure scores exist for this run
        existing_scores = session.exec(
            select(Score).where(Score.run_id == display_run_id, Score.pillar == "overall")
        ).all()
        if not existing_scores:
            console.print("[dim]No scores found for this run — computing now...[/dim]")
            compute_scores(display_run_id, session)

        items = build_recommendations(display_run_id, session)
        # Capture data before session closes
        snapshot = [
            {
                "tier": r.tier,
                "title": r.title,
                "test_id": r.test_id,
                "pillar": r.pillar,
                "severity": r.severity,
                "effort": r.effort,
                "owner_role": r.owner_role,
                "systems_affected": r.systems_affected,
                "priority": r.priority,
                "projected_uplift": r.projected_uplift,
                "current_scores": r.current_scores,
                "projected_scores": r.projected_scores,
                "org_wide_fix": r.org_wide_fix,
            }
            for r in items
        ]
        md = render_markdown(items, display_run_id)

    # Write Markdown plan
    out_path = Path(output)
    out_path.write_text(md)
    console.print(f"\n[dim]Improvement plan written to {out_path}[/dim]\n")

    if not snapshot:
        console.print("[green]No failing tests found — nothing to recommend.[/green]")
        return

    console.print(f"[bold]Improvement Plan — Run {display_run_id}[/bold]\n")

    tbl = Table(show_header=True, header_style="bold")
    tbl.add_column("Tier", width=10)
    tbl.add_column("Recommendation")
    tbl.add_column("Systems", width=22)
    tbl.add_column("Effort", justify="center", width=6)
    tbl.add_column("Owner", width=16)
    tbl.add_column("Priority", justify="right", width=8)
    tbl.add_column("Uplift", justify="right", width=8)

    for r in snapshot:
        scope = "org-wide" if r["org_wide_fix"] else ", ".join(r["systems_affected"])
        tbl.add_row(
            _TIER_LABEL.get(r["tier"], r["tier"]),
            f"[bold]{r['title']}[/bold]\n[dim]{r['test_id']} · {r['pillar']}[/dim]",
            scope[:22],
            r["effort"],
            r["owner_role"][:16],
            str(r["priority"]),
            f"+{r['projected_uplift']:.1f}",
        )

    console.print(tbl)
    console.print(f"\n[dim]Total recommendations: {len(snapshot)}[/dim]")


@app.command()
def dashboard() -> None:
    """Launch the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    console.print(f"[bold]Launching Aegis dashboard...[/bold]  {app_path}")
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
    )
    raise typer.Exit(result.returncode)


if __name__ == "__main__":
    app()
