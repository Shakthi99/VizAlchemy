"""
Visual generator — maps Tableau worksheets and dashboards into
Power BI report page / visual specs.
"""
from __future__ import annotations

import logging
from tableau_to_pbi.utils.models import (
    TableauIR,
    TableauWorksheet,
    TableauDashboard,
    DashboardObject,
    PBIVisual,
    PBIReportPage,
)
from tableau_to_pbi.utils.mappings import MARK_TO_VISUAL, SHELF_TO_WELL

log = logging.getLogger(__name__)

# PBI canvas dimensions (points)
PBI_W = 1280.0
PBI_H = 720.0


def _worksheet_to_visual(
    ws: TableauWorksheet,
    zone: DashboardObject | None,
    db_w: float,
    db_h: float,
    ds_table_map: dict[str, str] | None = None,
) -> PBIVisual:
    mark = ws.mark_type.lower().replace(" ", "_")
    visual_type, confidence, note = MARK_TO_VISUAL.get(mark, ("barChart", 0.60, f"Unknown mark type: {mark}"))

    # Coordinate normalisation: Tableau px → PBI percentage
    if zone and db_w and db_h:
        x_pct = round((zone.x / db_w) * 100, 2)
        y_pct = round((zone.y / db_h) * 100, 2)
        w_pct = round((zone.w / db_w) * 100, 2)
        h_pct = round((zone.h / db_h) * 100, 2)
    else:
        x_pct = y_pct = 0.0
        w_pct = h_pct = 50.0

    # Resolve Power BI table name from the worksheet's datasource
    table_name = ""
    if ws.datasource:
        table_name = (ds_table_map or {}).get(ws.datasource, ws.datasource)

    # Build field wells
    fields: dict[str, list[str]] = {}
    for enc in ws.encodings:
        well = SHELF_TO_WELL.get(enc.shelf, enc.shelf)
        field_label = f"{enc.aggregation}({enc.field})" if enc.aggregation not in ("NONE", "") else enc.field
        fields.setdefault(well, []).append(field_label)

    # Filters
    pbi_filters = [
        {"field": f.field, "type": f.filter_type, "values": f.values}
        for f in ws.filters
    ]

    return PBIVisual(
        visual_type=visual_type,
        title=ws.name,
        x_pct=x_pct,
        y_pct=y_pct,
        w_pct=w_pct,
        h_pct=h_pct,
        fields=fields,
        filters=pbi_filters,
        source_worksheet=ws.name,
        table_name=table_name,
        confidence=confidence,
        needs_review=confidence < 0.70 or bool(note),
        review_reason=note,
    )


def generate_report_pages(ir: TableauIR) -> list[PBIReportPage]:
    ws_map: dict[str, TableauWorksheet] = {ws.name: ws for ws in ir.worksheets}
    # Map datasource internal name -> PBI table name (matches MQueryTable.table_name)
    ds_table_map: dict[str, str] = {
        ds.name: (ds.caption or ds.name) for ds in ir.datasources
    }
    pages: list[PBIReportPage] = []

    for db in ir.dashboards:
        page = PBIReportPage(name=db.name, source_dashboard=db.name)

        for obj in db.objects:
            if obj.object_type != "worksheet" or obj.name not in ws_map:
                continue
            ws = ws_map[obj.name]
            visual = _worksheet_to_visual(ws, obj, db.width, db.height, ds_table_map)
            page.visuals.append(visual)
            log.debug(
                "Visual [%s] type=%s confidence=%.2f",
                ws.name, visual.visual_type, visual.confidence,
            )

        pages.append(page)
        log.info("Report page [%s]: %d visuals", db.name, len(page.visuals))

    # Worksheets not on any dashboard → own page each
    on_dashboards: set[str] = {
        obj.name
        for db in ir.dashboards
        for obj in db.objects
        if obj.object_type == "worksheet"
    }
    for ws in ir.worksheets:
        if ws.name not in on_dashboards:
            visual = _worksheet_to_visual(ws, None, 0, 0, ds_table_map)
            pages.append(PBIReportPage(
                name=ws.name,
                visuals=[visual],
                source_dashboard="",
            ))

    return pages
