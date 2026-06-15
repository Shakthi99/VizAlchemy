"""
Static mapping tables: Tableau → Power BI visual types, data types,
connection types, aggregation functions, and Tableau expression → DAX patterns.
"""

# ── Visual type mapping ────────────────────────────────────────────────────────

MARK_TO_VISUAL: dict[str, tuple[str, float, str]] = {
    # mark_type -> (pbi_visual_type, confidence, review_note)
    "bar":          ("barChart",         0.95, ""),
    "bar_h":        ("barChart",         0.90, "Set orientation=horizontal"),
    "line":         ("lineChart",        0.95, ""),
    "area":         ("areaChart",        0.90, ""),
    "circle":       ("scatterChart",     0.85, ""),
    "square":       ("scatterChart",     0.80, "Map shape to scatter"),
    "text":         ("tableEx",          0.85, ""),
    "pie":          ("pieChart",         0.90, ""),
    "map":          ("filledMap",        0.80, "Verify geo field is recognised by PBI"),
    "filled_map":   ("filledMap",        0.80, ""),
    "symbol_map":   ("map",              0.75, "Verify lat/lon fields"),
    "gantt":        ("gantt",            0.55, "Requires AppSource Gantt visual"),
    "polygon":      ("shapeMap",         0.50, "Requires custom shape file"),
    "density":      ("map",              0.45, "Density layer not native in PBI"),
    "automatic":    ("barChart",         0.70, "Tableau chose automatic — review"),
}

# ── Aggregation mapping ────────────────────────────────────────────────────────

AGG_MAP: dict[str, str] = {
    "SUM":          "SUM",
    "AVG":          "AVERAGE",
    "COUNT":        "COUNT",
    "COUNTD":       "DISTINCTCOUNT",
    "MIN":          "MIN",
    "MAX":          "MAX",
    "MEDIAN":       "MEDIAN",
    "STDEV":        "STDEV.S",
    "STDEVP":       "STDEV.P",
    "VAR":          "VAR.S",
    "VARP":         "VAR.P",
    "ATTR":         "SELECTEDVALUE",
    "NONE":         "",
    "YEAR":         "YEAR",
    "QUARTER":      "QUARTER",
    "MONTH":        "MONTH",
    "DAY":          "DAY",
}

# ── Data type mapping ──────────────────────────────────────────────────────────

DTYPE_MAP: dict[str, str] = {
    "string":    "Text",
    "integer":   "WholeNumber",
    "real":      "Decimal Number",
    "boolean":   "True/False",
    "date":      "Date",
    "datetime":  "Date/Time",
    "spatial":   "Text",           # no direct PBI equivalent
}

# ── Connection type mapping ────────────────────────────────────────────────────

CONN_TYPE_MAP: dict[str, dict] = {
    "sqlserver": {
        "m_source": 'Sql.Database("{server}", "{database}")',
        "mode": "DirectQuery",
    },
    "mysql": {
        "m_source": 'MySQL.Database("{server}", "{database}")',
        "mode": "DirectQuery",
    },
    "postgres": {
        "m_source": 'PostgreSQL.Database("{server}", "{database}")',
        "mode": "DirectQuery",
    },
    "oracle": {
        "m_source": 'Oracle.Database("{server}")',
        "mode": "DirectQuery",
    },
    "bigquery": {
        "m_source": 'GoogleBigQuery.Database()',
        "mode": "Import",
    },
    "snowflake": {
        "m_source": 'Snowflake.Databases("{server}")',
        "mode": "DirectQuery",
    },
    "redshift": {
        "m_source": 'AmazonRedshift.Database("{server}", "{database}")',
        "mode": "Import",
    },
    "csv":       {
        "m_source": 'Csv.Document(File.Contents("{table}"))',
        "mode": "Import",
    },
    "excel":     {
        "m_source": 'Excel.Workbook(File.Contents("{table}"), null, true)',
        "mode": "Import",
    },
    "unknown":   {
        "m_source": '/* TODO: configure data source */',
        "mode": "Import",
    },
}

# ── Tableau formula → DAX pattern catalog ─────────────────────────────────────
# Each entry: (regex_pattern, dax_template, confidence, review_note)
# Templates use {field} placeholders replaced at generation time.

FORMULA_PATTERNS: list[tuple[str, str, float, str]] = [
    # Basic aggregates — high confidence
    (r"SUM\(\[(.+?)\]\)",          "SUM({table}[{field}])",                       0.95, ""),
    (r"AVG\(\[(.+?)\]\)",          "AVERAGE({table}[{field}])",                   0.95, ""),
    (r"COUNT\(\[(.+?)\]\)",        "COUNT({table}[{field}])",                     0.95, ""),
    (r"COUNTD\(\[(.+?)\]\)",       "DISTINCTCOUNT({table}[{field}])",             0.95, ""),
    (r"MIN\(\[(.+?)\]\)",          "MIN({table}[{field}])",                       0.95, ""),
    (r"MAX\(\[(.+?)\]\)",          "MAX({table}[{field}])",                       0.95, ""),
    (r"MEDIAN\(\[(.+?)\]\)",       "MEDIAN({table}[{field}])",                    0.90, ""),

    # Null handling
    (r"ISNULL\(\[(.+?)\]\)",       "ISBLANK({table}[{field}])",                   0.90, ""),
    (r"ZN\((.+?)\)",               "IF(ISBLANK({inner}), 0, {inner})",            0.85, ""),
    (r"IFNULL\((.+?),\s*(.+?)\)",  "IF(ISBLANK({arg1}), {arg2}, {arg1})",        0.85, ""),

    # String functions
    (r"UPPER\(\[(.+?)\]\)",        "UPPER({table}[{field}])",                     0.95, ""),
    (r"LOWER\(\[(.+?)\]\)",        "LOWER({table}[{field}])",                     0.95, ""),
    (r"TRIM\(\[(.+?)\]\)",         "TRIM({table}[{field}])",                      0.95, ""),
    (r"LEN\(\[(.+?)\]\)",          "LEN({table}[{field}])",                       0.95, ""),
    (r"LEFT\(\[(.+?)\],\s*(\d+)\)","LEFT({table}[{field}], {n})",                 0.90, ""),
    (r"RIGHT\(\[(.+?)\],\s*(\d+)\)","RIGHT({table}[{field}], {n})",               0.90, ""),
    (r"MID\(\[(.+?)\],\s*(\d+),\s*(\d+)\)", "MID({table}[{field}], {start}, {len})", 0.90, ""),
    (r"CONTAINS\(\[(.+?)\],\s*\"(.+?)\"\)",  "CONTAINSSTRING({table}[{field}], \"{substr}\")", 0.85, ""),
    (r"STARTSWITH\(\[(.+?)\],\s*\"(.+?)\"\)", "LEFT({table}[{field}], LEN(\"{substr}\")) = \"{substr}\"", 0.80, ""),
    (r"ENDSWITH\(\[(.+?)\],\s*\"(.+?)\"\)",   "RIGHT({table}[{field}], LEN(\"{substr}\")) = \"{substr}\"", 0.80, ""),
    (r"REPLACE\(\[(.+?)\],\s*\"(.+?)\",\s*\"(.+?)\"\)", "SUBSTITUTE({table}[{field}], \"{old}\", \"{new}\")", 0.85, ""),

    # Date functions
    (r"TODAY\(\)",                 "TODAY()",                                     0.95, ""),
    (r"NOW\(\)",                   "NOW()",                                       0.95, ""),
    (r"YEAR\(\[(.+?)\]\)",         "YEAR({table}[{field}])",                      0.95, ""),
    (r"MONTH\(\[(.+?)\]\)",        "MONTH({table}[{field}])",                     0.95, ""),
    (r"DAY\(\[(.+?)\]\)",          "DAY({table}[{field}])",                       0.95, ""),
    (r"DATETRUNC\('month',\s*\[(.+?)\]\)", "DATE(YEAR({table}[{field}]), MONTH({table}[{field}]), 1)", 0.85, ""),
    (r"DATETRUNC\('year',\s*\[(.+?)\]\)",  "DATE(YEAR({table}[{field}]), 1, 1)",  0.85, ""),
    (r"DATEADD\('day',\s*(\d+),\s*\[(.+?)\]\)", "{table}[{field}] + {n}",        0.80, ""),
    (r"DATEDIFF\('day',\s*\[(.+?)\],\s*\[(.+?)\]\)", "DATEDIFF({table}[{f1}], {table}[{f2}], DAY)", 0.80, ""),
    (r"DATEDIFF\('month',\s*\[(.+?)\],\s*\[(.+?)\]\)", "DATEDIFF({table}[{f1}], {table}[{f2}], MONTH)", 0.80, ""),

    # LOD Expressions — lower confidence
    (r"\{FIXED\s+\[(.+?)\]\s*:\s*SUM\(\[(.+?)\]\)\}",
     "CALCULATE(SUM({table}[{measure}]), REMOVEFILTERS(), VALUES({table}[{dim}]))",
     0.65, "FIXED LOD — verify filter context is correct"),
    (r"\{FIXED\s+\[(.+?)\]\s*:\s*AVG\(\[(.+?)\]\)\}",
     "CALCULATE(AVERAGE({table}[{measure}]), REMOVEFILTERS(), VALUES({table}[{dim}]))",
     0.65, "FIXED LOD — verify filter context"),
    (r"\{INCLUDE\s+\[(.+?)\]\s*:\s*(.+?)\}",
     "CALCULATE({inner}, SUMMARIZE({table}, {table}[{dim}]))",
     0.55, "INCLUDE LOD — manual review recommended"),
    (r"\{EXCLUDE\s+\[(.+?)\]\s*:\s*(.+?)\}",
     "CALCULATE({inner}, REMOVEFILTERS({table}[{dim}]))",
     0.60, "EXCLUDE LOD — verify REMOVEFILTERS scope"),

    # Table calculations — low confidence
    (r"RUNNING_SUM\((.+?)\)",
     "CALCULATE({inner}, DATESYTD(Date[Date]))",
     0.50, "Table calc — requires date table and proper context"),
    (r"WINDOW_SUM\((.+?)\)",
     "CALCULATE({inner}, ALLSELECTED())",
     0.45, "Table calc — window context differs from DAX"),
    (r"RANK\(\)",
     "RANKX(ALL({table}[{dim}]), [{measure}])",
     0.55, "RANK — verify partition field"),
    (r"RUNNING_AVG\((.+?)\)",
     "AVERAGEX(DATESYTD(Date[Date]), {inner})",
     0.45, "Table calc — needs date table"),

    # Conditional
    (r"IIF\((.+?),\s*(.+?),\s*(.+?)\)",
     "IF({condition}, {true_val}, {false_val})",
     0.85, ""),
    (r"IF (.+?) THEN (.+?) ELSE (.+?) END",
     "IF({condition}, {true_val}, {false_val})",
     0.80, "Multi-branch IF — may need SWITCH"),

    # ATTR
    (r"ATTR\(\[(.+?)\]\)",
     "IF(HASONEVALUE({table}[{field}]), VALUES({table}[{field}]), BLANK())",
     0.75, "ATTR — single-value check"),
]

# ── Visual shelf → PBI field well mapping ─────────────────────────────────────

SHELF_TO_WELL: dict[str, str] = {
    "rows":    "values",
    "cols":    "axis",
    "color":   "legend",
    "size":    "size",
    "label":   "labels",
    "detail":  "details",
    "tooltip": "tooltips",
    "filter":  "filters",
}
