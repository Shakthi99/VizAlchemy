"""DAX translation engine - converts Tableau formulas/aggregations to DAX."""

from __future__ import annotations

import logging
import re
from typing import Optional

from tableau_to_powerbi.ir import (
    WorkbookIR,
    WorksheetIR,
    CalculatedFieldIR,
    MeasureIR,
    FieldReference,
)

logger = logging.getLogger("tableau_to_powerbi.translation")

# Tableau type → Power BI TMDL type
TYPE_MAP: dict[str, str] = {
    "integer": "int64",
    "real": "double",
    "string": "string",
    "date": "dateTime",
    "datetime": "dateTime",
    "boolean": "boolean",
}

# Tableau aggregation → DAX function
AGG_TO_DAX: dict[str, str] = {
    "Sum": "SUM",
    "Avg": "AVERAGE",
    "Count": "COUNT",
    "CountD": "DISTINCTCOUNT",
    "Max": "MAX",
    "Min": "MIN",
    "Median": "MEDIAN",
    "Attr": "SELECTEDVALUE",
}

# Format strings
FORMAT_MAP: dict[str, str] = {
    "currency": '"$#,##0.00"',
    "integer": '"#,##0"',
    "decimal": '"#,##0.00"',
    "percentage": '"0.00%"',
}


KNOWN_SCHEMA_COLUMNS: dict[str, set[str]] = {}
# Populated dynamically by _build_schema_lookup(ir) during measure generation


def _build_schema_lookup(ir) -> dict[str, set[str]]:
    """Build column lookup from IR datasources at runtime."""
    lookup: dict[str, set[str]] = {}
    for ds in ir.datasources:
        for table in ds.tables:
            table_name = table.name.replace(".csv", "").replace("#csv", "")
            # Handle Tableau's connection!table format
            if "!" in table_name:
                table_name = table_name.split("!", 1)[1]
            cols = {col.name for col in table.columns}
            lookup.setdefault(table_name, set()).update(cols)
    return lookup


def map_tableau_type(tableau_type: str) -> str:
    """Convert a Tableau data type to Power BI TMDL type."""
    return TYPE_MAP.get(tableau_type, "string")


def translate_calculated_field(calc_field: CalculatedFieldIR, table_name: str = "") -> str:
    """Translate a Tableau calculated field formula to DAX."""
    formula = calc_field.formula.strip()

    # TRIM([field])
    trim_match = re.match(r"TRIM\(\[([^\]]+)\]\)", formula, re.IGNORECASE)
    if trim_match:
        field_name = trim_match.group(1)
        tbl = table_name or calc_field.parent_table
        if tbl:
            return f"TRIM('{tbl}'[{field_name}])"
        return f"TRIM([{field_name}])"

    # IF ... THEN ... ELSE ... END
    if_else_match = re.match(
        r"IF\s+(.+?)\s+THEN\s+(.+?)\s+ELSE\s+(.+?)\s+END",
        formula,
        re.IGNORECASE | re.DOTALL,
    )
    if if_else_match:
        cond = _translate_expression(if_else_match.group(1), table_name)
        then_val = _translate_expression(if_else_match.group(2), table_name)
        else_val = _translate_expression(if_else_match.group(3), table_name)
        return f"IF({cond}, {then_val}, {else_val})"

    # IF ... THEN ... END (no ELSE)
    if_no_else_match = re.match(
        r"IF\s+(.+?)\s+THEN\s+(.+?)\s+END",
        formula,
        re.IGNORECASE | re.DOTALL,
    )
    if if_no_else_match:
        cond = _translate_expression(if_no_else_match.group(1), table_name)
        then_val = _translate_expression(if_no_else_match.group(2), table_name)
        return f"IF({cond}, {then_val}, BLANK())"

    # DATEPART('part', [field])
    datepart_match = re.match(
        r"DATEPART\(['\"](\w+)['\"],\s*\[([^\]]+)\]\)",
        formula,
        re.IGNORECASE,
    )
    if datepart_match:
        part = datepart_match.group(1).upper()
        field_name = datepart_match.group(2)
        tbl = table_name or calc_field.parent_table
        col_ref = f"'{tbl}'[{field_name}]" if tbl else f"[{field_name}]"
        return f"{part}({col_ref})"

    # Simple function translations (LEN, UPPER, LOWER, LEFT, RIGHT)
    for func in ("LEN", "UPPER", "LOWER", "LEFT", "RIGHT", "LTRIM", "RTRIM"):
        func_match = re.match(
            rf"{func}\(\[([^\]]+)\]\)", formula, re.IGNORECASE
        )
        if func_match:
            field_name = func_match.group(1)
            tbl = table_name or calc_field.parent_table
            col_ref = f"'{tbl}'[{field_name}]" if tbl else f"[{field_name}]"
            dax_func = "TRIM" if func in ("LTRIM", "RTRIM") else func
            return f"{dax_func}({col_ref})"

    # Fallback: return formula with basic bracket translation
    return _translate_expression(formula, table_name)


def _translate_expression(expr: str, table_name: str) -> str:
    """Basic expression translation for field references."""
    if table_name:
        expr = re.sub(r"\[([^\]]+)\]", rf"'{table_name}'[\1]", expr)
    return expr.strip()


def infer_parent_table(calc_field: CalculatedFieldIR, schema_lookup: dict[str, set[str]] | None = None) -> str:
    """Infer the source table for a calculated field from its bracketed field references."""
    referenced_fields = set(re.findall(r"\[([^\]]+)\]", calc_field.formula or ""))
    if not referenced_fields:
        return calc_field.parent_table

    lookup = schema_lookup or KNOWN_SCHEMA_COLUMNS
    candidate_tables = []
    for table_name, columns in lookup.items():
        if referenced_fields.issubset(columns):
            candidate_tables.append(table_name)

    if len(candidate_tables) == 1:
        return candidate_tables[0]

    return calc_field.parent_table


def generate_measure_from_aggregation(
    column_name: str,
    derivation: str,
    table_name: str,
    measure_name: Optional[str] = None,
) -> Optional[MeasureIR]:
    """Generate a DAX measure from a Tableau aggregation."""
    dax_func = AGG_TO_DAX.get(derivation)
    if not dax_func:
        return None

    col_ref = f"'{table_name}'[{column_name}]"
    dax_expr = f"{dax_func}({col_ref})"

    if not measure_name:
        measure_name = f"{derivation} of {column_name}"

    # Determine format string
    fmt = '"#,##0"'
    if derivation in ("Sum", "Max", "Min", "Avg") and column_name in (
        "total_price", "amount", "price", "price_at_purchase"
    ):
        fmt = '"$#,##0.00"'
    elif derivation in ("Avg",):
        fmt = '"#,##0.00"'

    return MeasureIR(
        name=measure_name,
        dax_expression=dax_expr,
        format_string=fmt,
        table_name=table_name,
    )


def generate_measures_for_workbook(ir: WorkbookIR) -> list[MeasureIR]:
    """Generate all DAX measures needed for the workbook dynamically from IR."""
    measures: list[MeasureIR] = []
    seen_measures: set[str] = set()

    # Build schema lookup from IR for table inference
    schema_lookup = _build_schema_lookup(ir)

    # Generate measures from worksheet aggregations (rows, cols, encodings)
    for ws in ir.worksheets:
        all_refs: list[FieldReference] = list(ws.rows) + list(ws.cols)
        # Also include encoding fields that have aggregations
        enc = ws.encodings
        for enc_ref in (enc.color, enc.size, enc.text, enc.wedge_size):
            if enc_ref and enc_ref.derivation and enc_ref.derivation != "None":
                all_refs.append(enc_ref)

        for ref in all_refs:
            if ref.derivation and ref.derivation not in ("None", "Month", "Day", "Year", "Quarter"):
                table = ref.table_name or "Data"
                m = generate_measure_from_aggregation(
                    column_name=ref.column_name,
                    derivation=ref.derivation,
                    table_name=table,
                )
                if m and m.name not in seen_measures:
                    measures.append(m)
                    seen_measures.add(m.name)

    # Translate calculated fields
    for calc in ir.calculated_fields:
        parent_table = calc.parent_table or infer_parent_table(calc, schema_lookup)
        calc.parent_table = parent_table
        calc.dax_expression = translate_calculated_field(calc, parent_table)

    logger.info("Generated %d measures", len(measures))
    return measures
