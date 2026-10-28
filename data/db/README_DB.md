# SmartCart e-commerce database

Built from the real Retailrocket files by `smartcart_ecommerce_database.ipynb`.

## Files
- `ecommerce.db`: SQLite database
- `schema.sql`: the same schema (tables, keys, indexes, views) for loading into another database
- `item_enrichment.csv`, `category_names.csv`: the generated product layer that the products table is built from

## Entity relationships
```
categories 1---* products 1---* order_items *---1 orders *---1 customers 1---1 customer_features
                    |                                 |            |
                    +---* events *---1 sessions *-----+------------+
                    +---* cart_items *---1 customers
daily_stats (one row per UTC day)        db_info (origin and settings)
```

## Real, derived and generated
| | |
|---|---|
| real | events, ids, timestamps, transaction ids, category tree, `products.in_stock` |
| derived from the real events | sessions (30-minute gap), orders, order items, carts, counts, conversion, customer features that do not use prices |
| generated from the id and a fixed seed | product name, brand, price, price tier, deal flag, category names, departments, and everything that sums prices (order values, customer spend, revenue) |

Generated fields are labelled with `*_is_synthetic`. Numbers built on generated prices are not business figures.

## Joining to the raw files
`products.item_id`, `events.item_id`, `order_items.item_id` = `itemid`; `customers.visitor_id`, `events.visitor_id` = `visitorid`; `orders.order_id` = `transactionid`; `categories.category_id` = `categoryid`.

## Example queries
```sql
SELECT name, price FROM products WHERE department = 'Electronics' AND in_stock = 1 ORDER BY price LIMIT 10;
SELECT segment_rule, COUNT(*) FROM customer_features GROUP BY segment_rule;
SELECT visitor_id, total_spent FROM customers ORDER BY total_spent DESC LIMIT 10;
SELECT * FROM v_order_details WHERE visitor_id = 1;
```

## Running models on it
```python
import sqlite3, pandas as pd
con = sqlite3.connect("ecommerce.db")
X = pd.read_sql("SELECT * FROM customer_features WHERE n_orders > 0", con)
events = pd.read_sql("SELECT * FROM events WHERE ts >= 1437000000000", con)
```
Split by time (the `ts` column), never at random, and compute features only from events before the cut-off.
