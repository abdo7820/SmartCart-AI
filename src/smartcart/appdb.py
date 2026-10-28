import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import config

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def new_id():
    return uuid.uuid4().hex


def now_ms():
    return int(time.time() * 1000)


class AppDB:
    def __init__(self, path=None, url=None):
        self.lock = threading.RLock()
        self.is_pg = bool(url)
        if self.is_pg:
            import psycopg
            from psycopg.rows import dict_row

            self.raw = psycopg.connect(url, autocommit=True, row_factory=dict_row)
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.raw = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
            self.raw.row_factory = sqlite3.Row
            self.raw.execute("PRAGMA foreign_keys = ON")
            self.raw.execute("PRAGMA journal_mode = WAL")
        self._tx_depth = 0

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.is_pg else sql

    def execute(self, sql, params=()):
        with self.lock:
            return self.raw.execute(self._sql(sql), list(params))

    def query(self, sql, params=()):
        with self.lock:
            return [dict(r) for r in self.raw.execute(self._sql(sql), list(params)).fetchall()]

    def one(self, sql, params=()):
        with self.lock:
            r = self.raw.execute(self._sql(sql), list(params)).fetchone()
            return dict(r) if r is not None else None

    def scalar(self, sql, params=()):
        r = self.one(sql, params)
        return None if r is None else next(iter(r.values()))

    @contextmanager
    def transaction(self):
        with self.lock:
            if self._tx_depth > 0:
                self._tx_depth += 1
                try:
                    yield self
                finally:
                    self._tx_depth -= 1
                return
            self.raw.execute("BEGIN")
            self._tx_depth = 1
            try:
                yield self
                self.raw.execute("COMMIT")
            except BaseException:
                self.raw.execute("ROLLBACK")
                raise
            finally:
                self._tx_depth = 0

    def close(self):
        self.raw.close()


def open_app_db():
    if config.APP_DATABASE_URL:
        return AppDB(url=config.APP_DATABASE_URL)
    return AppDB(path=config.APP_DATABASE_PATH)


def migrate(adb):
    adb.execute("CREATE TABLE IF NOT EXISTS app_migrations (name TEXT PRIMARY KEY, applied_at BIGINT NOT NULL)")
    done = {r["name"] for r in adb.query("SELECT name FROM app_migrations")}
    applied = []
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.name in done:
            continue
        statements = [s.strip() for s in re.split(r";\s*(?:\n|$)", f.read_text()) if s.strip()]
        with adb.transaction():
            for st in statements:
                adb.execute(st)
            adb.execute("INSERT INTO app_migrations (name, applied_at) VALUES (?, ?)", (f.name, now_ms()))
        applied.append(f.name)
    return applied
