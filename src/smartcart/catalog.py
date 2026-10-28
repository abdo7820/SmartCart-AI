from . import db

CARD_COLS = "p.item_id, p.name, p.brand, p.department, p.product_type, p.price, p.currency, p.in_stock, p.is_deal"
STOCK_SQL = {"any": "", "in_stock": " AND p.in_stock = 1", "not_out": " AND COALESCE(p.in_stock, 1) = 1"}


def departments(con):
    return [r["department"] for r in db.query(con, "SELECT department, COUNT(*) AS n FROM products GROUP BY department ORDER BY n DESC")]


def product_types(con):
    return [r["product_type"] for r in db.query(con, "SELECT DISTINCT product_type FROM products")]


def get_products(con, ids):
    ids = [int(i) for i in ids]
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = db.query(con, f"SELECT {CARD_COLS} FROM products p WHERE p.item_id IN ({marks})", ids)
    return {r["item_id"]: r for r in rows}


def get_product(con, item_id):
    return get_products(con, [item_id]).get(int(item_id))


def search(con, tokens=(), department=None, product_type=None, min_price=None, max_price=None, stock="any", limit=8, sort="popular"):
    where, params = ["1 = 1"], []
    for t in tokens:
        where.append("(LOWER(p.name) LIKE ? OR LOWER(p.product_type) LIKE ? OR LOWER(p.department) LIKE ?)")
        params += [f"%{t}%"] * 3
    if department:
        where.append("p.department = ?")
        params.append(department)
    if product_type:
        where.append("p.product_type = ?")
        params.append(product_type)
    if min_price is not None:
        where.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("p.price <= ?")
        params.append(max_price)
    order = {"popular": "p.popularity_rank ASC", "price_asc": "p.price ASC, p.item_id", "price_desc": "p.price DESC, p.item_id"}[sort]
    sql = f"SELECT {CARD_COLS} FROM products p WHERE {' AND '.join(where)}{STOCK_SQL[stock]} ORDER BY {order} LIMIT ?"
    return db.query(con, sql, [*params, limit])


def popular(con, k=10, departments=None, stock="not_out", min_price=None, max_price=None):
    where, params = ["1 = 1"], []
    if departments:
        where.append("p.department IN (" + ",".join("?" * len(departments)) + ")")
        params += list(departments)
    if min_price is not None:
        where.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("p.price <= ?")
        params.append(max_price)
    sql = (f"SELECT {CARD_COLS} FROM item_popularity ip JOIN products p ON p.item_id = ip.item_id WHERE {' AND '.join(where)}{STOCK_SQL[stock]} "
           "ORDER BY ip.score DESC, ip.item_id LIMIT ?")
    return db.query(con, sql, [*params, k])


def trending(con, k=10, stock="not_out"):
    sql = (f"SELECT {CARD_COLS} FROM rk_item_features f JOIN products p ON p.item_id = f.item_id WHERE f.i_pop_7d >= 20{STOCK_SQL[stock]} "
           "ORDER BY f.i_trend DESC, f.item_id LIMIT ?")
    return db.query(con, sql, [k])


def similar(con, item_id, k=8, stock="not_out", exclude=()):
    ex = [int(x) for x in exclude] + [int(item_id)]
    marks = ",".join("?" * len(ex))
    sql = (f"SELECT {CARD_COLS} FROM item_neighbors n JOIN products p ON p.item_id = n.neighbor_id WHERE n.item_id = ? AND p.item_id NOT IN ({marks}){STOCK_SQL[stock]} "
           "ORDER BY n.score DESC, p.item_id LIMIT ?")
    return db.query(con, sql, [int(item_id), *ex, k])
