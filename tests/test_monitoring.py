import pandas as pd

from smartcart.monitoring.data_quality import compare_frames
from smartcart.monitoring.store import MonitoringStore
from smartcart.monitoring import system


def test_empty_comparison_is_unavailable():
    result = compare_frames(pd.DataFrame(), pd.DataFrame())
    assert result["status"] == "unavailable"
    assert "reason" in result


def test_comparison_reports_schema_and_drift():
    reference = pd.DataFrame({"age": [1, 2, 3, 4, 5], "keep": [1, 1, 1, 1, 1]})
    current = pd.DataFrame({"age": [100, 101, 102, 103, 104], "new": [1, 2, 3, 4, 5]})
    result = compare_frames(reference, current, drift_threshold=0.01)
    assert result["status"] == "warning"
    assert result["missing_columns"] == ["keep"]
    assert result["unexpected_columns"] == ["new"]
    assert "age" in result["drifted_columns"]


def test_store_records_model_failures_and_distribution(tmp_path):
    store = MonitoringStore(tmp_path / "monitoring.db")
    try:
        store.record_prediction("churn", "bundle", 12.5, True, {"tier_counts": {"High": 2}})
        store.record_prediction("churn", "bundle", 20.0, False, error_code="ValueError")
        summary = store.model_summary(0)
        assert summary[0]["predictions"] == 2
        assert summary[0]["failures"] == 1
        assert summary[0]["distribution"]["tier_counts"]["High"] == 2
    finally:
        store.close()


def test_system_snapshot_collects_resources_or_reports_dependency(monkeypatch):
    current = system.snapshot()
    assert current["disk_percent"] is not None
    assert current["cpu_percent"] is not None or current["dependency_warning"]
    assert current["memory_percent"] is not None or current["dependency_warning"]

    monkeypatch.setattr(system, "psutil", None)
    unavailable = system.snapshot()
    assert unavailable["cpu_percent"] is None
    assert unavailable["memory_percent"] is None
    assert unavailable["dependency_warning"]
    assert system.alerts(unavailable) == [] or all(a["metric"] == "disk_percent" for a in system.alerts(unavailable))

