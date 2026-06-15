"""
TWB / TWBX parser — reads Tableau workbook XML and produces a TableauIR.

Handles both:
  .twb  — plain XML file
  .twbx — ZIP archive containing a .twb plus extract files
"""
from __future__ import annotations

import re
import zipfile
import logging
from pathlib import Path

try:
    # FIX: use defusedxml to prevent XXE attacks on untrusted .twb files
    from defusedxml import ElementTree as ET
except ImportError:
    # graceful fallback — log a warning so operators know the risk
    import logging as _l
    _l.getLogger(__name__).warning(
        "defusedxml not installed — XML parsing is XXE-unsafe. "
        "Run: pip install defusedxml"
    )
    from xml.etree import ElementTree as ET  # type: ignore[assignment]

from tableau_to_pbi.utils.models import (
    TableauIR,
    TableauDataSource,
    TableauColumn,
    TableauJoin,
    TableauWorksheet,
    TableauEncoding,
    TableauFilter,
    TableauDashboard,
    DashboardObject,
    TableauParameter,
)

log = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _attr(elem: ET.Element, *keys: str, default: str = "") -> str:
    for k in keys:
        v = elem.get(k)
        if v:
            return v
    return default


def _norm_name(name: str) -> str:
    """Strip Tableau internal brackets and prefixes."""
    return name.strip("[]").split("].[")[-1]


# ── datasource parsing ─────────────────────────────────────────────────────────

def _parse_join(rel: ET.Element) -> list[TableauJoin]:
    joins: list[TableauJoin] = []
    join_type = _attr(rel, "join", default="inner").lower()
    clauses = rel.findall(".//clause")
    for clause in clauses:
        expr = clause.find("expression")
        if expr is None:
            continue
        ops = expr.findall("expression")
        if len(ops) >= 2:
            left = _norm_name(_attr(ops[0], "op", default=""))
            right = _norm_name(_attr(ops[1], "op", default=""))
            joins.append(TableauJoin(
                join_type=join_type,
                left_key=left,
                right_key=right,
            ))
    # fallback: parse the relation's table names from child relations
    child_rels = rel.findall("relation")
    tables = [_attr(r, "name", default="") for r in child_rels]
    if joins and len(tables) >= 2:
        for j in joins:
            j.left_table = tables[0]
            j.right_table = tables[1]
    return joins


def _parse_datasource(ds_elem: ET.Element) -> TableauDataSource:
    name = _attr(ds_elem, "name", default="unknown")
    caption = _attr(ds_elem, "caption", default=name)

    ds = TableauDataSource(name=name, caption=caption)

    # Connection info
    conn = ds_elem.find(".//connection")
    if conn is not None:
        ds.connection_type = _attr(conn, "class", default="unknown").lower()
        ds.server = _attr(conn, "server", "servername", default="")
        ds.database = _attr(conn, "dbname", "database", default="")
        ds.schema_name = _attr(conn, "schema", default="")

        # Table / custom SQL
        rel = conn.find("relation")
        if rel is not None:
            rel_type = _attr(rel, "type", default="")
            if rel_type == "text":
                ds.custom_sql = (rel.text or "").strip()
            else:
                ds.table = _attr(rel, "name", "table", default="")

            # Nested joins
            for child in rel.findall("relation[@join]"):
                ds.joins.extend(_parse_join(child))

    # Columns
    for col_elem in ds_elem.findall(".//column"):
        col_name = _attr(col_elem, "name", default="")
        if not col_name or col_name.startswith(":"):
            continue
        formula_elem = col_elem.find("calculation")
        formula = ""
        is_calc = False
        if formula_elem is not None:
            formula = _attr(formula_elem, "formula", default="")
            is_calc = bool(formula)

        ds.columns.append(TableauColumn(
            name=_norm_name(col_name),
            caption=_attr(col_elem, "caption", default=_norm_name(col_name)),
            datatype=_attr(col_elem, "datatype", default="string"),
            role=_attr(col_elem, "role", default="dimension"),
            type=_attr(col_elem, "type", default="nominal"),
            formula=formula,
            is_calculated=is_calc,
            hidden=_attr(col_elem, "hidden", default="false").lower() == "true",
        ))

    return ds


# ── worksheet parsing ──────────────────────────────────────────────────────────

def _get_agg(field_ref: str) -> str:
    """Extract outermost Tableau aggregation prefix, e.g. SUM, YEAR, COUNTD."""
    field_ref = field_ref.strip()
    m = re.match(r"^([A-Za-z_]+)\s*\(", field_ref)
    if m:
        candidate = m.group(1).upper()
        return candidate if candidate.isalpha() else "NONE"
    return "NONE"


def _get_field_name(field_ref: str) -> str:
    """
    Unwrap aggregation wrappers to get the innermost field name.
    Handles nested aggs like SUM(YEAR([Order Date])) correctly
    by walking inward until we hit a [FieldName] bracket.
    """
    inner = field_ref.strip()
    # FIX: iteratively strip outermost function wrapper, respecting paren depth
    for _ in range(5):  # max 5 nesting levels
        m = re.match(r"^[A-Za-z_]+\s*\((.+)\)$", inner)
        if not m:
            break
        inner = m.group(1).strip()
        # Stop once the remaining content starts with a field bracket
        if inner.startswith("["):
            break
    return _norm_name(inner)


def _split_shelf(text: str) -> list[str]:
    """
    Split a Tableau shelf string on commas, but only at depth-0
    (i.e. not inside parentheses).  Handles cases like:
      SUM([Sales]),DATEADD('month',-1,[Order Date]),YEAR([Order Date])
    """
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            token = "".join(buf).strip()
            if token:
                parts.append(token)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_worksheet(ws_elem: ET.Element) -> TableauWorksheet:
    name = _attr(ws_elem, "name", default="Sheet")
    ws = TableauWorksheet(name=name)

    table = ws_elem.find(".//table")
    if table is None:
        return ws

    # Datasource reference
    ds_dep = table.find(".//datasource-dependencies")
    if ds_dep is not None:
        ws.datasource = _attr(ds_dep, "datasource", default="")

    # Mark type
    style = table.find(".//style-rule[@element='mark']")
    if style is not None:
        encoding_elem = style.find("encoding[@attr='mark']")
        if encoding_elem is not None:
            ws.mark_type = _attr(encoding_elem, "value", default="bar").lower()

    mark_class = table.find(".//mark[@class]")
    if mark_class is not None:
        ws.mark_type = _attr(mark_class, "class", default=ws.mark_type).lower()

    # Rows / Cols shelves
    rows_elem = table.find(".//rows")
    cols_elem = table.find(".//cols")

    def _parse_shelf(shelf_elem: ET.Element | None, shelf_name: str) -> list[TableauEncoding]:
        out: list[TableauEncoding] = []
        if shelf_elem is None:
            return out
        # FIX: use depth-aware split so nested commas (e.g. DATEADD args) aren't split incorrectly
        for ref in _split_shelf(shelf_elem.text or ""):
            ref = ref.strip()
            if not ref:
                continue
            out.append(TableauEncoding(
                shelf=shelf_name,
                field=_get_field_name(ref),
                aggregation=_get_agg(ref),
            ))
        return out

    ws.encodings.extend(_parse_shelf(rows_elem, "rows"))
    ws.encodings.extend(_parse_shelf(cols_elem, "cols"))
    ws.rows = [e.field for e in ws.encodings if e.shelf == "rows"]
    ws.cols = [e.field for e in ws.encodings if e.shelf == "cols"]

    # Encodings from pane / mark encodings
    for enc_elem in table.findall(".//encoding"):
        attr = _attr(enc_elem, "attr", default="")
        if attr in ("color", "size", "label", "detail", "tooltip"):
            field_ref = ""
            field_elem = enc_elem.find("field")
            if field_elem is not None:
                field_ref = _attr(field_elem, "name", default="")
            if field_ref:
                ws.encodings.append(TableauEncoding(
                    shelf=attr,
                    field=_get_field_name(field_ref),
                    aggregation=_get_agg(field_ref),
                ))

    # Filters
    for f_elem in table.findall(".//filter"):
        field = _norm_name(_attr(f_elem, "column", default=""))
        if not field:
            continue
        ftype = _attr(f_elem, "class", default="categorical")
        values: list[str] = []
        for mv in f_elem.findall(".//member[@value]"):
            values.append(_attr(mv, "value", default=""))
        ws.filters.append(TableauFilter(
            field=field,
            filter_type=ftype,
            values=values,
            datasource=ws.datasource,
        ))

    return ws


# ── dashboard parsing ──────────────────────────────────────────────────────────

def _parse_dashboard(db_elem: ET.Element) -> TableauDashboard:
    name = _attr(db_elem, "name", default="Dashboard")
    db = TableauDashboard(name=name)

    size_elem = db_elem.find("size")
    if size_elem is not None:
        db.width = float(_attr(size_elem, "maxwidth", "width", default="1366"))
        db.height = float(_attr(size_elem, "maxheight", "height", default="768"))

    for zone in db_elem.findall(".//zone"):
        z_type = _attr(zone, "type", default="").lower()
        z_name = _attr(zone, "name", default="")
        obj_type = "worksheet" if z_type in ("sheet", "") and z_name else z_type or "blank"
        db.objects.append(DashboardObject(
            object_type=obj_type,
            name=z_name,
            x=float(_attr(zone, "x", default="0")),
            y=float(_attr(zone, "y", default="0")),
            w=float(_attr(zone, "w", default="0")),
            h=float(_attr(zone, "h", default="0")),
        ))

    # Actions
    for action in db_elem.findall(".//action"):
        db.actions.append({
            "name":   _attr(action, "name", default=""),
            "type":   _attr(action, "type", default=""),
            "source": _attr(action, "source-sheet", default=""),
            "target": _attr(action, "target-sheet", default=""),
        })

    return db


# ── parameters ────────────────────────────────────────────────────────────────

def _parse_parameters(root: ET.Element) -> list[TableauParameter]:
    params: list[TableauParameter] = []
    for col in root.findall(".//datasource[@name='Parameters']//column"):
        col_name = _attr(col, "name", default="")
        if not col_name:
            continue
        values: list[str] = []
        for mv in col.findall(".//member[@value]"):
            values.append(_attr(mv, "value", default=""))
        params.append(TableauParameter(
            name=_norm_name(col_name),
            caption=_attr(col, "caption", default=_norm_name(col_name)),
            datatype=_attr(col, "datatype", default="string"),
            current_value=_attr(col, "value", default=""),
            values=values,
        ))
    return params


# ── public API ─────────────────────────────────────────────────────────────────

def parse_twb(path: Path) -> TableauIR:
    """
    Parse a .twb or .twbx file and return a TableauIR.
    """
    path = Path(path)
    xml_content: str

    if path.suffix.lower() == ".twbx":
        with zipfile.ZipFile(path) as zf:
            twb_names = [n for n in zf.namelist() if n.endswith(".twb")]
            if not twb_names:
                raise ValueError(f"No .twb found inside {path}")
            with zf.open(twb_names[0]) as f:
                xml_content = f.read().decode("utf-8", errors="replace")
    else:
        xml_content = path.read_text(encoding="utf-8", errors="replace")

    root = ET.fromstring(xml_content)

    ir = TableauIR(
        workbook_name=path.stem,
        source_file=str(path),
    )

    # Datasources (skip the built-in Parameters datasource)
    for ds_elem in root.findall(".//datasource"):
        if _attr(ds_elem, "name", default="").lower() == "parameters":
            continue
        try:
            ir.datasources.append(_parse_datasource(ds_elem))
        except Exception as e:
            log.warning("Datasource parse error: %s", e)

    # Worksheets
    for ws_elem in root.findall(".//worksheet"):
        try:
            ir.worksheets.append(_parse_worksheet(ws_elem))
        except Exception as e:
            log.warning("Worksheet parse error [%s]: %s", _attr(ws_elem, "name"), e)

    # Dashboards
    for db_elem in root.findall(".//dashboard"):
        try:
            ir.dashboards.append(_parse_dashboard(db_elem))
        except Exception as e:
            log.warning("Dashboard parse error [%s]: %s", _attr(db_elem, "name"), e)

    # Parameters
    ir.parameters = _parse_parameters(root)

    log.info(
        "Parsed %s: %d datasources, %d worksheets, %d dashboards, %d parameters",
        path.name,
        len(ir.datasources),
        len(ir.worksheets),
        len(ir.dashboards),
        len(ir.parameters),
    )
    return ir
