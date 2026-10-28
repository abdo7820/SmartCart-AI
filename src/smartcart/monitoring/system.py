import shutil
from datetime import datetime, timezone

try:
    import psutil
except ImportError:  # Keep the application importable before optional deps are installed.
    psutil = None

from .. import config


def snapshot():
    disk = shutil.disk_usage(config.ROOT.anchor or str(config.ROOT))
    memory = psutil.virtual_memory() if psutil else None
    return {"recorded_at": datetime.now(timezone.utc).isoformat(), "cpu_percent": float(psutil.cpu_percent(interval=0.05)) if psutil else None, "memory_percent": float(memory.percent) if memory else None, "disk_percent": round((disk.used / disk.total) * 100, 2), "disk_free_bytes": disk.free, "dependency_warning": None if psutil else "psutil is not installed; CPU and memory are unavailable"}


def alerts(values):
    checks = (("cpu_percent", config.MONITOR_CPU_WARN, "CPU usage"), ("memory_percent", config.MONITOR_MEMORY_WARN, "Memory usage"), ("disk_percent", config.MONITOR_DISK_WARN, "Disk usage"))
    return [{"severity": "warning", "metric": key, "title": f"{label} is high", "detail": f"{values[key]:.1f}% exceeds the configured {threshold:.1f}% threshold."} for key, threshold, label in checks if values.get(key) is not None and values[key] >= threshold]
