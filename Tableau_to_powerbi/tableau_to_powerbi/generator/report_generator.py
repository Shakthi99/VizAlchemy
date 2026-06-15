"""Power BI report.json generator."""

from __future__ import annotations

import json
import logging
from typing import Any

from tableau_to_powerbi.mapping import VisualSpec
from tableau_to_powerbi.config import CONFIG

logger = logging.getLogger("tableau_to_powerbi.generator")

# ---------------------------------------------------------------------------
# Power BI data-role name normalisation
# ---------------------------------------------------------------------------
# PBI uses different role names per visual type.  Any upstream code that uses
# a generic "Values" key must be remapped before being written to report.json
# otherwise PBI shows an empty / greyed-out visual with no data bound to it.
#
# This table maps generic/incorrect role names → correct PBI internal names.
# If projections already use the correct PBI names (as set in WORKSHEET_PROJECTIONS),
# these remappings will simply not trigger (passthrough via remap.get(role, role)).
#
# Correct PBI role names per visual type:
#   card:                   "Fields"
#   bar/column/line/area:   "Category", "Y", "Series"
#   pie/donut:              "Category", "Y"
#   treemap:                "Group", "Values"
#   pivotTable (matrix):    "Rows", "Columns", "Values"
#   map:                    "Category" (location), "Size" (bubble)
#   filledMap:              "Category" (location), "Values" (color saturation)
#   scatter:                "X", "Y", "Details", "Size", "Legend"
#   combo (line+column):    "Category", "Y", "Y2"
# ---------------------------------------------------------------------------
_PBI_ROLE_NORM: dict[str, dict[str, str]] = {
    "clusteredBarChart":       {"Values": "Y"},
    "clusteredColumnChart":    {"Values": "Y"},
    "stackedBarChart":         {"Values": "Y"},
    "columnChart":             {"Values": "Y"},
    "hundredPercentStackedBarChart":    {"Values": "Y"},
    "hundredPercentStackedColumnChart": {"Values": "Y"},
    "lineChart":               {"Values": "Y"},
    "areaChart":               {"Values": "Y"},
    "lineClusteredColumnComboChart": {"Values": "Y"},
    "pieChart":                {"Values": "Y"},
    "donutChart":              {"Values": "Y"},
    "treemap":                 {"Category": "Group"},
    "scatterChart":            {"Category": "Details"},
    "map":                     {"Location": "Category"},
    "filledMap":               {"Location": "Category"},
    "shapeMap":                {"Location": "Category"},
    "ribbonChart":             {"Values": "Y"},
    "waterfallChart":          {"Values": "Y"},
    "funnel":                  {"Values": "Y"},
    "card":                    {"Values": "Fields"},
    "pivotTable":              {},
}


def _normalize_projections(
    projections: dict[str, list[dict[str, str]]],
    visual_type: str,
) -> dict[str, list[dict[str, str]]]:
    """Remap generic role names to the PBI-specific names for this visual type."""
    remap = _PBI_ROLE_NORM.get(visual_type, {})
    if not remap:
        return projections
    result: dict[str, list[dict[str, str]]] = {}
    for role, items in projections.items():
        new_role = remap.get(role, role)
        # If two original roles map to the same PBI role, merge their fields
        result.setdefault(new_role, []).extend(items)
    return result


def _derive_dashboard_title(dashboard_name: str) -> str:
    """Derive a human-readable title from the dashboard name or dataset context.

    If the dashboard name is a camelCase/PascalCase code name (e.g. 'ShoppingDash'),
    split it into words and clean it up. If no usable name exists, generate a
    generic title.
    """
    import re
    if not dashboard_name:
        return "Analytics Dashboard"

    # Split camelCase/PascalCase into words
    words = re.sub(r'([a-z])([A-Z])', r'\1 \2', dashboard_name)
    words = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', words)
    # Replace underscores/hyphens with spaces
    words = re.sub(r'[_\-]+', ' ', words).strip()

    # Remove filler suffixes like "Dash", "Dashboard", "DB"
    cleaned = re.sub(r'\b(Dash|Dashboard|DB)\b', '', words, flags=re.IGNORECASE).strip()
    if not cleaned:
        return "Analytics Dashboard"

    # Capitalize and append "Dashboard" if not already present
    cleaned = cleaned.title()
    if "dashboard" not in cleaned.lower():
        cleaned += " Dashboard"
    return cleaned


def _build_title_container(title: str, container_id: int) -> dict[str, Any]:
    """Build a Power BI textbox visual container for the dashboard title."""
    config = {
        "name": "Title_Textbox",
        "singleVisual": {
            "visualType": "textbox",
            "objects": {
                "general": [{
                    "properties": {
                        "paragraphs": [{
                            "textRuns": [{
                                "value": title,
                                "textStyle": {
                                    "fontFamily": "Segoe UI Semibold",
                                    "fontSize": "20px",
                                    "bold": True,
                                }
                            }]
                        }]
                    }
                }]
            },
        },
    }

    return {
        "id": container_id,
        "x": 8,
        "y": 8,
        "width": 1204,
        "height": 50,
        "z": 0,
        "config": json.dumps(config),
        "filters": "[]",
        "query": "{}",
        "dataTransforms": "{}",
    }


def generate_report_json(
    visuals: list[VisualSpec],
    dashboard_title: str | None = None,
    dashboard_name: str | None = None,
    measure_names: set[str] | None = None,
    page_name: str | None = None,
) -> str:
    """Generate the Power BI report.json content.

    Args:
        visuals: List of visual specifications to render.
        dashboard_title: Explicit title from Tableau dashboard (if present).
        dashboard_name: Dashboard code name from Tableau (used to derive title).
        measure_names: Set of measure names (used to distinguish measures from columns).
        page_name: Display name for the report page.
    """
    _page_name = page_name or CONFIG.page_name
    report_config = {
        "themeCollection": {
            "baseTheme": {"name": "CY24SU06", "version": "5.45", "type": 2}
        },
        "activeSectionIndex": 0,
    }

    # Determine title: use explicit title if provided, else derive from name
    title = dashboard_title or _derive_dashboard_title(dashboard_name or "")

    visual_containers = []
    # Add title textbox as the first visual
    title_container = _build_title_container(title, 0)
    visual_containers.append(title_container)

    _measure_names = measure_names or set()
    for i, vis in enumerate(visuals, 1):
        container = _build_visual_container(vis, i, _measure_names)
        visual_containers.append(container)

    report_dict: dict[str, Any] = {
        "config": json.dumps(report_config),
        "layoutOptimization": 0,
        "sections": [
            {
                "name": _page_name.replace(" ", ""),
                "displayName": _page_name,
                "width": CONFIG.canvas_width,
                "height": CONFIG.canvas_height,
                "displayOption": 1,
                "visualContainers": visual_containers,
            }
        ],
    }

    return json.dumps(report_dict, indent=2)


def _build_visual_container(vis: VisualSpec, index: int, measure_names: set[str] | None = None) -> dict[str, Any]:
    """Build a single visual container for report.json."""
    # Normalise projection role names to the PBI-specific names for this visual
    projections = _normalize_projections(vis.projections, vis.visual_type)

    proto_query = _build_raw_query(projections, measure_names=measure_names)
    semantic_query_cmd = _build_semantic_query_cmd(proto_query, projections)

    config = {
        "name": vis.name,
        "singleVisual": {
            "visualType": vis.visual_type,
            "projections": projections,
            "prototypeQuery": proto_query,
        },
    }

    return {
        "id": index,
        "x": vis.x,
        "y": vis.y,
        "width": vis.width,
        "height": vis.height,
        "z": index,
        "config": json.dumps(config),
        "filters": "[]",
        "query": json.dumps(semantic_query_cmd),
        "dataTransforms": "{}",
    }


def _make_alias(table_name: str, used: set[str]) -> str:
    """Generate a unique short alias for a table name."""
    base = table_name[0].lower() if table_name else "t"
    if base not in used:
        used.add(base)
        return base
    # Try first two chars, then first three, etc.
    for length in range(2, len(table_name) + 1):
        candidate = table_name[:length].lower()
        if candidate not in used:
            used.add(candidate)
            return candidate
    # Fallback: append a number
    i = 2
    while True:
        candidate = f"{base}{i}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        i += 1


def _build_raw_query(
    projections: dict[str, list[dict[str, str]]],
    measure_names: set[str] | None = None,
) -> dict[str, Any]:
    """Build prototypeQuery: {Version, From, Select} for singleVisual."""
    # Measure names are passed dynamically from the pipeline.
    # These require Measure expression type, everything else uses Column.
    known_measures = measure_names or set()

    # First pass: collect tables and assign unique aliases
    table_names: list[str] = []
    seen_tables: set[str] = set()
    for _role, items in projections.items():
        for item in items:
            parts = item["queryRef"].split(".", 1)
            if len(parts) == 2 and parts[0] not in seen_tables:
                seen_tables.add(parts[0])
                table_names.append(parts[0])

    used_aliases: set[str] = set()
    table_alias: dict[str, str] = {t: _make_alias(t, used_aliases) for t in table_names}

    select_entries: list[dict] = []
    seen_select: set[str] = set()

    for _role, items in projections.items():
        for item in items:
            qref = item["queryRef"]
            if qref in seen_select:
                continue
            seen_select.add(qref)

            parts = qref.split(".", 1)
            if len(parts) != 2:
                continue
            t_name, f_name = parts
            alias = table_alias.get(t_name, t_name[0].lower())
            is_measure = f_name in known_measures
            expr_type = "Measure" if is_measure else "Column"

            select_entries.append({
                expr_type: {
                    "Expression": {"SourceRef": {"Source": alias}},
                    "Property": f_name,
                },
                "Name": qref,
            })

    return {
        "Version": 2,
        "From": [
            {"Name": table_alias[t], "Entity": t, "Type": 0}
            for t in table_names
        ],
        "Select": select_entries,
    }


def _build_semantic_query_cmd(
    raw_query: dict[str, Any],
    projections: dict[str, list[dict[str, str]]] | None = None,
) -> dict[str, Any]:
    """Wrap a raw prototypeQuery in a SemanticQueryDataShapeCommand.

    Builds proper PBI binding with:
    - Primary groupings: Category/Group/Rows/Details columns
    - Secondary groupings: Series/Legend columns
    - Projection indices mapped to their correct roles
    """
    select_items = raw_query.get("Select", [])
    n_select = len(select_items)

    # Build a queryRef → select index map
    qref_to_idx: dict[str, int] = {}
    for i, item in enumerate(select_items):
        name = item.get("Name", "")
        qref_to_idx[name] = i

    # Categorize projection indices by role type
    category_indices: list[int] = []
    series_indices: list[int] = []
    value_indices: list[int] = []

    # Roles that act as category (axis/grouping)
    category_roles = {"Category", "Group", "Rows", "Details", "Columns"}
    # Roles that act as series/legend
    series_roles = {"Series", "Legend"}
    # Roles that act as values/measures
    value_roles = {"Y", "Y2", "Values", "Fields", "Size"}

    if projections:
        for role, items in projections.items():
            for item in items:
                idx = qref_to_idx.get(item["queryRef"])
                if idx is None:
                    continue
                if role in category_roles:
                    category_indices.append(idx)
                elif role in series_roles:
                    series_indices.append(idx)
                elif role in value_roles:
                    value_indices.append(idx)
                else:
                    # Unknown role → treat as category
                    category_indices.append(idx)
    else:
        # Fallback: all in primary
        category_indices = list(range(n_select))

    # Build binding
    # Primary = category + values (PBI groups categories and aggregates values)
    primary_projections = category_indices + value_indices
    if not primary_projections:
        primary_projections = list(range(n_select))

    binding: dict[str, Any] = {
        "Primary": {
            "Groupings": [{"Projections": primary_projections}]
        },
        "DataReduction": {
            "DataVolume": 3,
            "Primary": {"Window": {"Count": 1000}},
        },
        "Version": 1,
    }

    # Add Secondary grouping for Series/Legend fields
    if series_indices:
        binding["Secondary"] = {
            "Groupings": [{"Projections": series_indices}]
        }
        binding["DataReduction"]["Secondary"] = {"Top": {"Count": 60}}

    return {
        "Commands": [
            {
                "SemanticQueryDataShapeCommand": {
                    "Query": raw_query,
                    "Binding": binding,
                }
            }
        ]
    }


def _build_semantic_query(projections: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    """Build the semantic query payload for a visual (kept for backwards compatibility)."""
    return _build_semantic_query_cmd(_build_raw_query(projections), projections)
