"""Intermediate Representation models for Tableau → Power BI migration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ColumnIR:
    """Represents a table column."""
    name: str
    remote_name: str = ""
    datatype: str = "string"  # integer, real, string, date, datetime
    role: str = "dimension"  # dimension | measure
    aggregation: Optional[str] = None  # Sum, Avg, Count, etc.


@dataclass
class TableIR:
    """Represents a data table."""
    name: str
    connection_name: str = ""
    filename: str = ""
    columns: list[ColumnIR] = field(default_factory=list)


@dataclass
class RelationshipIR:
    """Represents a relationship between two tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class DatasourceIR:
    """Represents a Tableau datasource."""
    name: str
    caption: str = ""
    tables: list[TableIR] = field(default_factory=list)
    relationships: list[RelationshipIR] = field(default_factory=list)
    column_mappings: dict[str, str] = field(default_factory=dict)


@dataclass
class CalculatedFieldIR:
    """Represents a Tableau calculated field."""
    name: str
    caption: str = ""
    formula: str = ""
    datatype: str = "string"
    parent_table: str = ""
    dax_expression: Optional[str] = None


@dataclass
class FieldReference:
    """Represents a field reference in a worksheet."""
    column_name: str
    derivation: str = "None"  # None, Sum, Avg, Count, CountD, Max, Min, Month, Day
    field_type: str = "nominal"  # quantitative, nominal, ordinal
    table_name: Optional[str] = None


@dataclass
class EncodingsIR:
    """Represents visual encodings of a worksheet."""
    color: Optional[FieldReference] = None
    size: Optional[FieldReference] = None
    text: Optional[FieldReference] = None
    wedge_size: Optional[FieldReference] = None
    lod: Optional[FieldReference] = None
    geometry: Optional[FieldReference] = None


@dataclass
class MeasureIR:
    """Represents a DAX measure to be generated."""
    name: str
    dax_expression: str
    format_string: str = "#,##0"
    table_name: str = ""


@dataclass
class WorksheetIR:
    """Represents a Tableau worksheet."""
    name: str
    mark_type: str = "Automatic"
    datasource_name: str = ""
    rows: list[FieldReference] = field(default_factory=list)
    cols: list[FieldReference] = field(default_factory=list)
    encodings: EncodingsIR = field(default_factory=EncodingsIR)
    measures: list[MeasureIR] = field(default_factory=list)


@dataclass
class ZoneIR:
    """Represents a dashboard zone."""
    id: int
    worksheet_name: Optional[str] = None
    x: float = 0
    y: float = 0
    w: float = 0
    h: float = 0


@dataclass
class DashboardIR:
    """Represents a Tableau dashboard."""
    name: str
    width: int = 1220
    height: int = 2160
    zones: list[ZoneIR] = field(default_factory=list)


@dataclass
class WorkbookIR:
    """Root IR representing the entire Tableau workbook."""
    name: str
    source_file: str = ""
    data_directory: str = ""
    datasources: list[DatasourceIR] = field(default_factory=list)
    worksheets: list[WorksheetIR] = field(default_factory=list)
    dashboards: list[DashboardIR] = field(default_factory=list)
    calculated_fields: list[CalculatedFieldIR] = field(default_factory=list)
