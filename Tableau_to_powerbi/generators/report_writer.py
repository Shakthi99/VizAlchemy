"""
Report writer — writes all generated artefacts to the output folder.

Output structure per workbook:
  output_pbi/{workbook_name}/
  ├── powerquery/           M queries (.pq files)
  ├── dax/                  DAX measures file
  ├── layout/               Report page visual specs (JSON)
  ├── migration_report/
  │   ├── summary.md
  │   ├── manual_review.md
  │   └── field_mapping.csv
  └── ir/
      └── {workbook}.ir.json
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from tableau_to_pbi.utils.models import TableauIR, PBIOutput
from tableau_to_pbi.validators.coverage_validator import ValidationReport

log = logging.getLogger(__name__)


def write_outputs(
    ir: TableauIR,
    output: PBIOutput,
    report: ValidationReport,
    out_dir: Path,
) -> Path:
    wb_dir = out_dir / ir.workbook_name
    pq_dir     = wb_dir / "powerquery"
    dax_dir    = wb_dir / "dax"
    layout_dir = wb_dir / "layout"
    rep_dir    = wb_dir / "migration_report"
    ir_dir     = wb_dir / "ir"

    for d in [pq_dir, dax_dir, layout_dir, rep_dir, ir_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # ── IR JSON ────────────────────────────────────────────────────────────────
    ir_path = ir_dir / f"{ir.workbook_name}.ir.json"
    ir_path.write_text(ir.model_dump_json(indent=2), encoding="utf-8")

    # ── Power Query M files ────────────────────────────────────────────────────
    for q in output.m_queries:
        safe_name = _safe(q.table_name)
        (pq_dir / f"{safe_name}.pq").write_text(q.m_expression, encoding="utf-8")

    # ── DAX measures ──────────────────────────────────────────────────────────
    dax_lines = ["-- Auto-generated DAX measures", "-- Review items marked with [REVIEW]", ""]
    for m in output.dax_measures:
        tag = " [REVIEW]" if m.needs_review else ""
        if m.source_formula:
            dax_lines.append(f"-- Source: {m.source_formula[:120]}")
        dax_lines.append(f"MEASURE {m.table}[{m.name}]{tag} =")
        dax_lines.append(f"    {m.expression}")
        if m.format_string:
            dax_lines.append(f'    FORMAT_STRING = "{m.format_string}"')
        dax_lines.append("")

    (dax_dir / "measures.dax").write_text("\n".join(dax_lines), encoding="utf-8")

    # ── Report page layout (JSON) ──────────────────────────────────────────────
    layout_data = [p.model_dump() for p in output.report_pages]
    (layout_dir / "report_pages.json").write_text(
        json.dumps(layout_data, indent=2), encoding="utf-8"
    )

    # ── Migration summary ──────────────────────────────────────────────────────
    summary_lines = [
        "# Tableau → Power BI Migration Summary",
        "",
        "## Coverage",
        "",
    ] + report.summary_lines() + [
        "",
        "## Source",
        f"- Workbook: `{ir.source_file}`",
        f"- Datasources: {len(ir.datasources)}",
        f"- Worksheets: {len(ir.worksheets)}",
        f"- Dashboards: {len(ir.dashboards)}",
        f"- Calculated fields: {report.total_calculated_fields}",
        f"- Parameters: {len(ir.parameters)}",
        "",
        "## Output Files",
        f"- `powerquery/` — {len(output.m_queries)} M query file(s)",
        f"- `dax/measures.dax` — {len(output.dax_measures)} DAX measure(s)",
        f"- `layout/report_pages.json` — {len(output.report_pages)} report page(s)",
        f"- `migration_report/field_mapping.csv` — full field lineage",
        "",
        "## Next Steps",
        "1. Open Power BI Desktop → `Get Data` → use M queries in `powerquery/`",
        "2. Paste measures from `dax/measures.dax` into the DAX editor",
        "3. Recreate visuals using `layout/report_pages.json` as a guide",
        "4. Address all items in `manual_review.md`",
        "5. Reconnect parameters as Power BI What-If parameters",
    ]
    (rep_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")

    # ── Manual review items ────────────────────────────────────────────────────
    errors   = [i for i in report.issues if i.severity == "ERROR"]
    warnings = [i for i in report.issues if i.severity == "WARNING"]
    infos    = [i for i in report.issues if i.severity == "INFO"]

    review_lines = ["# Manual Review Items", ""]
    if errors:
        review_lines += ["## Errors (must fix)", ""]
        for i in errors:
            review_lines.append(f"- **[{i.category.upper()}]** `{i.item}`: {i.message}")
        review_lines.append("")
    if warnings:
        review_lines += ["## Warnings (should fix)", ""]
        for i in warnings:
            review_lines.append(f"- **[{i.category.upper()}]** `{i.item}`: {i.message}")
        review_lines.append("")
    if infos:
        review_lines += ["## Info", ""]
        for i in infos:
            review_lines.append(f"- `{i.item}`: {i.message}")

    (rep_dir / "manual_review.md").write_text("\n".join(review_lines), encoding="utf-8")

    # ── Field mapping CSV ──────────────────────────────────────────────────────
    csv_path = rep_dir / "field_mapping.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Source Table", "Tableau Field", "Type", "Is Calculated",
            "Tableau Formula", "DAX Measure", "DAX Expression",
            "Confidence", "Needs Review", "Review Reason",
        ])
        dax_by_name = {m.name: m for m in output.dax_measures}
        for ds in ir.datasources:
            table = ds.caption or ds.name
            for col in ds.columns:
                m = dax_by_name.get(col.caption or col.name)
                writer.writerow([
                    table,
                    col.caption or col.name,
                    col.datatype,
                    col.is_calculated,
                    col.formula if col.is_calculated else "",
                    m.name if m else "",
                    m.expression[:200] if m else "",
                    f"{m.confidence:.0%}" if m else "",
                    m.needs_review if m else "",
                    m.review_reason if m else "",
                ])

    log.info("Outputs written to: %s", wb_dir)
    return wb_dir


def _safe(name: str) -> str:
    # FIX: strip leading/trailing underscores and fall back to "unnamed" to prevent
    # empty filenames or all-underscore collisions from non-ASCII datasource names
    result = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
    return result or "unnamed"
