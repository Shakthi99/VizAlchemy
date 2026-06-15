# Migration Plan: Tableau → Power BI

## Objective
Migrate the Shopping Tableau workbook (.twb) to a fully functional Power BI project (.pbip) with:
- Complete data model (TMDL)
- DAX measures equivalent to Tableau calculated fields
- Visual report layout (PBIR/report.json)
- Proper relationships between tables

## Phases

### Phase 1: Tableau Parsing
- Parse .twb XML to extract datasources, columns, relationships, worksheets, dashboards
- Build an Intermediate Representation (IR) of the workbook

### Phase 2: DAX Translation
- Convert Tableau calculated fields (e.g., TRIM, aggregations) to DAX equivalents
- Generate Power BI measures from Tableau aggregation patterns

### Phase 3: Visual Mapping
- Map Tableau mark types (Bar, Line, Area, Pie, Square, Shape, Map) to Power BI visual types
- Translate encodings (rows/cols/color/size/text) to Power BI projections

### Phase 4: Semantic Model Generation
- Generate TMDL files for tables, columns, measures, relationships
- Generate Power Query M expressions for data loading

### Phase 5: Report Generation
- Generate report.json with visual containers
- Generate definition.pbir linking to the dataset
- Package as .pbip ZIP archive

### Phase 6: Streamlit UI
- Upload .twb file
- Configure data source paths
- Run conversion pipeline
- Download generated .pbip

## Data Sources
| Table | File | Key Columns |
|-------|------|-------------|
| orders | orders.csv | order_id, order_date, customer_id, total_price |
| customers | customers.csv | customer_id, first_name, last_name, address, email, phone_number |
| order_items | order_items.csv | order_item_id, order_id, product_id, quantity, price_at_purchase |
| products | products.csv | product_id, product_name, category, price, supplier_id |
| reviews | reviews.csv | review_id, product_id, customer_id, rating, review_text, review_date |
| payment | payment.csv | payment_id, order_id, payment_method, amount, transaction_status |
| states_full_50states | states_full_50states.csv | customer_id, state, state_full |

## Worksheets to Migrate
1. Total Revenue (Card) - SUM(total_price)
2. Total Orders (Card) - COUNTD(order_id)
3. Average Customers (Card) - AVG(customer_id)
4. Max Payment (Card) - MAX(amount)
5. Month wise Order (Line) - MONTH(order_date) vs COUNT(order_id)
6. Category wise Revenue (Bar) - category vs SUM(total_price)
7. Payment Volume (Column) - payment_method × transaction_status vs COUNTD(payment_id)
8. Order Volume (Heatmap/Matrix) - MONTH×DAY(order_date) vs COUNT(order_id)
9. Productwise Quantity (Treemap) - product_name vs SUM(quantity)
10. Monthwise Average Quantity (Column+Line) - MONTH(order_date) vs AVG(quantity) + SUM(total_price)
11. Month wise shipment status (Area) - MONTH(shipment_date) × shipment_status vs SUM(total_price)
12. Ratings (Histogram) - Rating(bin) vs COUNT(rating)
13. Statewise Amount (Map) - TRIM(state_full) vs SUM(amount)
14. Statewise Revenue (Filled Map) - TRIM(state_full) vs SUM(amount)
15. Carrier Amount (Pie) - carrier vs SUM(amount)
16. Product wise Price (Scatter) - product_name vs SUM(price_at_purchase)
