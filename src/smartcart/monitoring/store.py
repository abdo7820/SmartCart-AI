import json
import sqlite3
import threading
import time
from pathlib import Path


class MonitoringStore:
    """Small separate SQLite store for operational ML/system observations."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS model_predictions (
          id INTEGER PRIMARY KEY, recorded_at INTEGER NOT NULL, model_name TEXT NOT NULL,
          model_version TEXT, duration_ms REAL NOT NULL, success INTEGER NOT NULL,
          summary_json TEXT NOT NULL, error_code TEXT
        );
        CREATE TABLE IF NOT EXISTS system_snapshots (
          id INTEGER PRIMARY KEY, recorded_at INTEGER NOT NULL, cpu_percent REAL,
          memory_percent REAL, disk_percent REAL, payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drift_reports (
          id INTEGER PRIMARY KEY, recorded_at INTEGER NOT NULL, dataset_name TEXT NOT NULL,
          status TEXT NOT NULL, payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_model_predictions_time ON model_predictions(recorded_at);
        CREATE INDEX IF NOT EXISTS ix_system_snapshots_time ON system_snapshots(recorded_at);
        CREATE INDEX IF NOT EXISTS ix_drift_reports_time ON drift_reports(recorded_at);
        """)
        self.con.commit()

    def _now(self):
        return int(time.time() * 1000)

    def record_prediction(self, model_name, model_version, duration_ms, success, summary=None, error_code=None):
        with self.lock:
            self.con.execute("INSERT INTO model_predictions VALUES (NULL,?,?,?,?,?,?,?)", (self._now(), model_name, str(model_version or "unknown"), float(duration_ms), int(success), json.dumps(summary or {}, default=str), error_code))
            self.con.commit()

    def record_system(self, snapshot):
        with self.lock:
            self.con.execute("INSERT INTO system_snapshots VALUES (NULL,?,?,?,?,?)", (self._now(), snapshot.get("cpu_percent"), snapshot.get("memory_percent"), snapshot.get("disk_percent"), json.dumps(snapshot, default=str)))
            self.con.commit()

    def record_drift(self, dataset_name, report):
        with self.lock:
            self.con.execute("INSERT INTO drift_reports VALUES (NULL,?,?,?,?)", (self._now(), dataset_name, report.get("status", "unavailable"), json.dumps(report, default=str)))
            self.con.commit()

    def model_summary(self, since_ms):
        rows = self.con.execute("SELECT model_name, model_version, COUNT(*) total, SUM(success) successes, AVG(duration_ms) avg_duration_ms, MAX(recorded_at) last_recorded FROM model_predictions WHERE recorded_at >= ? GROUP BY model_name, model_version", (since_ms,)).fetchall()
        out = []
        for row in rows:
            failures = int(row["total"] - row["successes"])
            dist = self.con.execute("SELECT summary_json FROM model_predictions WHERE recorded_at >= ? AND model_name = ? AND model_version = ? AND success = 1", (since_ms, row["model_name"], row["model_version"])).fetchall()
            merged = {}
            for item in dist:
                payload = json.loads(item[0] or "{}")
                for key, value in payload.items():
                    if isinstance(value, dict):
                        target = merged.setdefault(key, {})
                        for subkey, subvalue in value.items():
                            if isinstance(subvalue, (int, float)):
                                target[subkey] = target.get(subkey, 0) + subvalue
                            else:
                                target[subkey] = subvalue
                    elif key not in merged:
                        merged[key] = value
            out.append({"model_name": row["model_name"], "model_version": row["model_version"], "predictions": int(row["total"]), "total": int(row["total"]), "successes": int(row["successes"] or 0), "failures": failures, "failure_rate": round(failures / row["total"], 4), "avg_duration_ms": round(float(row["avg_duration_ms"]), 2), "last_recorded": row["last_recorded"], "distribution": merged})
        return out

    def latest_drift(self):
        row = self.con.execute("SELECT payload_json FROM drift_reports ORDER BY recorded_at DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.con.close()
