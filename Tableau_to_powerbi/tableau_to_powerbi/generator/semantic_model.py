"""Power BI semantic model (TMDL) generator."""

from __future__ import annotations

import logging
import re
import uuid

from tableau_to_powerbi.ir import (
    WorkbookIR,
    DatasourceIR,
    TableIR,
    ColumnIR,
    RelationshipIR,
    CalculatedFieldIR,
    MeasureIR,
)
from tableau_to_powerbi.config import CONFIG
from tableau_to_powerbi.translation import TYPE_MAP as TABLEAU_TYPE_MAP

logger = logging.getLogger("tableau_to_powerbi.generator")


# ---------------------------------------------------------------------------
# Dynamic schema extraction from IR
# ---------------------------------------------------------------------------

def _normalize_table_name(raw: str) -> str:
    """Normalize a table name: strip suffixes, handle connection!table format."""
    name = raw.replace(".csv", "").replace("#csv", "")
    # Tableau uses 'connection!table' format — take just the table part
    if "!" in name:
        name = name.split("!", 1)[1]
    return name


def _build_schema_from_ir(ir: WorkbookIR) -> dict[str, dict[str, str]]:
    """Build the table schema dynamically from parsed WorkbookIR datasources."""
    schema: dict[str, dict[str, str]] = {}
    for ds in ir.datasources:
        for table in ds.tables:
            table_name = _normalize_table_name(table.name)
            if table_name not in schema:
                schema[table_name] = {}
            for col in table.columns:
                tmdl_type = _tableau_to_tmdl_type(col.datatype)
                schema[table_name][col.name] = tmdl_type
    return schema


def _build_csv_filename_map(ir: WorkbookIR) -> dict[str, str]:
    """Build a mapping of normalized table name → CSV filename."""
    filename_map: dict[str, str] = {}
    for ds in ir.datasources:
        for table in ds.tables:
            table_name = _normalize_table_name(table.name)
            if table.filename:
                filename_map[table_name] = table.filename
            else:
                filename_map[table_name] = f"{table_name}.csv"
    return filename_map


def _build_relationships_from_ir(ir: WorkbookIR) -> list[tuple[str, str, str, str]]:
    """Build relationships dynamically from parsed WorkbookIR datasources."""
    rels: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for ds in ir.datasources:
        for rel in ds.relationships:
            key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
            if key not in seen:
                seen.add(key)
                rels.append(key)
    # Also infer relationships from shared column naming patterns
    all_tables = {t for ds in ir.datasources for t in [_normalize_table_name(tbl.name) for tbl in ds.tables]}
    inferred = _infer_relationships_generic(all_tables, ir)
    for rel in inferred:
        if rel not in seen:
            seen.add(rel)
            rels.append(rel)
    return rels


def _infer_relationships_generic(
    table_names: set[str], ir: WorkbookIR
) -> list[tuple[str, str, str, str]]:
    """Infer FK relationships by matching *_id columns across tables."""
    # Build a map: column_name -> set of tables that have it
    col_to_tables: dict[str, set[str]] = {}
    for ds in ir.datasources:
        for table in ds.tables:
            tname = _normalize_table_name(table.name)
            for col in table.columns:
                col_to_tables.setdefault(col.name, set()).add(tname)

    rels: list[tuple[str, str, str, str]] = []
    for col_name, tables in col_to_tables.items():
        if not col_name.endswith("_id") or len(tables) < 2:
            continue
        # The table whose name matches the prefix is the "one" (primary) side
        prefix = col_name.replace("_id", "")
        # Try plural forms: prefix, prefix + "s", prefix + "es"
        primary_candidates = {prefix, prefix + "s", prefix + "es"}
        primary = primary_candidates & tables
        if not primary:
            continue
        primary_table = sorted(primary)[0]
        for fk_table in tables:
            if fk_table == primary_table:
                continue
            rels.append((fk_table, col_name, primary_table, col_name))
    return rels


def _detect_date_columns(ir: WorkbookIR) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Detect date columns from worksheets that use Month/Day derivations."""
    month_cols: list[tuple[str, str]] = []
    day_cols: list[tuple[str, str]] = []
    seen_month: set[tuple[str, str]] = set()
    seen_day: set[tuple[str, str]] = set()

    for ws in ir.worksheets:
        for ref in ws.rows + ws.cols:
            if not ref.table_name:
                continue
            if ref.derivation == "Month" and (ref.table_name, ref.column_name) not in seen_month:
                seen_month.add((ref.table_name, ref.column_name))
                month_cols.append((ref.table_name, ref.column_name))
            elif ref.derivation == "Day" and (ref.table_name, ref.column_name) not in seen_day:
                seen_day.add((ref.table_name, ref.column_name))
                day_cols.append((ref.table_name, ref.column_name))

    return month_cols, day_cols


def _tableau_to_tmdl_type(tableau_type: str) -> str:
    """Convert Tableau datatype string to TMDL type."""
    mapping = {
        "integer": "int64",
        "real": "double",
        "string": "string",
        "date": "dateTime",
        "datetime": "dateTime",
        "boolean": "boolean",
    }
    return mapping.get(tableau_type.lower(), "string")


def _format_tmdl_name(name: str) -> str:
    """Format a name for TMDL syntax (quote if needed)."""
    # TMDL reserved words must be quoted when used as identifiers
    _TMDL_RESERVED = {
        "end", "table", "column", "measure", "partition", "relationship",
        "expression", "model", "database", "ref", "annotation", "source",
        "mode", "type", "name", "role", "culture", "from", "to", "in",
        "true", "false", "none", "not", "and", "or", "is",
    }
    if name.lower() in _TMDL_RESERVED:
        return f"'{name}'"
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return f"'{name}'"
    return name


def _tmdl_to_m_type(tmdl_type: str) -> str:
    """Convert a TMDL dataType to a Power Query M type constant."""
    m_type_map = {
        "int64": "Int64.Type",
        "double": "type number",
        "string": "type text",
        "dateTime": "type date",
        "boolean": "type logical",
    }
    return m_type_map.get(tmdl_type, "type text")


def generate_model_tmdl(ir: WorkbookIR | None = None) -> str:
    """Generate the model.tmdl file content."""
    schema = _build_schema_from_ir(ir) if ir else {}
    lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "",
        "\tannotation __PBI_TimeIntelligenceEnabled = 0",
        "",
    ]
    # Add ref table declarations for per-file structure
    for table_name in schema:
        lines.append(f"ref table {_format_tmdl_name(table_name)}")
    lines.append("")
    return "\n".join(lines)


def generate_database_tmdl(project_name: str) -> str:
    """Generate the database.tmdl file content."""
    return (
        f"database '{project_name}'\n"
        f"\tcompatibilityLevel: {CONFIG.compatibility_level}\n"
    )


def generate_tables_tmdl(
    measures: list[MeasureIR],
    calculated_fields: list[CalculatedFieldIR],
    data_directory: str = "",
    ir: WorkbookIR | None = None,
) -> str:
    """Generate TMDL content for all tables, columns, measures, and relationships.
    
    Returns a single string with all tables and relationships (legacy format).
    For the per-file PBIP format, use generate_table_files() instead.
    """
    table_files = generate_table_files(measures, calculated_fields, data_directory, ir=ir)
    rel_tmdl = generate_relationships_tmdl(ir=ir)
    # Combine all table files plus relationships into one string
    all_parts = list(table_files.values()) + [rel_tmdl]
    return "\n".join(all_parts)


def generate_table_files(
    measures: list[MeasureIR],
    calculated_fields: list[CalculatedFieldIR],
    data_directory: str = "",
    ir: WorkbookIR | None = None,
) -> dict[str, str]:
    """Generate individual TMDL content per table.
    
    Returns a dict mapping table_name -> TMDL content string.
    """
    if not data_directory:
        data_directory = CONFIG.default_data_directory

    # Build schema dynamically from IR
    schema = _build_schema_from_ir(ir) if ir else {}
    if not schema:
        logger.warning("No schema found from IR — no tables will be generated")
        return {}

    # Build CSV filename map for partitions
    csv_filenames = _build_csv_filename_map(ir) if ir else {}

    # Enrich schema from actual CSV headers when parser didn't find columns
    import os
    for table_name in list(schema.keys()):
        if not schema[table_name]:
            csv_file = csv_filenames.get(table_name, f"{table_name}.csv")
            csv_path = os.path.join(data_directory, csv_file)
            if os.path.isfile(csv_path):
                try:
                    with open(csv_path, "r", encoding="utf-8-sig") as f:
                        header_line = f.readline().strip()
                    headers = [h.strip().strip('"') for h in header_line.split(",")]
                    for h in headers:
                        if h and h not in schema[table_name]:
                            schema[table_name][h] = "string"
                    logger.info("Enriched schema for '%s' from CSV headers: %d columns", table_name, len(headers))
                except Exception as e:
                    logger.warning("Could not read CSV headers for '%s': %s", table_name, e)

    # Detect date columns for calculated Month/Day columns
    date_month_columns, date_day_columns = _detect_date_columns(ir) if ir else ([], [])

    # Group measures by table
    measures_by_table: dict[str, list[MeasureIR]] = {}
    for m in measures:
        measures_by_table.setdefault(m.table_name, []).append(m)

    result: dict[str, str] = {}

    # Generate table definitions
    for table_name, columns in schema.items():
        lines: list[str] = []
        formatted_table = _format_tmdl_name(table_name)

        lines.append(f"table {formatted_table}")
        lines.append(f"\tlineageTag: {uuid.uuid4()}")
        lines.append("")

        # Columns
        for col_name, dt in columns.items():
            formatted_col = _format_tmdl_name(col_name)
            lines.append(f"\tcolumn {formatted_col}")
            lines.append(f"\t\tdataType: {dt}")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\tsourceColumn: {_format_tmdl_name(col_name)}")
            lines.append(f"\t\tsummarizeBy: none")
            lines.append("")

        # Month-level calculated columns for date fields
        for month_table, month_col in date_month_columns:
            if month_table == table_name:
                # MonthNumber column (for sorting)
                month_num_name = f"{month_col}_MonthNumber"
                lines.append(f"\tcolumn {month_num_name} = MONTH('{table_name}'[{month_col}])")
                lines.append("\t\tdataType: int64")
                lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
                lines.append("")

                # MonthName column (for display)
                month_name_col = f"{month_col}_Month"
                lines.append(f"\tcolumn {month_name_col} = FORMAT('{table_name}'[{month_col}], \"MMM\")")
                lines.append("\t\tdataType: string")
                lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
                lines.append(f"\t\tsortByColumn: {month_num_name}")
                lines.append("")

        # Day-level calculated columns for date fields
        for day_table, day_col in date_day_columns:
            if day_table == table_name:
                day_col_name = f"{day_col}_Day"
                lines.append(f"\tcolumn {day_col_name} = DAY('{table_name}'[{day_col}])")
                lines.append("\t\tdataType: int64")
                lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
                lines.append("")

        # Additional calculated fields (skip if name duplicates an existing column or CSV header)
        _existing_col_names = {c.lower() for c in columns.keys()}
        # Also check CSV headers — a calc field that duplicates a CSV column causes merge errors
        csv_file_for_check = csv_filenames.get(table_name, f"{table_name}.csv")
        csv_path_for_check = os.path.join(data_directory, csv_file_for_check)
        if os.path.isfile(csv_path_for_check):
            try:
                with open(csv_path_for_check, "r", encoding="utf-8-sig") as _f:
                    _hdr = _f.readline().strip()
                _csv_cols = {h.strip().strip('"').lower() for h in _hdr.split(",")}
                _existing_col_names.update(_csv_cols)
            except Exception:
                pass

        for calc in calculated_fields:
            if calc.parent_table == table_name and calc.dax_expression:
                col_name_clean = calc.caption or calc.name
                # Skip calculated fields that duplicate existing schema/CSV columns
                if col_name_clean.lower() in _existing_col_names:
                    continue
                # Ensure DAX expression is single-line (TMDL requires it)
                dax_expr = " ".join(calc.dax_expression.replace("\r", "").split("\n"))
                dax_expr = " ".join(dax_expr.split())  # collapse whitespace
                lines.append(f"\tcolumn '{col_name_clean}' = {dax_expr}")
                lines.append("\t\tdataType: string")
                lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
                lines.append("")

        # Measures
        table_measures = measures_by_table.get(table_name, [])
        for m in table_measures:
            # Ensure DAX expression is single-line (TMDL requires it)
            m_dax = " ".join(m.dax_expression.replace("\r", "").split("\n"))
            m_dax = " ".join(m_dax.split())
            lines.append(
                f"\tmeasure '{m.name}' = {m_dax}"
            )
            lines.append(f"\t\tformatString: {m.format_string}")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append("")

        # Partition (Power Query M expression)
        csv_file = csv_filenames.get(table_name, f"{table_name}.csv")
        lines.append(f"\tpartition {table_name}-partition = m")
        lines.append("\t\tmode: import")
        lines.append("\t\tsource =")
        lines.append("\t\t\tlet")
        lines.append(
            f'\t\t\t\tSource = Csv.Document(File.Contents("{data_directory}/{csv_file}"),'
            '[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),'
        )
        lines.append(
            '\t\t\t\t#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalarTypes=true]),'
        )
        # Build type transformation list for numeric/date columns
        type_transforms = []
        for col_name, dt in columns.items():
            m_type = _tmdl_to_m_type(dt)
            type_transforms.append(f'{{"{col_name}", {m_type}}}')
        transforms_str = ", ".join(type_transforms)
        lines.append(
            f'\t\t\t\t#"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{transforms_str}}})'
        )
        lines.append("\t\t\tin")
        lines.append('\t\t\t\t#"Changed Type"')
        lines.append("")

        result[table_name] = "\n".join(lines)

    return result


def generate_relationships_tmdl(ir: WorkbookIR | None = None) -> str:
    """Generate TMDL content for all relationships."""
    relationships = _build_relationships_from_ir(ir) if ir else []
    lines: list[str] = []
    # Use bothDirections to replicate Tableau's flat/joined datasource behavior
    # where filtering by any dimension automatically filters all measures.
    for from_t, from_c, to_t, to_c in relationships:
        from_tbl = _format_tmdl_name(from_t)
        to_tbl = _format_tmdl_name(to_t)
        from_col = _format_tmdl_name(from_c)
        to_col = _format_tmdl_name(to_c)
        lines.append(f"relationship Rel_{from_t}_{to_t}")
        lines.append(f"\tfromColumn: {from_tbl}.{from_col}")
        lines.append(f"\ttoColumn: {to_tbl}.{to_col}")
        lines.append(f"\tfromCardinality: many")
        lines.append(f"\ttoCardinality: one")
        lines.append(f"\tcrossFilteringBehavior: bothDirections")
        lines.append(f"\tisActive: true")
        lines.append("")

    return "\n".join(lines)
