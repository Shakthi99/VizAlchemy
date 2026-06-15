# DAX Translation Catalog

## Measures Generated from Tableau Worksheets

### KPI Cards
```dax
Total Revenue = SUM('orders'[total_price])
Total Orders = DISTINCTCOUNT('orders'[order_id])
Average Customers = AVERAGE('orders'[customer_id])
Max Payment = MAX('payment'[amount])
```

### Aggregation Measures
```dax
Order Count = COUNT('orders'[order_id])
Payment Count = DISTINCTCOUNT('payment'[payment_id])
Total Quantity = SUM('order_items'[quantity])
Average Quantity = AVERAGE('order_items'[quantity])
Total Amount = SUM('payment'[amount])
Rating Count = COUNT('reviews'[rating])
Total Price At Purchase = SUM('order_items'[price_at_purchase])
```

### Calculated Columns
```dax
Clean_state = TRIM('states_full_50states'[state_full])
```

### Date Intelligence (derived from Month derivations)
```dax
Order Month = MONTH('orders'[order_date])
Order Day = DAY('orders'[order_date])
Shipment Month = MONTH('shipments'[shipment_date])
```

## Translation Rules

### Aggregation Derivation → DAX

| Tableau Derivation Pattern | DAX Output |
|---|---|
| `derivation='Sum' column='[col]'` | `SUM('table'[col])` |
| `derivation='Avg' column='[col]'` | `AVERAGE('table'[col])` |
| `derivation='Count' column='[col]'` | `COUNT('table'[col])` |
| `derivation='CountD' column='[col]'` | `DISTINCTCOUNT('table'[col])` |
| `derivation='Max' column='[col]'` | `MAX('table'[col])` |
| `derivation='Min' column='[col]'` | `MIN('table'[col])` |
| `derivation='Month' column='[col]'` (dimension) | Date hierarchy |
| `derivation='Day' column='[col]'` (dimension) | Date hierarchy |

### Tableau Calculation → DAX

| Tableau Formula | DAX Equivalent |
|---|---|
| `TRIM([state_full])` | `TRIM('states_full_50states'[state_full])` |
| `[Rating (bin)]` with `size='0.865'` | `ROUNDDOWN('reviews'[rating] / 0.865, 0) * 0.865` |

## Format Strings

| Measure | DAX Format String |
|---|---|
| Total Revenue | "$#,##0.00" |
| Total Orders | "#,##0" |
| Average Customers | "#,##0.00" |
| Max Payment | "$#,##0.00" |
| Order Count | "#,##0" |
| Total Quantity | "#,##0" |
| Average Quantity | "#,##0.00" |
| Total Amount | "$#,##0.00" |
