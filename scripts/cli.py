"""Command-line interface for the theoretical-week simulator.

Examples (run from the project root):

    python scripts/cli.py pipeline
    python scripts/cli.py lookup --id-sim 5601 --poi-sim 0133898091CD
    python scripts/cli.py stats
    python scripts/cli.py serve

Every data-facing command accepts --dataset {real,demo} (default: real).
`demo` is the SYNTHETIC pre-Phase-2 demonstration dataset -- see
docs/decisions/0003-synthetic-demo-dataset.md and
`python scripts/generate_demo_dataset.py`. It is never loaded by default;
you must ask for it explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from src.simulation.simulator import lookup_poi, validate_against_historical

_DATASET_OPTION = click.option(
    "--dataset",
    type=click.Choice(["real", "demo"]),
    default="real",
    show_default=True,
    help="'real' = supplied company extract. 'demo' = SYNTHETIC demo dataset "
    "(generate first with `python scripts/generate_demo_dataset.py`).",
)


def _canonical_path(dataset: str) -> Path:
    return settings.DATA_CANONICAL / "poi_canonical.parquet" if dataset == "real" else settings.DEMO_CANONICAL_PARQUET


def _load_canonical(dataset: str = "real") -> pd.DataFrame:
    path = _canonical_path(dataset)
    if not path.exists():
        hint = "python scripts/run_pipeline.py" if dataset == "real" else "python scripts/generate_demo_dataset.py"
        raise click.ClickException(f"{path} not found. Run `{hint}` first.")
    return pd.read_parquet(path)


@click.group()
def cli() -> None:
    """Theoretical Week Simulator -- Phase 1 CLI."""


@cli.command()
def pipeline() -> None:
    """Run the full ingestion -> validation -> canonical pipeline."""
    from scripts.run_pipeline import main as run_pipeline_main

    run_pipeline_main()


@cli.command()
@click.option("--id-sim", required=True, help="Id_Sim of the simulation.")
@click.option("--poi-sim", required=True, help="POI_Sim identifier.")
@_DATASET_OPTION
def lookup(id_sim: str, poi_sim: str, dataset: str) -> None:
    """Look up one POI and explain its theoretical-week calculation."""
    canonical = _load_canonical(dataset)
    result = lookup_poi(canonical, id_sim, poi_sim)
    if result is None:
        raise click.ClickException(f"No POI found for Id_Sim={id_sim}, POI_Sim={poi_sim}")

    if dataset == "demo":
        click.secho(
            "*** SYNTHETIC DEMO DATA -- generated, not real company data (see "
            "data/synthetic/demo_2025_2026/metadata/README.md) ***",
            fg="yellow",
            bold=True,
        )
    click.echo(f"POI            : {result.id_sim} / {result.poi_sim}")
    click.echo(f"Data origin    : {result.data_origin}")
    click.echo(f"Status         : {result.calculation_status}")
    click.echo("Component dates:")
    for comp, val in result.component_dates.items():
        click.echo(f"  {comp:<14}: {val if val is not None else '(missing)'}")
    if result.calculation_status == "CALCULATED":
        click.echo(f"DateTheorique  : {result.date_theorique}")
        click.echo(f"SemTheorique   : {result.sem_theorique} ({result.sem_theorique_label})")
        click.echo(f"BlockingElement: {', '.join(result.blocking_element)}")
    else:
        click.echo(f"MissingComponents: {', '.join(result.missing_components) or '(none)'}")
        click.echo(f"InvalidComponents: {', '.join(result.invalid_components) or '(none)'}")
    if result.data_quality_flag:
        click.echo(f"QualityFlags   : {', '.join(result.data_quality_flag)}")


@cli.command()
@_DATASET_OPTION
def stats(dataset: str) -> None:
    """Print status distribution and historical match rate for the current
    canonical dataset."""
    canonical = _load_canonical(dataset)
    click.echo(f"Dataset: {dataset.upper()} ({_canonical_path(dataset)})")
    click.echo(f"Total POIs: {len(canonical):,}")
    click.echo("Status distribution:")
    for status, count in canonical["calculation_status"].value_counts().items():
        click.echo(f"  {status:<16}: {count:,} ({count / len(canonical):.1%})")

    summary = validate_against_historical(canonical)
    click.echo("\nHistorical validation:")
    click.echo(f"  Comparable POIs: {summary.comparable_pois}")
    if summary.match_rate is None:
        click.echo("  Match rate: N/A (no comparable historical SemTheorique in this dataset)")
    else:
        click.echo(f"  Match rate: {summary.match_rate:.1%} ({summary.matches}/{summary.comparable_pois})")


@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=5000, type=int)
@_DATASET_OPTION
def serve(host: str, port: int, dataset: str) -> None:
    """Launch the lightweight web UI. --dataset only sets the initial view;
    the UI also has a switcher link to change dataset without restarting."""
    from src.simulation.webapp import create_app

    app = create_app(default_dataset=dataset)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    cli()
