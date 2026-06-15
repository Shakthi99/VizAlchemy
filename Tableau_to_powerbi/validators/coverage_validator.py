"""
Coverage validator — checks field mapping completeness,
visual confidence, and produces a structured validation report.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from tableau_to_pbi.utils.models import TableauIR, PBIOutput


@dataclass
class ValidationIssue:
    severity: str           # ERROR | WARNING | INFO
    category: str           # field | visual | dax | layout | filter
    item: str
    message: str


@dataclass
class ValidationReport:
    workbook_name: str
    issues: list[ValidationIssue] = field(default_factory=list)

    # Coverage counts
    total_calculated_fields: int = 0
    translated_fields: int = 0
    fields_needing_review: int = 0

    total_visuals: int = 0
    visuals_auto: int = 0
    visuals_flagged: int = 0

    total_datasources: int = 0
    mapped_datasources: int = 0

    @property
    def field_coverage_pct(self) -> float:
        if not self.total_calculated_fields:
            return 100.0
        return round(self.translated_fields / self.total_calculated_fields * 100, 1)

    @property
    def visual_coverage_pct(self) -> float:
        if not self.total_visuals:
            return 100.0
        return round(self.visuals_auto / self.total_visuals * 100, 1)

    @property
    def overall_coverage_pct(self) -> float:
        weights = [(self.field_coverage_pct, 0.4), (self.visual_coverage_pct, 0.6)]
        return round(sum(v * w for v, w in weights), 1)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Workbook          : {self.workbook_name}",
            f"Overall Coverage  : {self.overall_coverage_pct}%",
            f"  Field Coverage  : {self.field_coverage_pct}%  "
            f"({self.translated_fields}/{self.total_calculated_fields} calculated fields)",
            f"  Visual Coverage : {self.visual_coverage_pct}%  "
            f"({self.visuals_auto}/{self.total_visuals} visuals auto-mapped)",
            f"  Datasources     : {self.mapped_datasources}/{self.total_datasources} mapped",
            "",
            f"Issues  : {len([i for i in self.issues if i.severity == 'ERROR'])} errors, "
            f"{len([i for i in self.issues if i.severity == 'WARNING'])} warnings",
        ]
        return lines


def validate(ir: TableauIR, output: PBIOutput) -> ValidationReport:
    report = ValidationReport(workbook_name=ir.workbook_name)

    # ── Datasource coverage ────────────────────────────────────────────────────
    report.total_datasources = len(ir.datasources)
    ir_ds_names = {ds.name for ds in ir.datasources}
    out_ds_names = {q.datasource_name for q in output.m_queries}
    report.mapped_datasources = len(ir_ds_names & out_ds_names)
    for ds_name in ir_ds_names - out_ds_names:
        report.issues.append(ValidationIssue(
            severity="ERROR", category="datasource", item=ds_name,
            message=f"Datasource '{ds_name}' has no M query generated",
        ))

    # ── Calculated field coverage ──────────────────────────────────────────────
    calc_fields = [
        (ds.caption or ds.name, col)
        for ds in ir.datasources
        for col in ds.columns
        if col.is_calculated
    ]
    report.total_calculated_fields = len(calc_fields)
    out_measure_names = {m.name for m in output.dax_measures}

    for table, col in calc_fields:
        measure_name = col.caption or col.name
        if measure_name in out_measure_names:
            report.translated_fields += 1
        else:
            report.issues.append(ValidationIssue(
                severity="WARNING", category="field", item=measure_name,
                message=f"Calculated field '{measure_name}' from '{table}' has no DAX measure",
            ))

    for m in output.dax_measures:
        if m.needs_review:
            report.fields_needing_review += 1
            report.issues.append(ValidationIssue(
                severity="WARNING", category="dax", item=m.name,
                message=f"DAX measure '{m.name}' needs review: {m.review_reason} (confidence={m.confidence:.0%})",
            ))
        if m.confidence == 0.0:
            report.issues.append(ValidationIssue(
                severity="ERROR", category="dax", item=m.name,
                message=f"DAX measure '{m.name}' could not be translated — original: {m.source_formula[:80]}",
            ))

    # ── Visual coverage ────────────────────────────────────────────────────────
    all_visuals = [v for page in output.report_pages for v in page.visuals]
    report.total_visuals = len(all_visuals)
    for vis in all_visuals:
        # FIX: visuals_auto tracks all mapped visuals (including flagged ones).
        # visuals_flagged is a sub-count for "mapped but needs review".
        # Previously, flagged visuals were excluded from visuals_auto, making
        # coverage % artificially low for workbooks with review notes.
        report.visuals_auto += 1
        if vis.needs_review:
            report.visuals_flagged += 1
            report.issues.append(ValidationIssue(
                severity="WARNING", category="visual", item=vis.source_worksheet,
                message=f"Visual '{vis.source_worksheet}' ({vis.visual_type}) flagged: {vis.review_reason}",
            ))

    # ── Worksheet to dashboard coverage ───────────────────────────────────────
    ws_names = {ws.name for ws in ir.worksheets}
    visuals_covered = {v.source_worksheet for page in output.report_pages for v in page.visuals}
    for ws_name in ws_names - visuals_covered:
        report.issues.append(ValidationIssue(
            severity="WARNING", category="layout", item=ws_name,
            message=f"Worksheet '{ws_name}' not placed on any report page",
        ))

    # ── Parameter coverage ─────────────────────────────────────────────────────
    if ir.parameters and not output.parameters:
        report.issues.append(ValidationIssue(
            severity="INFO", category="field", item="parameters",
            message=f"{len(ir.parameters)} Tableau parameter(s) detected — add as Power BI What-If parameters manually",
        ))

    return report
