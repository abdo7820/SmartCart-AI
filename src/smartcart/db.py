import sqlite3

import pandas as pd

from . import config


class PgRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    names = [c.name for c in cursor.description] if cursor.description else []

    def make(values):
        return PgRow(zip(names, values))

    return make


class PgConn:
    is_pg = True

    def __init__(self, url):
        import psycopg

        self.raw = psycopg.connect(url, autocommit=True, row_factory=_row_factory)

    def execute(self, sql, params=()):
        return self.raw.execute(sql.replace("?", "%s"), list(params))

    def frame(self, sql, params=()):
        import psycopg

        with self.raw.cursor(row_factory=psycopg.rows.tuple_row) as cur:
            cur.execute(sql.replace("?", "%s"), list(params))
            cols = [c.name for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)

    def tables(self):
        rows = self.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()").fetchall()
        return {r["table_name"] for r in rows}

    def close(self):
        self.raw.close()


class SqliteConn:
    is_pg = False

    def __init__(self, path):
        self.raw = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        self.raw.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        return self.raw.execute(sql, list(params))

    def frame(self, sql, params=()):
        cur = self.raw.execute(sql, list(params))
        cols = [c[0] for c in cur.description]
        return pd.DataFrame([tuple(r) for r in cur.fetchall()], columns=cols)

    def tables(self):
        return {r[0] for r in self.raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}

    def close(self):
        self.raw.close()


def connect():
    if config.DATABASE_URL:
        return PgConn(config.DATABASE_URL)
    return SqliteConn(config.DATABASE_PATH)


def query(con, sql, params=()):
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def frame(con, sql, params=()):
    return con.frame(sql, params)


def one(con, sql, params=()):
    r = con.execute(sql, params).fetchone()
    return dict(r) if r is not None else None


def db_info(con):
    return {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM db_info").fetchall()}


def as_of_ms(con):
    r = con.execute("SELECT MAX(ts) AS m FROM events").fetchone()
    return int(r["m"]) + 1
