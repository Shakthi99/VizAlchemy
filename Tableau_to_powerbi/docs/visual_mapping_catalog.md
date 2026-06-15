# Visual Mapping Catalog: Tableau → Power BI

## Mark Type → Visual Type Mapping

| Tableau Mark | Power BI Visual | visualType value | Notes |
|---|---|---|---|
| Automatic (with rows+cols) | clusteredBarChart | clusteredBarChart | Default for bar-like |
| Automatic (text only) | card | card | KPI cards |
| Bar | clusteredBarChart | clusteredBarChart | Horizontal bars |
| Line | lineChart | lineChart | Time series |
| Area | areaChart | areaChart | Filled area |
| Pie | pieChart | pieChart | Proportional |
| Square (treemap) | treemap | treemap | Hierarchical size |
| Shape (scatter) | scatterChart | scatterChart | Point distribution |
| Automatic (heatmap) | matrix | matrix | Cross-tab with color |
| Map (symbol) | map | map | Geographic bubbles |
| Map (filled/geometry) | filledMap | filledMap | Choropleth |
| Histogram | clusteredColumnChart | clusteredColumnChart | Binned distribution |

## Encoding → Projection Mapping

| Tableau Encoding | Power BI Projection Role | Notes |
|---|---|---|
| cols (dimension) | Category / Axis | X-axis dimension |
| rows (measure) | Values | Y-axis measure |
| rows (dimension) | Rows (matrix) | Row grouping |
| color (dimension) | Legend / Series | Color by category |
| color (measure) | Values (gradient) | Color saturation |
| size (measure) | Size | Bubble/mark size |
| text (measure) | Values (card) | Display value |
| wedge-size | Values (pie) | Pie slice size |
| lod (dimension) | Category (detail) | Level of detail |
| geometry | Location | Map geography |

## Specific Worksheet → Visual Mapping

| Worksheet | PBI Visual | Category | Values | Series |
|---|---|---|---|---|
| Total Revenue | card | - | SUM(total_price) | - |
| Total Orders | card | - | DISTINCTCOUNT(order_id) | - |
| Average Customers | card | - | AVERAGE(customer_id) | - |
| Max Payment | card | - | MAX(amount) | - |
| Month wise Order | lineChart | MONTH(order_date) | COUNT(order_id) | - |
| Category wise Revenue | clusteredBarChart | category | SUM(total_price) | - |
| Payment Volume | clusteredColumnChart | payment_method | DISTINCTCOUNT(payment_id) | transaction_status |
| Order Volume | matrix | MONTH(order_date) | COUNT(order_id) | DAY(order_date) |
| Productwise Quantity | treemap | product_name | SUM(quantity) | - |
| Monthwise Average Quantity | clusteredColumnChart | MONTH(order_date) | AVERAGE(quantity) | - |
| Month wise shipment status | areaChart | MONTH(shipment_date) | SUM(total_price) | shipment_status |
| Ratings | clusteredColumnChart | Rating(bin) | COUNT(rating) | - |
| Statewise Amount | map | Clean_state | SUM(amount) | - |
| Statewise Revenue | filledMap | Clean_state | SUM(amount) | - |
| Carrier Amount | pieChart | carrier | SUM(amount) | - |
| Product wise Price | scatterChart | product_name | SUM(price_at_purchase) | - |
