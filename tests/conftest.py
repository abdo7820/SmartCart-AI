import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DAY = 86_400_000
SYSTEM_START = 1_430_000_000_000


def build_test_db(path):
    con = sqlite3.connect(path)
    schema = (ROOT / "data" / "db" / "schema.sql").read_text()
    con.executescript(schema)
    rng = np.random.default_rng(0)
    n_items, n_vis = 60, 80
    deps = ["Electronics", "Fashion", "Toys & Games"]
    con.execute("INSERT INTO categories VALUES (1, NULL, 1, 0, 'Root', 'Electronics', 1)")
    for i in range(1, n_items + 1):
        price = float(round(10 + i * 2.5, 2))
        con.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (i, 1, 1, f"Item {i}", "Brand", "Thing", deps[i % 3], price, "USD", "standard", 1.0, int(i % 7 == 0), int(i % 2), None, 1, 1,
                     SYSTEM_START, "2015-05-01 00:00:00", SYSTEM_START, 0, 0, 0, 0, 0, 0, None, None, 0.0, 0.0, i))
    rows, sess, orders, order_items = [], [], [], []
    eid = sid = oid = 0
    for v in range(1, n_vis + 1):
        con.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)", (v, SYSTEM_START, "x", SYSTEM_START, "x", 0, 0, 0, 0.0, 1))
        for _ in range(rng.integers(1, 4)):
            sid += 1
            t = SYSTEM_START + int(rng.integers(0, 100)) * DAY + int(rng.integers(0, DAY // 2))
            first = int(rng.integers(1, n_items - 5))
            items = [first, first + 1, first + 2]
            sess.append((sid, v, t, "x", t + 60_000, 60.0, 0, 0, 0, 0, 0, 0, 0))
            for k, it in enumerate(items):
                eid += 1
                rows.append((eid, t + k * 1000, v, sid, "view", it, None))
            if v % 4 == 0:
                eid += 1
                rows.append((eid, t + 5000, v, sid, "addtocart", items[0], None))
                eid += 1
                oid += 1
                orders.append((oid, v, sid, t + 9000, "x", 1, 10.0, 1))
                order_items.append((oid, oid, items[0], 10.0, 1, 1))
                rows.append((eid, t + 9000, v, sid, "transaction", items[0], oid))
    con.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", sess)
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", orders)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", order_items)
    con.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO db_info VALUES (?,?)", [("data_origin", "test"), ("enrichment_origin", "synthetic")])
    con.execute("UPDATE customers SET n_orders = 1 WHERE visitor_id IN (SELECT visitor_id FROM orders)")
    con.execute("INSERT INTO customer_features(visitor_id, segment_rule) SELECT visitor_id, 'browser' FROM customers")
    con.commit()
    con.close()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_serving_tables.py"), "--db", str(path)], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_ranker_state.py"), "--db", str(path)], check=True)


class Session:
    """A browser-like client: own cookie jar, sends the CSRF token it received at login."""

    def __init__(self):
        from fastapi.testclient import TestClient
        from smartcart.app import app
        self.c = TestClient(app)
        self.csrf = None

    def _h(self, extra=None):
        h = dict(extra or {})
        if self.csrf:
            h["X-CSRF-Token"] = self.csrf
        return h

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None, headers=None, **kw):
        return self.c.post(url, json=json, headers=self._h(headers), **kw)

    def put(self, url, json=None, headers=None, **kw):
        return self.c.put(url, json=json, headers=self._h(headers), **kw)

    def delete(self, url, headers=None, **kw):
        return self.c.delete(url, headers=self._h(headers), **kw)

    def login(self, email, password):
        r = self.c.post("/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            self.csrf = r.json()["csrf_token"]
        return r

    def register(self, email, password, name="Test Person", **extra):
        r = self.c.post("/auth/register", json={"email": email, "password": password, "full_name": name, **extra})
        if r.status_code == 201:
            self.csrf = r.json()["csrf_token"]
        return r


PASSWORD = "Sup3r-secret-pw"


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    work = tmp_path_factory.mktemp("db")
    db_path = work / "test.db"
    build_test_db(db_path)
    from smartcart import config
    config.DATABASE_PATH = db_path
    config.APP_DATABASE_PATH = work / "app.db"
    config.RATE_LIMIT_ENABLED = False
    pg_url = os.environ.get("TEST_PG_URL")
    if pg_url:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "sqlite_to_postgres.py"), "--sqlite", str(db_path), "--url", pg_url], check=True)
        config.DATABASE_URL = pg_url
        config.APP_DATABASE_URL = pg_url
    from fastapi.testclient import TestClient
    from smartcart.app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def anon(client):
    return Session()


@pytest.fixture(scope="session")
def admin_credentials(client):
    from smartcart import accounts
    from smartcart.state import state
    email = "root@example.com"
    accounts.provision_admin(state["adb"], email, "Root Admin", PASSWORD)
    return email, PASSWORD


@pytest.fixture()
def admin(client, admin_credentials):
    s = Session()
    assert s.login(*admin_credentials).status_code == 200
    return s


@pytest.fixture()
def make_user(client):
    import itertools
    counter = itertools.count()

    def make(**extra):
        s = Session()
        email = f"user{next(counter)}_{os.urandom(3).hex()}@example.com"
        r = s.register(email, PASSWORD, **extra)
        assert r.status_code == 201, r.text
        s.email = email
        s.account = r.json()["account"]
        return s

    return make
