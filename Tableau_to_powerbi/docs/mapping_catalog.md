# Mapping Catalog: Tableau → Power BI Data Types

## Column Type Mapping

| Tableau Type | Power BI TMDL Type | Notes |
|---|---|---|
| integer | int64 | Direct mapping |
| real | double | Floating point |
| string | string | Text fields |
| date | dateTime | Date only → dateTime in PBI |
| datetime | dateTime | Full datetime |
| boolean | boolean | True/false |

## Aggregation Mapping

| Tableau Aggregation | DAX Function | Example |
|---|---|---|
| Sum | SUM() | SUM('orders'[total_price]) |
| Avg | AVERAGE() | AVERAGE('orders'[customer_id]) |
| Count | COUNT() | COUNT('orders'[order_id]) |
| CountD | DISTINCTCOUNT() | DISTINCTCOUNT('orders'[order_id]) |
| Max | MAX() | MAX('payment'[amount]) |
| Min | MIN() | MIN('payment'[amount]) |
| Median | MEDIAN() | MEDIAN('reviews'[rating]) |
| Attr | SELECTEDVALUE() | SELECTEDVALUE('products'[category]) |

## Calculated Field Translation

| Tableau Function | DAX Equivalent | Example |
|---|---|---|
| TRIM([field]) | TRIM('table'[field]) | TRIM('states_full_50states'[state_full]) |
| IF cond THEN a ELSE b END | IF(cond, a, b) | IF([rating] > 3, "Good", "Bad") |
| DATEPART('month', [date]) | MONTH([date]) | MONTH('orders'[order_date]) |
| DATEPART('year', [date]) | YEAR([date]) | YEAR('orders'[order_date]) |
| DATEPART('day', [date]) | DAY([date]) | DAY('orders'[order_date]) |
| [field1] + [field2] | [field1] + [field2] | Direct arithmetic |
| LEN([field]) | LEN([field]) | LEN('customers'[first_name]) |
| UPPER([field]) | UPPER([field]) | UPPER('customers'[first_name]) |
| LOWER([field]) | LOWER([field]) | LOWER('customers'[first_name]) |

## Relationship Mapping

| From Table | From Column | To Table | To Column | Cardinality |
|---|---|---|---|---|
| orders | customer_id | customers | customer_id | Many-to-One |
| order_items | order_id | orders | order_id | Many-to-One |
| order_items | product_id | products | product_id | Many-to-One |
| payment | order_id | orders | order_id | Many-to-One |
| reviews | product_id | products | product_id | Many-to-One |
| shipments | order_id | orders | order_id | Many-to-One |
| states_full_50states | customer_id | orders | customer_id | Many-to-One |
| products | supplier_id | suppliers | supplier_id | Many-to-One |
