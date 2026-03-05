from __future__ import annotations

from app.recommendation_extraction.schemas import ParseCandidate


def _in_range(value: float | None, min_v: float, max_v: float) -> bool:
    if value is None:
        return False
    return min_v <= value <= max_v


def validate_candidate(candidate: ParseCandidate) -> list[str]:
    warnings: list[str] = []
    t = candidate.recommendation_type

    if candidate.time_start and candidate.time_end and candidate.time_start == candidate.time_end:
        warnings.append("time interval has same start/end")

    if candidate.value_min is not None and candidate.value_max is not None:
        if candidate.value_min >= candidate.value_max:
            warnings.append("value_min must be lower than value_max")

    if t == "basal_rate" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 0.01, 15.0):
        warnings.append("basal_rate outside expected range")
    if t == "carb_ratio" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 2.0, 40.0):
        warnings.append("carb_ratio outside expected range")
    if t == "correction_factor" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 0.5, 20.0):
        warnings.append("correction_factor outside expected range")
    if t == "target_glucose" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 3.0, 15.0):
        warnings.append("target_glucose outside expected range")
    if t == "target_range":
        if candidate.value_min is None or candidate.value_max is None:
            warnings.append("target_range missing bounds")
        else:
            if not (2.5 <= candidate.value_min <= 20.0 and 2.5 <= candidate.value_max <= 20.0):
                warnings.append("target_range outside expected values")
    if t == "prebolus_time" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 0.0, 120.0):
        warnings.append("prebolus_time outside expected range")
    if t == "temp_basal_percent" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, -100.0, 300.0):
        warnings.append("temp_basal_percent outside expected range")
    if t == "active_insulin_time" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 1.0, 12.0):
        warnings.append("active_insulin_time outside expected range")
    if t == "correction_interval" and not _in_range(candidate.value if isinstance(candidate.value, float) else None, 0.25, 12.0):
        warnings.append("correction_interval outside expected range")
    if t in {"low_glucose_alert_threshold", "high_glucose_alert_threshold"} and not _in_range(
        candidate.value if isinstance(candidate.value, float) else None, 2.0, 25.0
    ):
        warnings.append("alert threshold outside expected range")
    if t == "dual_bolus_split":
        if not isinstance(candidate.value, str):
            warnings.append("dual_bolus_split should keep split string")
        else:
            try:
                raw_split = candidate.value.split("%/")
                first = float(raw_split[0])
                second = float(raw_split[1].split("%")[0])
                if abs((first + second) - 100.0) > 5.0:
                    warnings.append("dual bolus split does not sum to ~100%")
            except Exception:
                warnings.append("dual_bolus_split parse issue")

    return warnings

