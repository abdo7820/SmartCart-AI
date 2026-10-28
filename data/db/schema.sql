CREATE TABLE db_info (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    parent_id INTEGER REFERENCES categories(category_id),
    root_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    name_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE products (
    item_id INTEGER PRIMARY KEY,
    category_id INTEGER REFERENCES categories(category_id),
    raw_category_id INTEGER,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    product_type TEXT NOT NULL,
    department TEXT NOT NULL,
    price REAL NOT NULL CHECK (price > 0),
    currency TEXT NOT NULL,
    price_tier TEXT NOT NULL CHECK (price_tier IN ('budget', 'standard', 'premium')),
    price_vs_category_median REAL,
    is_deal INTEGER NOT NULL CHECK (is_deal IN (0, 1)),
    in_stock INTEGER CHECK (in_stock IN (0, 1)),
    price_proxy_790 REAL,
    name_is_synthetic INTEGER NOT NULL DEFAULT 1,
    price_is_synthetic INTEGER NOT NULL DEFAULT 1,
    first_seen_ts INTEGER NOT NULL,
    first_seen_utc TEXT NOT NULL,
    last_seen_ts INTEGER NOT NULL,
    n_views INTEGER NOT NULL,
    n_carts INTEGER NOT NULL,
    n_purchases INTEGER NOT NULL,
    n_buyers INTEGER NOT NULL,
    views_7d INTEGER NOT NULL,
    views_30d INTEGER NOT NULL,
    view_to_cart REAL,
    cart_to_buy REAL,
    age_days REAL,
    days_since_last_seen REAL,
    popularity_rank INTEGER
);

CREATE TABLE customers (
    visitor_id INTEGER PRIMARY KEY,
    first_seen_ts INTEGER NOT NULL,
    first_seen_utc TEXT NOT NULL,
    last_seen_ts INTEGER NOT NULL,
    last_seen_utc TEXT NOT NULL,
    n_events INTEGER NOT NULL,
    n_sessions INTEGER NOT NULL,
    n_orders INTEGER NOT NULL,
    total_spent REAL NOT NULL,
    spend_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE customer_features (
    visitor_id INTEGER PRIMARY KEY REFERENCES customers(visitor_id),
    n_events INTEGER, n_views INTEGER, n_carts INTEGER, n_purchases INTEGER, n_items INTEGER, n_sessions INTEGER, n_orders INTEGER,
    days_since_last_event REAL, tenure_days REAL, days_since_last_purchase REAL, days_to_first_purchase REAL,
    mean_gap_days REAL, max_gap_days REAL, overdue_ratio REAL,
    n_cart_items INTEGER, n_cart_abandoned INTEGER, cart_abandon_rate REAL,
    n_categories INTEGER, fav_category_id INTEGER REFERENCES categories(category_id), fav_department TEXT,
    unavailable_exposure REAL, price_proxy_790_mean REAL, weekend_share REAL, peak_hour INTEGER,
    total_spent REAL, avg_order_value REAL, last_order_value REAL, avg_price_viewed REAL, deal_share REAL, budget_share REAL,
    segment_rule TEXT NOT NULL,
    value_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE sessions (
    session_id INTEGER PRIMARY KEY,
    visitor_id INTEGER NOT NULL REFERENCES customers(visitor_id),
    start_ts INTEGER NOT NULL,
    start_utc TEXT NOT NULL,
    end_ts INTEGER NOT NULL,
    duration_s REAL NOT NULL,
    n_events INTEGER NOT NULL,
    n_views INTEGER NOT NULL,
    n_carts INTEGER NOT NULL,
    n_purchases INTEGER NOT NULL,
    n_items INTEGER NOT NULL,
    has_cart INTEGER NOT NULL,
    has_purchase INTEGER NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    visitor_id INTEGER NOT NULL REFERENCES customers(visitor_id),
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    ts INTEGER NOT NULL,
    ts_utc TEXT NOT NULL,
    n_items INTEGER NOT NULL,
    total_value REAL NOT NULL,
    total_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    item_id INTEGER NOT NULL REFERENCES products(item_id),
    unit_price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE cart_items (
    visitor_id INTEGER NOT NULL REFERENCES customers(visitor_id),
    item_id INTEGER NOT NULL REFERENCES products(item_id),
    first_cart_ts INTEGER NOT NULL,
    last_cart_ts INTEGER NOT NULL,
    n_cart_events INTEGER NOT NULL,
    first_purchase_ts INTEGER,
    purchased INTEGER NOT NULL,
    unit_price REAL,
    PRIMARY KEY (visitor_id, item_id)
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    ts INTEGER NOT NULL,
    visitor_id INTEGER NOT NULL REFERENCES customers(visitor_id),
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('view', 'addtocart', 'transaction')),
    item_id INTEGER NOT NULL REFERENCES products(item_id),
    order_id INTEGER REFERENCES orders(order_id)
);

CREATE TABLE daily_stats (
    date TEXT PRIMARY KEY,
    events INTEGER, views INTEGER, carts INTEGER, purchases INTEGER, visitors INTEGER, sessions INTEGER, orders INTEGER,
    revenue REAL, revenue_is_synthetic INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_events_visitor ON events(visitor_id, ts);
CREATE INDEX idx_events_item ON events(item_id);
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_ts ON events(ts);
CREATE INDEX idx_sessions_visitor ON sessions(visitor_id, start_ts);
CREATE INDEX idx_orders_visitor ON orders(visitor_id, ts);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_item ON order_items(item_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_department ON products(department, price);
CREATE INDEX idx_cart_items_item ON cart_items(item_id);
CREATE INDEX idx_features_segment ON customer_features(segment_rule);

CREATE VIEW v_events AS
SELECT e.event_id, datetime(e.ts / 1000, 'unixepoch') AS event_time_utc, e.visitor_id, e.session_id, e.event_type, e.item_id,
       p.name AS product_name, p.department, p.price, e.order_id
FROM events e JOIN products p ON p.item_id = e.item_id;

CREATE VIEW v_order_details AS
SELECT o.order_id, o.ts_utc, o.visitor_id, oi.item_id, p.name AS product_name, p.department, oi.unit_price, oi.quantity,
       o.total_value AS order_total
FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.item_id = oi.item_id;

CREATE VIEW v_product_sales AS
SELECT p.item_id, p.name, p.department, p.price, p.in_stock, p.n_views, p.n_carts, p.n_purchases, p.n_buyers,
       COALESCE(SUM(oi.unit_price * oi.quantity), 0) AS generated_revenue
FROM products p LEFT JOIN order_items oi ON oi.item_id = p.item_id
GROUP BY p.item_id;
