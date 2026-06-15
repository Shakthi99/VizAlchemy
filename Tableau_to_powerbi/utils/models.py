"""
Pydantic models for Tableau IR and Power BI output specs.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Tableau IR models ──────────────────────────────────────────────────────────

class TableauColumn(BaseModel):
    name: str
    caption: str = ""
    datatype: str = "string"
    role: str = "dimension"          # dimension | measure
    type: str = "nominal"            # nominal | ordinal | quantitative | temporal
    formula: str = ""                # empty for raw fields
    is_calculated: bool = False
    hidden: bool = False


class TableauJoin(BaseModel):
    join_type: str = "inner"         # inner | left | right | full
    left_table: str = ""
    right_table: str = ""
    left_key: str = ""
    right_key: str = ""


class TableauDataSource(BaseModel):
    name: str
    caption: str = ""
    connection_type: str = "unknown" # sqlserver | mysql | postgres | csv | excel | ...
    server: str = ""
    database: str = ""
    schema_name: str = ""
    table: str = ""
    custom_sql: str = ""
    columns: list[TableauColumn] = Field(default_factory=list)
    joins: list[TableauJoin] = Field(default_factory=list)
    parameters: list[dict[str, Any]] = Field(default_factory=list)


class TableauFilter(BaseModel):
    field: str
    filter_type: str = "categorical"  # categorical | range | relative_date | top_n
    values: list[str] = Field(default_factory=list)
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    include_nulls: bool = False
    datasource: str = ""


class TableauEncoding(BaseModel):
    """A single shelf assignment: rows, cols, color, size, label, detail, tooltip."""
    shelf: str          # rows | cols | color | size | label | detail | tooltip | filter
    field: str
    aggregation: str = "SUM"  # SUM | AVG | COUNT | COUNTD | MIN | MAX | ATTR | NONE
    alias: str = ""


class TableauWorksheet(BaseModel):
    name: str
    datasource: str = ""
    mark_type: str = "bar"           # bar | line | area | circle | square | text | map | pie | gantt
    encodings: list[TableauEncoding] = Field(default_factory=list)
    filters: list[TableauFilter] = Field(default_factory=list)
    title: str = ""
    rows: list[str] = Field(default_factory=list)
    cols: list[str] = Field(default_factory=list)


class DashboardObject(BaseModel):
    object_type: str   # worksheet | text | image | blank | container
    name: str = ""
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


class TableauDashboard(BaseModel):
    name: str
    width: float = 1366
    height: float = 768
    objects: list[DashboardObject] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)


class TableauParameter(BaseModel):
    name: str
    caption: str = ""
    datatype: str = "string"
    current_value: str = ""
    allowable_values: str = "all"    # all | list | range
    values: list[str] = Field(default_factory=list)


class TableauIR(BaseModel):
    """Root Intermediate Representation for one .twb workbook."""
    workbook_name: str
    source_file: str
    datasources: list[TableauDataSource] = Field(default_factory=list)
    worksheets: list[TableauWorksheet] = Field(default_factory=list)
    dashboards: list[TableauDashboard] = Field(default_factory=list)
    parameters: list[TableauParameter] = Field(default_factory=list)


# ── Power BI output models ─────────────────────────────────────────────────────

class MQueryTable(BaseModel):
    table_name: str
    datasource_name: str
    m_expression: str
    connection_type: str = ""


class DAXMeasure(BaseModel):
    name: str
    expression: str
    table: str = "Measures"
    format_string: str = ""
    source_formula: str = ""         # original Tableau formula
    confidence: float = 1.0          # 0-1 confidence in translation
    needs_review: bool = False
    review_reason: str = ""


class PBIVisual(BaseModel):
    visual_type: str                 # barChart | lineChart | columnChart | ...
    title: str = ""
    x_pct: float = 0
    y_pct: float = 0
    w_pct: float = 0
    h_pct: float = 0
    fields: dict[str, list[str]] = Field(default_factory=dict)  # axis/values/legend -> [field]
    filters: list[dict[str, Any]] = Field(default_factory=list)
    source_worksheet: str = ""
    table_name: str = ""             # Power BI table name for the primary datasource
    confidence: float = 1.0
    needs_review: bool = False
    review_reason: str = ""


class PBIReportPage(BaseModel):
    name: str
    visuals: list[PBIVisual] = Field(default_factory=list)
    source_dashboard: str = ""


class PBIOutput(BaseModel):
    """Everything needed to reconstruct a Power BI report."""
    workbook_name: str
    m_queries: list[MQueryTable] = Field(default_factory=list)
    dax_measures: list[DAXMeasure] = Field(default_factory=list)
    report_pages: list[PBIReportPage] = Field(default_factory=list)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
