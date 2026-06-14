# Tableau → Power BI Migrator

Automated migration tool that converts Tableau workbooks (.twb) to Power BI projects (.pbip).

## Features

- **Full XML Parsing**: Extracts datasources, columns, relationships, worksheets, dashboards, and calculated fields from Tableau .twb files
- **DAX Translation**: Converts Tableau aggregations and calculated fields to DAX measures
- **Visual Mapping**: Maps Tableau mark types (Bar, Line, Area, Pie, Map, etc.) to Power BI visual types
- **Semantic Model Generation**: Produces TMDL files with tables, columns, measures, relationships, and Power Query M expressions
- **Report Layout Generation**: Creates report.json with proper visual containers and layout
- **PBIP Packaging**: Assembles a complete Power BI project (.pbip) as a downloadable ZIP

## Project Structure

```
tableau_to_powerbi/
├── streamlit_app.py              # Streamlit entry point
├── requirements.txt              # Python dependencies
├── tableau_to_powerbi/           # Core package
│   ├── __init__.py
│   ├── config.py                 # Configuration
│   ├── pipeline.py               # Pipeline orchestrator
│   ├── ir/                       # Intermediate Representation models
│   │   └── __init__.py
│   ├── parser/                   # Tableau XML parser
│   │   └── __init__.py
│   ├── translation/              # DAX translation engine
│   │   └── __init__.py
│   ├── mapping/                  # Visual mapping engine
│   │   └── __init__.py
│   ├── generator/                # Power BI generators
│   │   ├── __init__.py           # PBIP packager
│   │   ├── semantic_model.py     # TMDL generator
│   │   └── report_generator.py   # report.json generator
│   └── utils/                    # Utilities
│       └── __init__.py           # Logging setup
├── docs/                         # Documentation
│   ├── plan.md
│   ├── architecture.md
│   ├── tasks.md
│   ├── mapping_catalog.md
│   ├── visual_mapping_catalog.md
│   ├── dax_translation_catalog.md
│   ├── ir_schema.md
│   ├── agent_rules.md
│   └── test_strategy.md
└── Dataset/                      # Sample data
    ├── customers.csv
    ├── orders.csv
    ├── order_items.csv
    ├── products.csv
    ├── payment.csv
    ├── reviews.csv
    └── states_full_50states.csv
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the application

```bash
streamlit run streamlit_app.py
```

### 3. Use the application

1. Open the browser (typically http://localhost:8501)
2. Upload your Tableau workbook (.twb file)
3. Configure the project name and data directory
4. Click "Run Migration"
5. Download the generated Power BI project (.zip)

### 4. Open in Power BI

1. Extract the downloaded ZIP file
2. Open the `.pbip` file in Power BI Desktop
3. Update the data source paths in Power Query to point to your CSV files
4. Refresh the data model

## Architecture

The migration follows a 6-phase pipeline:

1. **Parse** → Extract metadata from Tableau XML
2. **IR** → Build intermediate representation
3. **Translate** → Convert calculations to DAX
4. **Map** → Map visual types and encodings
5. **Generate** → Produce TMDL and report.json
6. **Package** → Assemble PBIP ZIP archive

## Supported Migrations

| Tableau Feature | Power BI Equivalent | Status |
|---|---|---|
| CSV Data Sources | Power Query M (Csv.Document) | ✅ |
| Table Relationships | Model Relationships | ✅ |
| Calculated Fields (TRIM) | DAX Calculated Columns | ✅ |
| SUM/AVG/COUNT/MAX aggregations | DAX Measures | ✅ |
| Bar/Line/Area/Pie charts | Corresponding PBI visuals | ✅ |
| Maps (symbol & filled) | Map & Filled Map visuals | ✅ |
| Treemaps | Treemap visual | ✅ |
| Dashboard layout | Report page layout | ✅ |
| KPI Cards | Card visuals | ✅ |

## Requirements

- Python 3.11+
- streamlit >= 1.28.0
- lxml >= 4.9.0
- pydantic >= 2.0.0
