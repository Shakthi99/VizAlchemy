"""
CLI entry point.

Usage examples:
  # Local only — migrate a single file
  python3 -m tableau_to_pbi migrate --input input_twb/MyDashboard.twb

  # Local only — batch
  python3 -m tableau_to_pbi migrate-batch --input-dir input_twb/

  # Touchless publish — migrate + publish to Power BI Service
  python3 -m tableau_to_pbi migrate --input input_twb/MyDashboard.twb \\
      --workspace "My Workspace"

  # Touchless publish — batch with XMLA (Fabric/Premium)
  python3 -m tableau_to_pbi migrate-batch --input-dir input_twb/ \\
      --workspace "My Workspace" \\
      --xmla "powerbi://api.powerbi.com/v1.0/myorg/My Workspace"

  Required env vars for publish:
    PBI_TENANT_ID      Azure AD tenant ID
    PBI_CLIENT_ID      App registration client ID
    PBI_CLIENT_SECRET  App registration secret  (omit for device-flow auth)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import click

from tableau_to_pbi.pipeline import migrate_workbook, migrate_batch

DEFAULT_INPUT_DIR  = Path(__file__).parent / "input_twb"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output_pbi"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
def cli() -> None:
    """Tableau → Power BI Migration Accelerator"""


# ── shared publish options (reused by both commands) ──────────────────────────
_publish_options = [
    click.option("--workspace", "workspace", default=None,
                 help="Power BI workspace name or GUID. Set to enable touchless publish."),
    click.option("--xmla", "xmla_endpoint", default=None,
                 help="XMLA endpoint URL for Premium/Fabric semantic model deploy."),
    click.option("--no-overwrite", "no_overwrite", is_flag=True, default=False,
                 help="Abort if report already exists in workspace (default: overwrite)."),
]

def _add_publish_options(cmd):
    for opt in reversed(_publish_options):
        cmd = opt(cmd)
    return cmd


@cli.command("migrate")
@click.option("--input",  "input_path", required=True, type=click.Path(exists=True))
@click.option("--output", "output_dir", default=str(DEFAULT_OUTPUT_DIR), show_default=True)
@click.option("--no-llm", "no_llm",    is_flag=True, default=False)
@click.option("--verbose", "-v",        is_flag=True, default=False)
@_add_publish_options
def migrate_cmd(input_path: str, output_dir: str, no_llm: bool, verbose: bool,
                workspace: Optional[str], xmla_endpoint: Optional[str],
                no_overwrite: bool) -> None:
    """Migrate a single Tableau workbook. Add --workspace to auto-publish."""
    _setup_logging(verbose)
    summary = migrate_workbook(
        Path(input_path),
        Path(output_dir),
        use_llm=not no_llm,
        workspace=workspace,
        xmla_endpoint=xmla_endpoint,
        overwrite=not no_overwrite,
    )
    _print_summary([summary])


@cli.command("migrate-batch")
@click.option("--input-dir",  "input_dir",  default=str(DEFAULT_INPUT_DIR), show_default=True)
@click.option("--output-dir", "output_dir", default=str(DEFAULT_OUTPUT_DIR), show_default=True)
@click.option("--no-llm",     "no_llm",     is_flag=True, default=False)
@click.option("--verbose", "-v",             is_flag=True, default=False)
@_add_publish_options
def migrate_batch_cmd(input_dir: str, output_dir: str, no_llm: bool, verbose: bool,
                      workspace: Optional[str], xmla_endpoint: Optional[str],
                      no_overwrite: bool) -> None:
    """Migrate all .twb / .twbx files in a folder. Add --workspace to auto-publish each."""
    _setup_logging(verbose)
    summaries = migrate_batch(
        Path(input_dir),
        Path(output_dir),
        use_llm=not no_llm,
        workspace=workspace,
        xmla_endpoint=xmla_endpoint,
        overwrite=not no_overwrite,
    )
    _print_summary(summaries)


def _print_summary(summaries: list[dict]) -> None:
    click.echo("\n" + "═" * 70)
    click.echo("  MIGRATION RESULTS")
    click.echo("═" * 70)
    for s in summaries:
        if "error" in s:
            click.secho(f"  ✗ {s['workbook']}: {s['error']}", fg="red")
            continue
        coverage = s.get("overall_coverage", "?")
        errors   = s.get("errors", 0)
        warnings = s.get("warnings", 0)
        color    = "green" if errors == 0 else "yellow"
        click.secho(
            f"  ✓ {s['workbook']}  coverage={coverage}  "
            f"errors={errors}  warnings={warnings}",
            fg=color,
        )
        click.echo(f"    PBIX   → {s.get('pbix_path', '')}")
        click.echo(f"    Output → {s.get('output_dir', '')}")
        if s.get("report_url"):
            click.secho(f"    Live   → {s['report_url']}", fg="cyan")
        if s.get("publish_error"):
            click.secho(f"    Publish failed: {s['publish_error']}", fg="yellow")
    click.echo("═" * 70)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
