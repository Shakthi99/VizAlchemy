"""Pipeline orchestrator - coordinates the full Tableau → Power BI migration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from tableau_to_powerbi.config import CONFIG
from tableau_to_powerbi.ir import WorkbookIR, MeasureIR
from tableau_to_powerbi.parser import parse_twb
from tableau_to_powerbi.translation import generate_measures_for_workbook
from tableau_to_powerbi.mapping import map_all_worksheets, VisualSpec
from tableau_to_powerbi.generator.semantic_model import (
    generate_model_tmdl,
    generate_database_tmdl,
    generate_tables_tmdl,
    generate_table_files,
    generate_relationships_tmdl,
)
from tableau_to_powerbi.generator.report_generator import generate_report_json, _derive_dashboard_title
from tableau_to_powerbi.generator.pbip_packager import package_pbip

logger = logging.getLogger("tableau_to_powerbi.pipeline")


@dataclass
class PipelineResult:
    """Result of the migration pipeline."""
    success: bool = False
    pbip_bytes: Optional[bytes] = None
    workbook_ir: Optional[WorkbookIR] = None
    measures: list[MeasureIR] = field(default_factory=list)
    visuals: list[VisualSpec] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def worksheets_count(self) -> int:
        if self.workbook_ir:
            return len(self.workbook_ir.worksheets)
        return 0

    @property
    def tables_count(self) -> int:
        if self.workbook_ir and self.workbook_ir.datasources:
            return sum(len(ds.tables) for ds in self.workbook_ir.datasources)
        return 0

    @property
    def measures_count(self) -> int:
        return len(self.measures)

    @property
    def visuals_count(self) -> int:
        return len(self.visuals)


def run_pipeline(
    twb_bytes: bytes,
    filename: str = "",
    project_name: Optional[str] = None,
    data_directory: Optional[str] = None,
) -> PipelineResult:
    """
    Run the full Tableau → Power BI migration pipeline.

    Args:
        twb_bytes: Raw bytes of the .twb file
        filename: Original filename
        project_name: Name for the PBI project (default: from config)
        data_directory: Path where CSV data files are located

    Returns:
        PipelineResult with the generated PBIP archive
    """
    result = PipelineResult()
    # Derive project name from filename if not explicitly provided
    if project_name:
        proj_name = project_name
    elif filename:
        import re as _re
        # Strip extension, clean up non-alphanumeric chars
        base = filename.rsplit(".", 1)[0].strip()
        # Remove parenthetical suffixes like " (1)"
        base = _re.sub(r"\s*\(\d+\)\s*$", "", base)
        proj_name = base.replace(" ", "") + "Report" if base else CONFIG.project_name
    else:
        proj_name = CONFIG.project_name
    data_dir = data_directory or CONFIG.default_data_directory

    try:
        # Phase 1: Parse Tableau workbook
        logger.info("Phase 1: Parsing Tableau workbook '%s'", filename)
        ir = parse_twb(twb_bytes, filename)
        result.workbook_ir = ir

        # Use data directory from TWB only if it exists on this machine
        # and the user hasn't explicitly overridden
        if ir.data_directory and (
            not data_directory or data_directory == CONFIG.default_data_directory
        ):
            import os
            if os.path.isdir(ir.data_directory):
                data_dir = ir.data_directory
                logger.info("Using data directory from TWB: %s", data_dir)
            else:
                logger.warning(
                    "TWB data directory '%s' not found on this machine, using '%s'",
                    ir.data_directory, data_dir,
                )

        if not ir.worksheets:
            result.warnings.append("No worksheets found in workbook")

        # Phase 2: Generate DAX measures
        logger.info("Phase 2: Generating DAX measures")
        measures = generate_measures_for_workbook(ir)
        result.measures = measures

        # Phase 3: Map visuals
        logger.info("Phase 3: Mapping visuals")
        visuals = map_all_worksheets(ir.worksheets)
        result.visuals = visuals

        # Phase 4: Generate TMDL
        logger.info("Phase 4: Generating semantic model (TMDL)")
        model_tmdl = generate_model_tmdl(ir=ir)
        database_tmdl = generate_database_tmdl(proj_name)
        table_files = generate_table_files(
            measures=measures,
            calculated_fields=ir.calculated_fields,
            data_directory=data_dir,
            ir=ir,
        )
        relationships_tmdl = generate_relationships_tmdl(ir=ir)
        tables_tmdl = generate_tables_tmdl(
            measures=measures,
            calculated_fields=ir.calculated_fields,
            data_directory=data_dir,
            ir=ir,
        )

        # Phase 5: Generate report.json
        logger.info("Phase 5: Generating report layout")
        # Extract dashboard name for title migration
        dashboard_name = ir.dashboards[0].name if ir.dashboards else ""
        # Build set of measure names for proper Column vs Measure distinction
        measure_name_set = {m.name for m in measures}
        # Derive page name from dashboard or workbook name
        page_display_name = _derive_dashboard_title(dashboard_name) if dashboard_name else ir.name
        report_json = generate_report_json(
            visuals,
            dashboard_name=dashboard_name,
            measure_names=measure_name_set,
            page_name=page_display_name,
        )

        # Phase 6: Package
        logger.info("Phase 6: Packaging PBIP archive")
        pbip_bytes = package_pbip(
            project_name=proj_name,
            model_tmdl=model_tmdl,
            database_tmdl=database_tmdl,
            tables_tmdl=tables_tmdl,
            report_json=report_json,
            table_files=table_files,
            relationships_tmdl=relationships_tmdl,
        )

        result.pbip_bytes = pbip_bytes
        result.success = True
        logger.info("Pipeline completed successfully")

    except Exception as e:
        logger.error("Pipeline failed: %s", str(e), exc_info=True)
        result.errors.append(str(e))
        result.success = False

    return result
