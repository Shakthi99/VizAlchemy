"""Tableau .twb XML parser - main entry point."""

from __future__ import annotations

import io
import logging
import re
from typing import Optional

from lxml import etree

from tableau_to_powerbi.ir import (
    WorkbookIR,
    DatasourceIR,
    TableIR,
    ColumnIR,
    RelationshipIR,
    CalculatedFieldIR,
    WorksheetIR,
    DashboardIR,
    ZoneIR,
    FieldReference,
    EncodingsIR,
)

logger = logging.getLogger("tableau_to_powerbi.parser")


def parse_twb(twb_bytes: bytes, filename: str = "") -> WorkbookIR:
    """Parse a .twb file and return a WorkbookIR."""
    tree = etree.parse(io.BytesIO(twb_bytes))
    root = tree.getroot()

    workbook_name = filename.replace(".twb", "").replace(".twbx", "").strip()
    if not workbook_name:
        workbook_name = "Workbook"

    ir = WorkbookIR(name=workbook_name, source_file=filename)
    ir.datasources = _parse_datasources(root)
    ir.calculated_fields = _parse_calculated_fields(root)
    ir.worksheets = _parse_worksheets(root)
    ir.dashboards = _parse_dashboards(root)
    ir.data_directory = _extract_data_directory(root)

    logger.info(
        "Parsed workbook '%s': %d datasources, %d worksheets, %d dashboards, %d calculated fields",
        ir.name,
        len(ir.datasources),
        len(ir.worksheets),
        len(ir.dashboards),
        len(ir.calculated_fields),
    )
    return ir


def _extract_data_directory(root: etree._Element) -> str:
    """Extract the data directory from the first CSV connection in the TWB."""
    for conn in root.findall(".//named-connection/connection[@class='textscan']"):
        directory = conn.get("directory", "")
        if directory:
            return directory.replace("\\", "/")
    return ""


def _clean_identifier(raw: str) -> str:
    """Remove disambiguation suffixes, brackets, and Tableau internal prefixes."""
    clean = raw.strip("[]'\" ")
    # Handle Tableau's [Extract].[table] pattern
    if "].[" in clean:
        clean = clean.split("].[", 1)[1].rstrip("]")
    # Tableau uses 'connection!table' format internally — take just the table part
    if "!" in clean:
        clean = clean.split("!", 1)[1]
    # Strip #csv suffix variants
    clean = re.sub(r"#csv$", "", clean, flags=re.IGNORECASE)
    # Remove table-disambiguation suffix like " (tablename.csv)" or " (tablename)"
    clean = re.sub(r"\s+\([^)]+\)$", "", clean)
    return clean.strip()


def _parse_datasources(root: etree._Element) -> list[DatasourceIR]:
    """Extract datasource definitions."""
    datasources = []

    for ds_elem in root.findall(".//datasource"):
        ds_name = ds_elem.get("name", "")
        # Skip the built-in Parameters datasource
        if ds_name.lower() == "parameters":
            continue
        # Only process inline datasources or those with connections
        if ds_elem.get("inline") != "true" and ds_elem.find(".//connection") is None:
            continue

        ds_caption = ds_elem.get("caption", "")
        ds_ir = DatasourceIR(name=ds_name, caption=ds_caption)

        # Parse tables from relation elements
        tables_found: dict[str, TableIR] = {}
        for relation in ds_elem.findall(".//relation[@type='table']"):
            table_name_raw = relation.get("name", "")
            table_name = _clean_identifier(table_name_raw)
            if not table_name:
                continue

            # Skip Tableau extract/shadow tables (have UUID suffixes like _5B1BE0E2E165...)
            if re.search(r"_[0-9A-Fa-f]{32}$", table_name):
                continue

            # Strip .csv from table name for cleaner PBI identifiers
            table_name = table_name.replace(".csv", "")

            conn_name = relation.get("connection", "")
            table_ir = TableIR(name=table_name, connection_name=conn_name)

            # Derive filename from table reference
            table_ref = relation.get("table", "")
            if table_ref:
                # _clean_identifier strips brackets, !, and #csv suffix
                clean_ref = _clean_identifier(table_ref)
                # Also strip UUID extract suffixes from filename
                clean_ref = re.sub(r"_[0-9A-Fa-f]{32}$", "", clean_ref)
                clean_ref = clean_ref.replace(".csv", "")
                table_ir.filename = clean_ref + ".csv" if clean_ref else ""

            # Only add if not already found (avoid duplicates from multiple relations)
            if table_name not in tables_found:
                tables_found[table_name] = table_ir

        ds_ir.tables = list(tables_found.values())

        # Parse column mappings
        for map_elem in ds_elem.findall(".//cols/map"):
            key = _clean_identifier(map_elem.get("key", ""))
            value = map_elem.get("value", "")
            if key and value:
                ds_ir.column_mappings[key] = value

        # Enrich columns from metadata-records
        for record in ds_elem.findall(".//metadata-record[@class='column']"):
            parent_name = record.findtext("parent-name", "")
            local_name = record.findtext("local-name", "")
            local_type = record.findtext("local-type", "")
            remote_name_val = record.findtext("remote-name", "")

            if not parent_name or not local_name:
                continue

            table_name = _clean_identifier(parent_name).replace(".csv", "")
            col_name = _clean_identifier(local_name)

            # Skip extract/shadow table columns (UUID suffix)
            if re.search(r"_[0-9A-Fa-f]{32}$", table_name):
                continue

            if table_name in tables_found:
                existing = next(
                    (c for c in tables_found[table_name].columns if c.name == col_name),
                    None,
                )
                if existing:
                    if local_type:
                        existing.datatype = local_type
                    if remote_name_val:
                        existing.remote_name = remote_name_val
                else:
                    tables_found[table_name].columns.append(
                        ColumnIR(
                            name=col_name,
                            remote_name=remote_name_val or col_name,
                            datatype=local_type or "string",
                        )
                    )

        # Infer relationships from shared column names
        ds_ir.relationships = _infer_relationships(tables_found)
        datasources.append(ds_ir)

    return datasources


def _infer_relationships(tables: dict[str, TableIR]) -> list[RelationshipIR]:
    """Infer relationships based on common column naming patterns (*_id convention)."""
    relationships = []

    # Build normalized table name set
    table_names: set[str] = set()
    for t_name in tables:
        normalized = t_name.replace(".csv", "").replace("#csv", "")
        table_names.add(normalized)
        table_names.add(t_name)

    # Build column → tables map
    col_to_tables: dict[str, set[str]] = {}
    for t_name, table_ir in tables.items():
        normalized = t_name.replace(".csv", "").replace("#csv", "")
        for col in table_ir.columns:
            col_to_tables.setdefault(col.name, set()).add(normalized)

    # Infer FK relationships from *_id columns
    seen: set[tuple[str, str, str, str]] = set()
    for col_name, owning_tables in col_to_tables.items():
        if not col_name.endswith("_id") or len(owning_tables) < 2:
            continue
        # The table whose name matches the prefix is the "one" side
        prefix = col_name.replace("_id", "")
        primary_candidates = {prefix, prefix + "s", prefix + "es"}
        primary = primary_candidates & table_names
        if not primary:
            continue
        primary_table = sorted(primary)[0]
        for fk_table in owning_tables:
            if fk_table == primary_table:
                continue
            key = (fk_table, col_name, primary_table, col_name)
            if key not in seen:
                seen.add(key)
                relationships.append(
                    RelationshipIR(
                        from_table=fk_table,
                        from_column=col_name,
                        to_table=primary_table,
                        to_column=col_name,
                    )
                )

    return relationships


def _parse_calculated_fields(root: etree._Element) -> list[CalculatedFieldIR]:
    """Extract calculated fields from the workbook."""
    calc_fields: list[CalculatedFieldIR] = []
    existing_names: set[str] = set()

    for ds_elem in root.findall(".//datasource"):
        ds_name = ds_elem.get("name", "")
        if ds_name.lower() == "parameters":
            continue

        for col_elem in ds_elem.findall(".//column[calculation]"):
            name = col_elem.get("name", "")
            caption = col_elem.get("caption", "")
            datatype = col_elem.get("datatype", "string")

            calc_elem = col_elem.find("calculation")
            if calc_elem is not None:
                formula = calc_elem.get("formula", "")
                if formula:
                    clean_name = _clean_identifier(name)
                    if clean_name not in existing_names:
                        calc_fields.append(
                            CalculatedFieldIR(
                                name=clean_name,
                                caption=caption or clean_name,
                                formula=formula,
                                datatype=datatype,
                            )
                        )
                        existing_names.add(clean_name)

    # Also look in datasource-dependencies within worksheets
    for dep in root.findall(".//datasource-dependencies"):
        for col_elem in dep.findall("column[calculation]"):
            name = col_elem.get("name", "")
            caption = col_elem.get("caption", "")
            datatype = col_elem.get("datatype", "string")
            calc_elem = col_elem.find("calculation")
            if calc_elem is not None:
                formula = calc_elem.get("formula", "")
                calc_class = calc_elem.get("class", "")
                if formula and calc_class == "tableau":
                    clean_name = _clean_identifier(name)
                    if clean_name not in existing_names:
                        calc_fields.append(
                            CalculatedFieldIR(
                                name=clean_name,
                                caption=caption or clean_name,
                                formula=formula,
                                datatype=datatype,
                            )
                        )
                        existing_names.add(clean_name)

    logger.info("Found %d calculated fields", len(calc_fields))
    return calc_fields


def _parse_field_reference(raw_col: str) -> Optional[FieldReference]:
    """Parse a column instance reference string into a FieldReference."""
    match = re.search(r"\[([a-z]+):([^:]+):([a-z]+)\]", raw_col)
    if match:
        derivation_raw = match.group(1)
        column_name = match.group(2)
        type_code = match.group(3)

        derivation_map = {
            "sum": "Sum",
            "avg": "Avg",
            "cnt": "Count",
            "ctd": "CountD",
            "max": "Max",
            "min": "Min",
            "mn": "Month",
            "dy": "Day",
            "yr": "Year",
            "none": "None",
        }
        derivation = derivation_map.get(derivation_raw, "None")

        type_map = {"qk": "quantitative", "nk": "nominal", "ok": "ordinal"}
        field_type = type_map.get(type_code, "nominal")

        return FieldReference(
            column_name=column_name,
            derivation=derivation,
            field_type=field_type,
        )

    # Simpler format: [field_name]
    simple_match = re.search(r"\[([^\]]+)\]", raw_col)
    if simple_match:
        col_name = simple_match.group(1)
        return FieldReference(column_name=col_name)

    return None


def _parse_worksheets(root: etree._Element) -> list[WorksheetIR]:
    """Extract worksheet definitions."""
    worksheets = []

    for ws_elem in root.findall(".//worksheet"):
        ws_name = ws_elem.get("name", "")
        if not ws_name:
            continue

        ws_ir = WorksheetIR(name=ws_name)

        # Get mark type
        mark_elem = ws_elem.find(".//mark")
        if mark_elem is not None:
            ws_ir.mark_type = mark_elem.get("class", "Automatic")

        # Get datasource reference
        ds_dep = ws_elem.find(".//datasource-dependencies")
        if ds_dep is not None:
            ws_ir.datasource_name = ds_dep.get("datasource", "")

        # Parse rows and cols
        rows_elem = ws_elem.find(".//rows")
        if rows_elem is not None and rows_elem.text:
            refs = _parse_shelf_fields(rows_elem.text)
            ws_ir.rows = refs

        cols_elem = ws_elem.find(".//cols")
        if cols_elem is not None and cols_elem.text:
            refs = _parse_shelf_fields(cols_elem.text)
            ws_ir.cols = refs

        # Parse encodings
        ws_ir.encodings = _parse_encodings(ws_elem)

        worksheets.append(ws_ir)

    logger.info("Parsed %d worksheets", len(worksheets))
    return worksheets


def _parse_shelf_fields(text: str) -> list[FieldReference]:
    """Parse field references from rows/cols text."""
    refs = []
    pattern = r"\[([^\]]+)\]\.\[([^\]]+)\]"
    for match in re.finditer(pattern, text):
        field_part = match.group(2)
        ref = _parse_field_reference(f"[{field_part}]")
        if ref:
            refs.append(ref)
    return refs


def _parse_encodings(ws_elem: etree._Element) -> EncodingsIR:
    """Extract encoding channels from worksheet."""
    encodings_ir = EncodingsIR()

    encodings_elem = ws_elem.find(".//encodings")
    if encodings_elem is None:
        return encodings_ir

    for enc_name, attr_name in [
        ("color", "color"),
        ("size", "size"),
        ("text", "text"),
        ("wedge-size", "wedge_size"),
        ("lod", "lod"),
        ("geometry", "geometry"),
    ]:
        elem = encodings_elem.find(enc_name)
        if elem is not None:
            col_ref = elem.get("column", "")
            ref = _parse_field_reference(col_ref)
            if ref:
                setattr(encodings_ir, attr_name, ref)

    return encodings_ir


def _parse_dashboards(root: etree._Element) -> list[DashboardIR]:
    """Extract dashboard definitions."""
    dashboards = []

    for dash_elem in root.findall(".//dashboard"):
        dash_name = dash_elem.get("name", "")
        if not dash_name:
            continue

        dash_ir = DashboardIR(name=dash_name)

        # Get size
        size_elem = dash_elem.find("size")
        if size_elem is not None:
            try:
                dash_ir.width = int(size_elem.get("maxwidth", size_elem.get("width", "1220")))
                dash_ir.height = int(size_elem.get("maxheight", size_elem.get("height", "2160")))
            except (ValueError, TypeError):
                pass

        # Parse zones to find worksheet placements
        zone_id = 0
        for zone_elem in dash_elem.findall(".//zone"):
            ws_name = zone_elem.get("name")
            if ws_name:
                zone_id += 1
                try:
                    x = float(zone_elem.get("x", "0"))
                    y = float(zone_elem.get("y", "0"))
                    w = float(zone_elem.get("w", "0"))
                    h = float(zone_elem.get("h", "0"))
                except (ValueError, TypeError):
                    x = y = w = h = 0

                dash_ir.zones.append(
                    ZoneIR(
                        id=zone_id,
                        worksheet_name=ws_name,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                    )
                )

        dashboards.append(dash_ir)

    logger.info("Parsed %d dashboards", len(dashboards))
    return dashboards
