# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                      │
│  Upload .twb → Configure → Convert → Download .pbip      │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                  Pipeline Orchestrator                     │
│  Coordinates parsing → IR → translation → generation      │
└──┬──────────────┬──────────────┬──────────────┬──────────┘
   │              │              │              │
┌──▼───┐   ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
│Parser│   │DAX Engine  │  │Visual   │  │PBI Gen    │
│Module│   │            │  │Mapper   │  │           │
└──┬───┘   └─────┬──────┘  └────┬────┘  └─────┬─────┘
   │              │              │              │
┌──▼──────────────▼──────────────▼──────────────▼──────────┐
│              Intermediate Representation (IR)              │
│  WorkbookIR → DatasourceIR → WorksheetIR → DashboardIR   │
└──────────────────────────────────────────────────────────┘
```

## Module Structure

```
workspace/
├── streamlit_app.py                  # Active Streamlit entry point
├── tableau_to_powerbi/
│   ├── config.py                     # Application configuration
│   ├── pipeline.py                   # Orchestrator
│   ├── ir/
│   │   └── __init__.py               # Dataclass IR models
│   ├── parser/
│   │   └── __init__.py               # Tableau XML parsing
│   ├── translation/
│   │   └── __init__.py               # Tableau calc → DAX
│   ├── mapping/
│   │   └── __init__.py               # Visual mapping
│   ├── generator/
│   │   ├── semantic_model.py         # TMDL generation
│   │   ├── report_generator.py       # report.json generation
│   │   └── pbip_packager.py          # ZIP packaging
│   └── utils/
│       └── __init__.py               # Logging setup
└── Dataset/                          # CSV files used by refresh
```

## Data Flow

1. **Input**: User uploads .twb file via Streamlit
2. **Parse**: `twb_parser` extracts XML → populates IR models
3. **Translate**: `dax_engine` converts Tableau calcs to DAX
4. **Map**: `visual_mapper` converts Tableau marks to PBI visual types
5. **Generate**: `semantic_model` + `report_generator` produce TMDL/PBIR
6. **Package**: `pbip_packager` assembles ZIP archive
7. **Output**: User downloads .pbip ZIP

## Technology Stack
- Python 3.11+
- Streamlit (UI)
- lxml (XML parsing)
- Pydantic (data models)
- zipfile (archive generation)
