import math

import pandas as pd


def _psi(reference, current, bins=10):
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    cur = pd.to_numeric(current, errors="coerce").dropna()
    if ref.empty or cur.empty:
        return None
    edges = sorted(set(ref.quantile([i / bins for i in range(bins + 1)]).tolist()))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -math.inf, math.inf
    r = pd.cut(ref, bins=edges, include_lowest=True).value_counts(normalize=True, sort=False).to_numpy()
    c = pd.cut(cur, bins=edges, include_lowest=True).value_counts(normalize=True, sort=False).to_numpy()
    r = r.clip(1e-6)
    c = c.clip(1e-6)
    return float(sum((now - old) * math.log(now / old) for old, now in zip(r, c)))


def compare_frames(reference, current, drift_threshold=0.20):
    reference = reference if isinstance(reference, pd.DataFrame) else pd.DataFrame(reference)
    current = current if isinstance(current, pd.DataFrame) else pd.DataFrame(current)
    ref_cols, cur_cols = set(reference.columns), set(current.columns)
    missing_columns = sorted(ref_cols - cur_cols)
    unexpected_columns = sorted(cur_cols - ref_cols)
    missing_values = {str(c): float(current[c].isna().mean()) for c in current.columns if current[c].isna().any()}
    drift = {}
    for col in sorted(ref_cols & cur_cols):
        if pd.api.types.is_numeric_dtype(reference[col]) and pd.api.types.is_numeric_dtype(current[col]):
            score = _psi(reference[col], current[col])
            if score is not None:
                drift[col] = {"metric": "psi", "value": round(score, 6), "drifted": score >= drift_threshold}
    drifted = sorted(col for col, item in drift.items() if item["drifted"])
    status = "unavailable" if reference.empty or current.empty else ("warning" if missing_columns or drifted else "ok")
    return {"status": status, "reference_rows": int(len(reference)), "current_rows": int(len(current)),
            "reference_columns": sorted(ref_cols), "current_columns": sorted(cur_cols), "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns, "missing_values": missing_values, "drift": drift,
            "drifted_columns": drifted, "drift_threshold": drift_threshold,
            "reason": "reference or current dataset is empty" if status == "unavailable" else None}
