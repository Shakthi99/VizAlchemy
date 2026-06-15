"""
PBIX / PBIP Assembler — builds a deployable Power BI file from generated artifacts.

Supports TWO output formats:
  1. .pbix  — classic ZIP format, opened directly by Power BI Desktop (any version)
  2. .pbip  — Power BI Project folder format (PBIR), requires PBI Desktop May 2023+

The .pbip format requires these files inside the ZIP:
  <Name>.Report/
    definition.pbir          ← THE FILE THAT WAS MISSING — causes the error you saw
    report.json              ← visual layout (PBIR schema)
  <Name>.Dataset/
    definition.pbidataset    ← dataset reference
    model.bim                ← tabular model (optional, for embedded datasets)
  .platform                  ← workspace metadata

The classic .pbix format (recommended for maximum compatibility) uses:
  [Content_Types].xml
  Version
  DataMashup
  Report/Layout
  SecurityBindings
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path

from tableau_to_pbi.utils.models import PBIOutput, PBIReportPage, PBIVisual

log = logging.getLogger(__name__)

# Power BI canvas reference size (points at 100% zoom)
PBI_CANVAS_W = 1280.0
PBI_CANVAS_H = 720.0

# ── Content Types ──────────────────────────────────────────────────────────────

_CONTENT_TYPES_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="xml"  ContentType="application/xml" />
  <Override PartName="/DataMashup"   ContentType="application/octet-stream" />
  <Override PartName="/Report/Layout" ContentType="application/json" />
</Types>"""

_VERSION = "4.21"   # Minimum PBIX format version accepted by PBI Service

# ── Field parser ─────────────────────────────────────────────────────────────

_AGG_RE = re.compile(
    r'^(SUM|AVG|AVERAGE|COUNT|COUNTD|MIN|MAX|MEDIAN)\((.+)\)$', re.IGNORECASE
)
# Power BI aggregation function codes
_AGG_FUNC_CODE: dict[str, int] = {
    "SUM":     0,  # Sum
    "AVG":     1,  # Average
    "AVERAGE": 1,
    "COUNT":   2,  # Count
    "COUNTD":  2,  # DistinctCount (PBI code 6, use 2 as safe fallback)
    "MIN":     3,  # Min
    "MAX":     4,  # Max
    "MEDIAN":  6,  # Median
}


def _parse_field(f: str) -> tuple:
    """Parse a Tableau field string into a (kind, ...) tuple.

    Returns:
      ('agg', inner_field, func_code, normalized_name)  for aggregations
      ('col', field_name)                               for plain columns
    """
    m = _AGG_RE.match(f.strip())
    if m:
        agg = m.group(1).upper()
        inner = m.group(2).strip()
        func_code = _AGG_FUNC_CODE.get(agg, 0)
        # PBI naming: "Sum(Sales)", "Average(Profit)", etc.
        norm = f"{agg[0].upper()}{agg[1:].lower()}({inner})"
        return ("agg", inner, func_code, norm)
    return ("col", f.strip())


def _collect_select_entries(
    vis, alias: str
) -> tuple[list[dict], dict[str, str]]:
    """Return (select_entries, field_to_queryref) for a visual's fields.

    select_entries  — Power BI Select[] items for prototypeQuery / SemanticQuery
    field_to_queryref — original field string -> queryRef name (for projections)
    """
    select_entries: list[dict] = []
    seen: set[str] = set()
    field_to_queryref: dict[str, str] = {}

    for fields in vis.fields.values():
        for field_str in fields:
            parsed = _parse_field(field_str)
            if parsed[0] == "agg":
                _, inner, func_code, norm_name = parsed
                field_to_queryref[field_str] = norm_name
                if norm_name not in seen:
                    seen.add(norm_name)
                    select_entries.append({
                        "Aggregation": {
                            "Expression": {
                                "Column": {
                                    "Expression": {"SourceRef": {"Source": alias}},
                                    "Property": inner,
                                }
                            },
                            "Function": func_code,
                        },
                        "Name": norm_name,
                    })
            else:
                _, col_name = parsed
                field_to_queryref[field_str] = col_name
                if col_name not in seen:
                    seen.add(col_name)
                    select_entries.append({
                        "Column": {
                            "Expression": {"SourceRef": {"Source": alias}},
                            "Property": col_name,
                        },
                        "Name": col_name,
                    })

    return select_entries, field_to_queryref


# ── Visual config builder ──────────────────────────────────────────────────────

_PBI_VISUAL_TYPE: dict[str, str] = {
    "barChart":      "barChart",
    "columnChart":   "columnChart",
    "lineChart":     "lineChart",
    "areaChart":     "areaChart",
    "scatterChart":  "scatterChart",
    "pieChart":      "pieChart",
    "donutChart":    "donutChart",
    "filledMap":     "filledMap",
    "map":           "map",
    "tableEx":       "tableEx",
    "matrix":        "pivotTable",
    "card":          "card",
    "multiRowCard":  "multiRowCard",
    "slicer":        "slicer",
    "gantt":         "gantt",
    "shapeMap":      "shapeMap",
    "columnChart":         "columnChart",
    "stackedBarChart":     "stackedBarChart",
    "clusteredBarChart":   "clusteredBarChart",
    "lineClusteredColumnComboChart": "lineClusteredColumnComboChart",
}

_DATA_ROLES: dict[str, dict[str, str]] = {
    "barChart":    {"axis": "Category", "values": "Y", "legend": "Series"},
    "columnChart": {"axis": "Category", "values": "Y", "legend": "Series"},
    "clusteredBarChart":   {"axis": "Category", "values": "Y", "legend": "Series"},
    "clusteredColumnChart":{"axis": "Category", "values": "Y", "legend": "Series"},
    "columnChart":         {"axis": "Category", "values": "Y", "legend": "Series"},
    "stackedBarChart":     {"axis": "Category", "values": "Y", "legend": "Series"},
    "lineChart":   {"axis": "Category", "values": "Y", "legend": "Series"},
    "areaChart":   {"axis": "Category", "values": "Y", "legend": "Series"},
    # Combo chart: Y = column bars, Y2 = line series
    "lineClusteredColumnComboChart": {"axis": "Category", "values": "Y", "values2": "Y2", "legend": "Series"},
    "scatterChart":{"axis": "X", "values": "Y", "legend": "Legend", "size": "Size"},
    "pieChart":    {"axis": "Category", "values": "Y", "legend": "Legend"},
    "donutChart":  {"axis": "Category", "values": "Y", "legend": "Legend"},
    "filledMap":   {"axis": "Location", "values": "Y", "legend": "Legend"},
    "map":         {"axis": "Location", "values": "Y", "legend": "Legend"},
    "tableEx":     {"values": "Values"},
    "matrix":      {"axis": "Rows", "values": "Values", "legend": "Columns"},
    "card":        {"values": "cardMeasures"},
    "multiRowCard":{"values": "cardMeasures"},
    "slicer":      {"axis": "Field"},
}


def _build_visual_config(vis: PBIVisual, page_id: str, vis_idx: int) -> str:
    pbi_type = _PBI_VISUAL_TYPE.get(vis.visual_type, vis.visual_type)
    role_map = _DATA_ROLES.get(vis.visual_type, {})

    table_name = vis.table_name or "Table"
    alias = table_name[0].lower() if table_name else "t"

    select_entries, field_to_queryref = _collect_select_entries(vis, alias)

    # Build projections using queryRef values aligned with Select[*].Name
    projections: dict[str, list[dict]] = {}
    for well, fields in vis.fields.items():
        role = role_map.get(well, well)
        refs = [{"queryRef": field_to_queryref.get(f, f)} for f in fields]
        if refs:
            projections[role] = refs

    config = {
        "name": f"visual_{page_id}_{vis_idx}",
        "layouts": [{"id": 0, "position": {
            "x": round(vis.x_pct / 100 * PBI_CANVAS_W),
            "y": round(vis.y_pct / 100 * PBI_CANVAS_H),
            "z": vis_idx,
            "width":  round(vis.w_pct / 100 * PBI_CANVAS_W),
            "height": round(vis.h_pct / 100 * PBI_CANVAS_H),
        }}],
        "singleVisual": {
            "visualType": pbi_type,
            "projections": projections,
            "prototypeQuery": {
                "Version": 2,
                "From": [{"Name": alias, "Entity": table_name, "Type": 0}],
                "Select": select_entries,
            },
            "vcObjects": {
                "title": [{"properties": {
                    "text": {"expr": {"Literal": {"Value": f"'{vis.title}'"}}},
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                }}],
            },
        },
    }
    return json.dumps(config)


def _build_semantic_query_cmd(vis: PBIVisual) -> str:
    """Build the container-level SemanticQueryDataShapeCommand JSON string."""
    table_name = vis.table_name or "Table"
    alias = table_name[0].lower() if table_name else "t"

    select_entries, _ = _collect_select_entries(vis, alias)

    if not select_entries:
        return "{}"

    return json.dumps({
        "Commands": [{
            "SemanticQueryDataShapeCommand": {
                "Query": {
                    "Version": 2,
                    "From": [{"Name": alias, "Entity": table_name, "Type": 0}],
                    "Select": select_entries,
                },
                "Binding": {
                    "Primary": {
                        "Groupings": [{"Projections": list(range(len(select_entries)))}]
                    },
                    "DataReduction": {
                        "DataVolume": 3,
                        "Primary": {"Window": {"Count": 1000}},
                    },
                    "Version": 1,
                },
            }
        }]
    })


def _build_filter_config(filters: list[dict]) -> str:
    if not filters:
        return "[]"
    pbi_filters = []
    for f in filters:
        pbi_filters.append({
            "type": "Categorical",
            "displaySettings": {},
            "target": {"column": f.get("field", ""), "table": ""},
            "filterType": 1,
            "operator": "In",
            "values": f.get("values", []),
        })
    return json.dumps(pbi_filters)


# ── Report/Layout builder (shared by both formats) ────────────────────────────

def _build_layout(output: PBIOutput) -> str:
    """Build the full Report/Layout JSON string (classic PBIX format)."""
    sections = []
    for page_idx, page in enumerate(output.report_pages):
        page_id = f"page{page_idx + 1:04d}"
        containers = []
        for vis_idx, vis in enumerate(page.visuals):
            x = round(vis.x_pct / 100 * PBI_CANVAS_W)
            y = round(vis.y_pct / 100 * PBI_CANVAS_H)
            w = round(vis.w_pct / 100 * PBI_CANVAS_W) or 400
            h = round(vis.h_pct / 100 * PBI_CANVAS_H) or 300

            containers.append({
                "x": x, "y": y, "z": vis_idx,
                "width": w, "height": h,
                "config":  _build_visual_config(vis, page_id, vis_idx),
                "filters": _build_filter_config(vis.filters),
                "query":   _build_semantic_query_cmd(vis),
                "dataTransforms": "{}",
            })

        sections.append({
            "id": page_idx,
            "name": page_id,
            "displayName": page.name,
            "filters": "[]",
            "ordinal": page_idx,
            "visualContainers": containers,
            "config": json.dumps({
                "relationships": [],
                "objects": {"page": [{"properties": {
                    "width":  {"expr": {"Literal": {"Value": str(int(PBI_CANVAS_W))}}},
                    "height": {"expr": {"Literal": {"Value": str(int(PBI_CANVAS_H))}}},
                }}]},
            }),
        })

    layout = {
        "id": 0,
        "resourcePackages": [],
        "sections": sections,
        "config": json.dumps({
            "version": "5.47",
            "themeCollection": {"baseTheme": {"name": "CY24SU08", "version": "5.47"}},
        }),
        "layoutOptimization": 0,
    }
    return json.dumps(layout, indent=2)


# ── DataMashup builder ─────────────────────────────────────────────────────────

def _build_mashup_section(output: PBIOutput) -> str:
    lines = ["section Section1;", ""]
    for q in output.m_queries:
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in q.table_name)
        lines.append(f"shared #\"{q.table_name}\" = ")
        indented = "\n".join("    " + l for l in q.m_expression.splitlines())
        lines.append(indented + ";")
        lines.append("")
    return "\n".join(lines)


def _build_mashup_zip(output: PBIOutput) -> bytes:
    section_m = _build_mashup_section(output)
    content_types = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="m" ContentType="application/vnd.ms-excel.query" />'
        '</Types>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("Section1.m", section_m)
        zf.writestr(
            "Formulas/Section1/Package/Formulas/Section1.m",
            section_m,
        )
        zf.writestr("Config/Package.json", json.dumps({
            "version": "2.0",
            "culture": "en-US",
        }))
    return buf.getvalue()


# ── BIM builder ───────────────────────────────────────────────────────────────

def build_bim(output: PBIOutput) -> dict:
    tables = []
    measure_table = {
        "name": "_Measures",
        "isHidden": True,
        "columns": [{"name": "Placeholder", "dataType": "string", "isHidden": True}],
        "partitions": [{"name": "_Measures", "mode": "import",
                        "source": {"type": "m", "expression": [
                            'let', '    t = #table({"x"}, {{{""}}})', 'in', '    t'
                        ]}}],
        "measures": [],
    }

    for m in output.dax_measures:
        measure_table["measures"].append({
            "name": m.name,
            "expression": m.expression,
            "formatString": m.format_string or "#,0.00",
            "annotations": [
                {"name": "SourceFormula", "value": m.source_formula[:500]},
                {"name": "Confidence",    "value": str(m.confidence)},
                {"name": "NeedsReview",   "value": str(m.needs_review)},
            ],
        })
    tables.append(measure_table)

    for q in output.m_queries:
        tables.append({
            "name": q.table_name,
            "partitions": [{
                "name": q.table_name,
                "mode": "import" if q.connection_type == "Import" else "directQuery",
                "source": {
                    "type": "m",
                    "expression": q.m_expression.splitlines(),
                },
            }],
            "columns": [],
        })

    return {
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"fastCombine": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "tables": tables,
            "relationships": [],
            "annotations": [
                {"name": "PBIDesktopVersion", "value": "auto-generated"},
                {"name": "GeneratedBy",        "value": "Tableau→PBI Accelerator"},
            ],
        },
    }


# ── Classic .pbix assembler ───────────────────────────────────────────────────

def assemble_pbix(output: PBIOutput, out_path: Path) -> Path:
    """
    Assemble and write a .pbix file to out_path.
    This is the RECOMMENDED format — maximum compatibility with all
    Power BI Desktop versions and Power BI Service.
    Returns the path to the written file.
    """
    out_path = Path(out_path)
    # Enforce .pbix extension — prevents the definition.pbir error
    if out_path.suffix.lower() != ".pbix":
        out_path = out_path.with_suffix(".pbix")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    layout_json  = _build_layout(output)
    mashup_bytes = _build_mashup_zip(output)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES_XML)
        zf.writestr("Version",             _VERSION)
        zf.writestr("SecurityBindings",    "")
        zf.writestr("DataMashup",          mashup_bytes)
        zf.writestr("Report/Layout",       layout_json)

    log.info("PBIX assembled → %s  (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path


# ── PBIP (.pbip zip) assembler ────────────────────────────────────────────────
#
# Use this ONLY if you specifically need the Power BI Project (PBIR) format.
# Requires Power BI Desktop May 2023 or later.
# The error "Required artifact is missing definition.pbir" happens when a file
# is incorrectly named/structured as PBIP without this file present.

def assemble_pbip(output: PBIOutput, out_path: Path, report_name: str) -> Path:
    """
    Assemble a .pbip-compatible ZIP with the full PBIR folder structure.

    Internal ZIP layout:
      .platform
      {report_name}.Report/
          definition.pbir          ← REQUIRED — was missing, caused the error
          report.json              ← visual layout in PBIR schema
      {report_name}.Dataset/
          definition.pbidataset    ← dataset metadata
          model.bim                ← embedded tabular model (BIM)

    Returns the path to the written zip file.
    """
    out_path = Path(out_path)
    # Always use .pbip extension for this format
    if out_path.suffix.lower() != ".pbip":
        out_path = out_path.with_suffix(".pbip")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitise report name for use as folder names inside the ZIP
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in report_name).strip()
    if not safe_name:
        safe_name = "Report"

    report_folder  = f"{safe_name}.Report"
    dataset_folder = f"{safe_name}.Dataset"

    # ── 1. definition.pbir  ──────────────────────────────────────────────────
    # This is the file that was MISSING and caused the error.
    # It tells Power BI Desktop where the dataset lives (by relative path).
    definition_pbir = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/1.0.0/schema.json",
        "version": "1.0",
        "datasetReference": {
            "byPath": {
                "path": f"../{dataset_folder}"
            },
            "byConnection": None,
        },
    }

    # ── 2. report.json  ──────────────────────────────────────────────────────
    # PBIR uses a different schema from classic Report/Layout.
    # We convert our internal page/visual model to the PBIR format.
    report_json = _build_pbir_report_json(output, safe_name)

    # ── 3. definition.pbidataset  ────────────────────────────────────────────
    definition_pbidataset = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/dataset/definition/1.0.0/schema.json",
        "version": "1.0",
        "mode": "import",
    }

    # ── 4. model.bim  ────────────────────────────────────────────────────────
    bim = build_bim(output)

    # ── 5. .platform  ────────────────────────────────────────────────────────
    platform_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Report",
            "displayName": report_name,
        },
        "config": {
            "version": "2.0",
            "logicalId": "",
        },
    }

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Platform metadata at root
        zf.writestr(".platform", json.dumps(platform_json, indent=2))

        # Report folder — definition.pbir is the critical missing file
        zf.writestr(
            f"{report_folder}/definition.pbir",
            json.dumps(definition_pbir, indent=2),
        )
        zf.writestr(
            f"{report_folder}/report.json",
            json.dumps(report_json, indent=2),
        )

        # Dataset folder
        zf.writestr(
            f"{dataset_folder}/definition.pbidataset",
            json.dumps(definition_pbidataset, indent=2),
        )
        zf.writestr(
            f"{dataset_folder}/model.bim",
            json.dumps(bim, indent=2),
        )

    log.info("PBIP assembled → %s  (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path


def _build_pbir_report_json(output: PBIOutput, report_name: str) -> dict:
    """
    Convert our internal page/visual model to PBIR report.json schema.
    PBIR uses a different (newer) JSON structure than classic Report/Layout.
    """
    pages = []
    for page_idx, page in enumerate(output.report_pages):
        page_id = f"ReportSection{page_idx + 1}"
        visuals = []

        for vis_idx, vis in enumerate(page.visuals):
            pbi_type = _PBI_VISUAL_TYPE.get(vis.visual_type, vis.visual_type)
            role_map = _DATA_ROLES.get(vis.visual_type, {})

            projections: dict[str, list[dict]] = {}
            for well, fields in vis.fields.items():
                role = role_map.get(well, well)
                projections[role] = [{"queryRef": f} for f in fields]

            x = round(vis.x_pct / 100 * PBI_CANVAS_W)
            y = round(vis.y_pct / 100 * PBI_CANVAS_H)
            w = max(round(vis.w_pct / 100 * PBI_CANVAS_W), 100)
            h = max(round(vis.h_pct / 100 * PBI_CANVAS_H), 80)

            visuals.append({
                "id": f"visual_{page_idx}_{vis_idx}",
                "position": {"x": x, "y": y, "z": vis_idx, "width": w, "height": h},
                "visual": {
                    "visualType": pbi_type,
                    "projections": projections,
                    "title": vis.title,
                },
            })

        pages.append({
            "id": page_id,
            "name": page.name,
            "displayName": page.name,
            "ordinal": page_idx,
            "width": int(PBI_CANVAS_W),
            "height": int(PBI_CANVAS_H),
            "visuals": visuals,
            "filters": [],
        })

    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/1.0.0/schema.json",
        "version": "1.0",
        "reportId": "",
        "config": {
            "version": "5.47",
            "themeCollection": {"baseTheme": {"name": "CY24SU08", "version": "5.47"}},
        },
        "pages": pages,
    }