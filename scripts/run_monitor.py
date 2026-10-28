"""Capture local system snapshots for SmartCart monitoring.

No HTTP/API telemetry is collected by this process.
"""

import argparse
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartcart import config  # noqa: E402
from smartcart.monitoring.store import MonitoringStore  # noqa: E402
from smartcart.monitoring.system import snapshot  # noqa: E402


def display(value):
    return f"{value:.1f}%" if value is not None else "unavailable"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=60, help="seconds between snapshots")
    parser.add_argument("--once", action="store_true", help="capture one snapshot and exit")
    args = parser.parse_args()
    store = MonitoringStore(config.MONITORING_DB_PATH)
    try:
        while True:
            current = snapshot()
            store.record_system(current)
            print(f"system_snapshot cpu={display(current['cpu_percent'])} memory={display(current['memory_percent'])} disk={display(current['disk_percent'])}", flush=True)
            if args.once:
                return 0
            time.sleep(max(1.0, args.interval))
    except KeyboardInterrupt:
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
