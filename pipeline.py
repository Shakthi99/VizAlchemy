"""
Migration pipeline — orchestrates Parser → M-Query → DAX → Visual → Validate → Write → Publish.

Publish flags (all optional — omit to stay local):
  workspace        Power BI workspace name or GUID
  xmla_endpoint    XMLA endpoint URL (Premium/Fabric only)
  overwrite        Overwrite existing report in workspace
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from tableau_to_pbi.parsers.twb_parser import parse_twb
from tableau_to_pbi.generators.mquery_generator import generate_m_queries
from tableau_to_pbi.generators.dax_generator import generate_dax_measures
from tableau_to_pbi.generators.visual_generator import generate_report_pages
from tableau_to_pbi.generators.report_writer import write_outputs
from tableau_to_pbi.generators.pbix_assembler import assemble_pbix, build_bim
from tableau_to_pbi.validators.coverage_validator import validate
from tableau_to_pbi.utils.models import PBIOutput

log = logging.getLogger(__name__)


def migrate_workbook(
    twb_path: Path,
    output_dir: Path,
    use_llm: bool = True,
    workspace: Optional[str] = None,
    xmla_endpoint: Optional[str] = None,
    overwrite: bool = True,
) -> dict:
    """
    Full migration pipeline for one .twb / .twbx file.
    Set workspace= to also publish to Power BI Service.
    Returns a dict with summary info.
    """
    log.info("═" * 60)
    log.info("Migrating: %s", twb_path.name)

    # Stage 1: Parse
    log.info("[1/6] Parsing Tableau workbook …")
    ir = parse_twb(twb_path)

    # Stage 2: Generate M queries
    log.info("[2/6] Generating Power Query M …")
    m_queries = generate_m_queries(ir.datasources)

    # Stage 3: Generate DAX
    log.info("[3/6] Generating DAX measures …")
    dax_measures = generate_dax_measures(ir, use_llm=use_llm)

    # Stage 4: Generate visuals / layout
    log.info("[4/6] Mapping visuals and layout …")
    report_pages = generate_report_pages(ir)

    output = PBIOutput(
        workbook_name=ir.workbook_name,
        m_queries=m_queries,
        dax_measures=dax_measures,
        report_pages=report_pages,
        parameters=[p.model_dump() for p in ir.parameters],
    )

    # Stage 5: Validate + write artefacts + assemble PBIX
    log.info("[5/6] Validating and writing outputs …")
    validation = validate(ir, output)
    out_dir = write_outputs(ir, output, validation, output_dir)

    # Assemble PBIX file
    pbix_path = out_dir / f"{ir.workbook_name}.pbix"
    assemble_pbix(output, pbix_path)

    # Write BIM (semantic model) for XMLA/REST deployment
    import json as _json
    bim = build_bim(output)
    bim_path = out_dir / f"{ir.workbook_name}.bim"
    bim_path.write_text(_json.dumps(bim, indent=2), encoding="utf-8")
    log.info("BIM written → %s", bim_path)

    summary = {
        "workbook":         ir.workbook_name,
        "source":           str(twb_path),
        "output_dir":       str(out_dir),
        "pbix_path":        str(pbix_path),
        "datasources":      len(ir.datasources),
        "worksheets":       len(ir.worksheets),
        "dashboards":       len(ir.dashboards),
        "m_queries":        len(m_queries),
        "dax_measures":     len(dax_measures),
        "report_pages":     len(report_pages),
        "field_coverage":   f"{validation.field_coverage_pct}%",
        "visual_coverage":  f"{validation.visual_coverage_pct}%",
        "overall_coverage": f"{validation.overall_coverage_pct}%",
        "errors":           len([i for i in validation.issues if i.severity == "ERROR"]),
        "warnings":         len([i for i in validation.issues if i.severity == "WARNING"]),
        "report_url":       "",
    }

    # Stage 6: Publish to Power BI Service (optional)
    if workspace:
        log.info("[6/6] Publishing to Power BI Service …")
        try:
            from tableau_to_pbi.generators.pbi_publisher import publish
            pub = publish(
                pbix_path=pbix_path,
                bim=bim,
                workbook_name=ir.workbook_name,
                workspace=workspace,
                xmla_endpoint=xmla_endpoint,
                overwrite=overwrite,
            )
            summary["report_url"] = pub.get("report_url", "")
            summary["dataset_id"] = pub.get("dataset_id", "")
        except Exception as e:
            log.error("Publish failed (artefacts still written locally): %s", e)
            summary["publish_error"] = str(e)
    else:
        log.info("[6/6] Skipping publish (no --workspace set)")

    log.info("Done. Coverage: %s | Errors: %d | Warnings: %d | PBIX: %s",
             summary["overall_coverage"], summary["errors"], summary["warnings"],
             pbix_path.name)
    return summary


def migrate_batch(
    input_dir: Path,
    output_dir: Path,
    use_llm: bool = True,
    workspace: Optional[str] = None,
    xmla_endpoint: Optional[str] = None,
    overwrite: bool = True,
) -> list[dict]:
    """Migrate all .twb / .twbx files in a directory."""
    files = list(input_dir.glob("*.twb")) + list(input_dir.glob("*.twbx"))
    if not files:
        log.warning("No .twb / .twbx files found in %s", input_dir)
        return []

    log.info("Found %d workbook(s) in %s", len(files), input_dir)
    summaries: list[dict] = []

    for f in sorted(files):
        try:
            s = migrate_workbook(
                f, output_dir,
                use_llm=use_llm,
                workspace=workspace,
                xmla_endpoint=xmla_endpoint,
                overwrite=overwrite,
            )
            summaries.append(s)
        except Exception as e:
            log.error("Failed to migrate %s: %s", f.name, e, exc_info=True)
            summaries.append({"workbook": f.stem, "source": str(f), "error": str(e)})

    return summaries
