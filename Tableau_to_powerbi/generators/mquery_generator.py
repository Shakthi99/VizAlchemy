"""
Power Query M generator — converts Tableau datasource IR into M queries.
"""
from __future__ import annotations

import logging
from tableau_to_pbi.utils.models import TableauDataSource, TableauJoin, MQueryTable
from tableau_to_pbi.utils.mappings import CONN_TYPE_MAP

log = logging.getLogger(__name__)

JOIN_KIND_MAP = {
    "inner": "JoinKind.Inner",
    "left":  "JoinKind.LeftOuter",
    "right": "JoinKind.RightOuter",
    "full":  "JoinKind.FullOuter",
    "all":   "JoinKind.LeftOuter",
}


def _m_source(ds: TableauDataSource) -> str:
    tpl = CONN_TYPE_MAP.get(ds.connection_type, CONN_TYPE_MAP["unknown"])["m_source"]
    return (
        tpl
        .replace("{server}", ds.server or "YOUR_SERVER")
        .replace("{database}", ds.database or "YOUR_DATABASE")
        .replace("{table}", ds.table or "YOUR_TABLE")
    )


def _m_table_ref(ds: TableauDataSource) -> str:
    """M expression to reach the base table / custom SQL."""
    src = _m_source(ds)
    if ds.custom_sql:
        safe_sql = ds.custom_sql.replace('"', '""')
        return (
            f'let\n'
            f'    Source = {src},\n'
            f'    Data = Value.NativeQuery(Source, "{safe_sql}", null, [EnableFolding=true])\n'
            f'in\n'
            f'    Data'
        )

    schema_part = f', [Schema="{ds.schema_name}"]' if ds.schema_name else ""
    table_part = f'Source{{[Schema="{ds.schema_name}", Item="{ds.table}"]}}'
    if not ds.schema_name:
        table_part = f'Source{{[Item="{ds.table}"]}}'

    return (
        f'let\n'
        f'    Source = {src},\n'
        f'    Table = {table_part}[Data]\n'
        f'in\n'
        f'    Table'
    )


def _apply_joins(base_expr: str, ds: TableauDataSource) -> str:
    if not ds.joins:
        return base_expr

    lines = ["let"]
    # Unwrap existing let..in to extend it
    if base_expr.strip().startswith("let"):
        inner_lines = base_expr.strip().splitlines()
        # strip the trailing "in\n    <name>" lines
        in_idx = next((i for i, l in enumerate(inner_lines) if l.strip() == "in"), len(inner_lines) - 2)
        lines = inner_lines[:in_idx]
        last_step = inner_lines[in_idx + 1].strip()
    else:
        lines = ["let", f"    Base = {base_expr},"]
        last_step = "Base"

    prev_step = last_step
    for i, join in enumerate(ds.joins):
        join_step   = f"Joined_{i + 1}"
        expand_step = f"Expanded_{i + 1}"
        kind = JOIN_KIND_MAP.get(join.join_type.lower(), "JoinKind.Inner")
        right_ref = join.right_table or "RightTable"
        nested_col = f"{right_ref}_data"

        # Step 1: NestedJoin — produces a nested Table column
        lines.append(
            f'    {join_step} = Table.NestedJoin(\n'
            f'        {prev_step}, {{"{join.left_key}"}},\n'
            f'        {right_ref}, {{"{join.right_key}"}},\n'
            f'        "{nested_col}", {kind}\n'
            f'    ),'
        )
        # FIX: Step 2: ExpandTableColumn — flatten the nested Table column into real columns
        lines.append(
            f'    {expand_step} = Table.ExpandTableColumn(\n'
            f'        {join_step}, "{nested_col}",\n'
            f'        Table.ColumnNames({right_ref}),\n'
            f'        List.Transform(Table.ColumnNames({right_ref}), each "{right_ref}." & _)\n'
            f'    ),'
        )
        prev_step = expand_step

    lines.append("in")
    lines.append(f"    {prev_step}")
    return "\n".join(lines)


def generate_m_queries(datasources: list[TableauDataSource]) -> list[MQueryTable]:
    results: list[MQueryTable] = []
    for ds in datasources:
        try:
            base = _m_table_ref(ds)
            full_expr = _apply_joins(base, ds)
            conn_info = CONN_TYPE_MAP.get(ds.connection_type, CONN_TYPE_MAP["unknown"])
            results.append(MQueryTable(
                table_name=ds.caption or ds.name,
                datasource_name=ds.name,
                m_expression=full_expr,
                connection_type=conn_info.get("mode", "Import"),
            ))
            log.debug("Generated M query for datasource: %s", ds.name)
        except Exception as e:
            log.error("M query generation failed for %s: %s", ds.name, e)
    return results
