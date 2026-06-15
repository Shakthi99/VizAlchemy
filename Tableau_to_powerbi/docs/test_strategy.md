# Test Strategy

## Unit Tests

### Parser Tests
- `test_datasource_parser`: Verify correct extraction of tables, columns, types
- `test_worksheet_parser`: Verify mark types, encodings, row/col fields
- `test_dashboard_parser`: Verify zone extraction and layout
- `test_calculated_fields`: Verify formula extraction (TRIM)

### Translation Tests
- `test_type_mapper`: Verify all Tableau→PBI type conversions
- `test_dax_engine`: Verify aggregation→DAX translations
- `test_calculated_field_translation`: Verify TRIM → TRIM DAX

### Mapping Tests
- `test_visual_mapper`: Verify mark→visualType for all mark types
- `test_encoding_mapper`: Verify encoding→projection role mapping

### Generator Tests
- `test_tmdl_generation`: Verify valid TMDL output
- `test_report_json`: Verify valid report.json structure
- `test_pbip_packager`: Verify ZIP contains all required files

## Integration Tests
- `test_full_pipeline`: Upload Shopping.twb → get valid .pbip ZIP
- `test_zip_structure`: Verify all expected files present in ZIP
- `test_tmdl_parseable`: Verify TMDL syntax is well-formed

## Validation Criteria
- All 9 tables present in TMDL
- All 8 relationships defined
- All 16 worksheets mapped to visuals
- Measures generated for each card visual
- Clean_state calculated column present
- Report.json contains visualContainers for all worksheets
