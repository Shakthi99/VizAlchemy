# Tasks

## Phase 1: Core Infrastructure
- [x] Task 1.1: Create project folder structure
- [x] Task 1.2: Define IR Pydantic models
- [x] Task 1.3: Setup configuration and logging

## Phase 2: Tableau Parser
- [x] Task 2.1: Implement datasource parser (connections, tables, columns)
- [x] Task 2.2: Implement worksheet parser (marks, encodings, rows/cols)
- [x] Task 2.3: Implement dashboard parser (zones, layout)
- [x] Task 2.4: Implement calculated fields parser

## Phase 3: DAX Translation
- [x] Task 3.1: Implement type mapping (Tableau → Power BI data types)
- [x] Task 3.2: Implement aggregation translation (SUM, AVG, COUNT, COUNTD, MAX, MIN)
- [x] Task 3.3: Implement calculated field translation (TRIM → TRIM, etc.)
- [x] Task 3.4: Generate DAX measures from worksheet aggregations

## Phase 4: Visual Mapping
- [x] Task 4.1: Map Tableau mark types to Power BI visual types
- [x] Task 4.2: Map encodings (rows/cols/color/size/text) to projections
- [x] Task 4.3: Handle special visuals (maps, treemaps, histograms)

## Phase 5: Power BI Generation
- [x] Task 5.1: Generate TMDL (tables, columns, measures, relationships)
- [x] Task 5.2: Generate Power Query M expressions
- [x] Task 5.3: Generate report.json with visual containers
- [x] Task 5.4: Generate definition files (.pbip, .pbism, .pbir, .pmdl)
- [x] Task 5.5: Package into ZIP archive

## Phase 6: Streamlit UI
- [x] Task 6.1: File upload interface
- [x] Task 6.2: Data source configuration
- [x] Task 6.3: Conversion progress display
- [x] Task 6.4: Download interface
- [x] Task 6.5: Error handling and validation display
