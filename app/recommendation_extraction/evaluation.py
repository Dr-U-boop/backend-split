from __future__ import annotations

from math import fabs


def evaluate_predictions(gold: list[dict], pred: list[dict]) -> dict:
    if len(gold) != len(pred):
        raise ValueError("gold and pred lengths must match")

    n = len(gold)
    if n == 0:
        return {"count": 0}

    type_ok = 0
    unit_ok = 0
    range_ok = 0
    time_ok = 0
    value_abs_errors: list[float] = []
    warnings_count = 0

    for g, p in zip(gold, pred):
        if g.get("recommendation_type") == p.get("recommendation_type"):
            type_ok += 1
        if g.get("unit") == p.get("unit"):
            unit_ok += 1
        if g.get("value_min") == p.get("value_min") and g.get("value_max") == p.get("value_max"):
            if g.get("value_min") is not None or g.get("value_max") is not None:
                range_ok += 1
        if g.get("time_start") == p.get("time_start") and g.get("time_end") == p.get("time_end"):
            if g.get("time_start") or g.get("time_end"):
                time_ok += 1
        gv = g.get("value")
        pv = p.get("value")
        if isinstance(gv, (int, float)) and isinstance(pv, (int, float)):
            value_abs_errors.append(fabs(float(gv) - float(pv)))
        if p.get("errors_or_warnings"):
            warnings_count += 1

    return {
        "count": n,
        "type_accuracy": type_ok / n,
        "unit_accuracy": unit_ok / n,
        "range_exact_match": range_ok / n,
        "time_interval_exact_match": time_ok / n,
        "value_mae": (sum(value_abs_errors) / len(value_abs_errors)) if value_abs_errors else None,
        "warning_rate": warnings_count / n,
    }

