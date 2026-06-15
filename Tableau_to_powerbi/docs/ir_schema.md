# IR Schema: Intermediate Representation Models

## WorkbookIR (Root)
```python
class WorkbookIR:
    name: str
    source_file: str
    datasources: list[DatasourceIR]
    worksheets: list[WorksheetIR]
    dashboards: list[DashboardIR]
    calculated_fields: list[CalculatedFieldIR]
```

## DatasourceIR
```python
class DatasourceIR:
    name: str
    caption: str
    tables: list[TableIR]
    relationships: list[RelationshipIR]
    column_mappings: dict[str, str]  # local_name → table.column
```

## TableIR
```python
class TableIR:
    name: str
    connection_name: str
    filename: str
    columns: list[ColumnIR]
```

## ColumnIR
```python
class ColumnIR:
    name: str
    remote_name: str
    datatype: str  # integer, real, string, date, datetime
    role: str  # dimension, measure
    aggregation: str | None  # Sum, Avg, Count, etc.
```

## RelationshipIR
```python
class RelationshipIR:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
```

## CalculatedFieldIR
```python
class CalculatedFieldIR:
    name: str
    caption: str
    formula: str  # Tableau formula
    datatype: str
    parent_table: str
    dax_expression: str | None  # Translated DAX
```

## WorksheetIR
```python
class WorksheetIR:
    name: str
    mark_type: str  # Automatic, Bar, Line, Area, Pie, Square, Shape, Map
    datasource_name: str
    rows: list[FieldReference]
    cols: list[FieldReference]
    encodings: EncodingsIR
    measures: list[MeasureIR]
```

## FieldReference
```python
class FieldReference:
    column_name: str
    derivation: str  # None, Sum, Avg, Count, CountD, Max, Min, Month, Day
    field_type: str  # quantitative, nominal, ordinal
    table_name: str | None
```

## EncodingsIR
```python
class EncodingsIR:
    color: FieldReference | None
    size: FieldReference | None
    text: FieldReference | None
    wedge_size: FieldReference | None
    lod: FieldReference | None
    geometry: FieldReference | None
```

## MeasureIR
```python
class MeasureIR:
    name: str
    dax_expression: str
    format_string: str
    table_name: str
```

## DashboardIR
```python
class DashboardIR:
    name: str
    width: int
    height: int
    zones: list[ZoneIR]
```

## ZoneIR
```python
class ZoneIR:
    id: int
    worksheet_name: str | None
    x: float
    y: float
    w: float
    h: float
```
