# Tableau → Power BI Migration Summary

## Coverage

Workbook          : sample_sales_dashboard
Overall Coverage  : 100.0%
  Field Coverage  : 100.0%  (7/7 calculated fields)
  Visual Coverage : 100.0%  (6/6 visuals auto-mapped)
  Datasources     : 1/1 mapped

Issues  : 0 errors, 0 warnings

## Source
- Workbook: `tableau_to_pbi/input_twb/sample_sales_dashboard.twb`
- Datasources: 1
- Worksheets: 6
- Dashboards: 2
- Calculated fields: 7
- Parameters: 0

## Output Files
- `powerquery/` — 1 M query file(s)
- `dax/measures.dax` — 12 DAX measure(s)
- `layout/report_pages.json` — 2 report page(s)
- `migration_report/field_mapping.csv` — full field lineage

## Next Steps
1. Open Power BI Desktop → `Get Data` → use M queries in `powerquery/`
2. Paste measures from `dax/measures.dax` into the DAX editor
3. Recreate visuals using `layout/report_pages.json` as a guide
4. Address all items in `manual_review.md`
5. Reconnect parameters as Power BI What-If parameters