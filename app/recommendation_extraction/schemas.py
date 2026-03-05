from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


RecommendationType = Literal[
    "basal_rate",
    "carb_ratio",
    "correction_factor",
    "target_glucose",
    "target_range",
    "prebolus_time",
    "temp_basal_percent",
    "active_insulin_time",
    "dual_bolus_split",
    "correction_interval",
    "low_glucose_alert_threshold",
    "high_glucose_alert_threshold",
    "unknown",
]


@dataclass(slots=True)
class ParseConfig:
    enable_ml_fallback: bool = True
    fuzzy_threshold: float = 62.0
    min_rule_confidence: float = 0.55
    high_confidence_threshold: float = 0.82


@dataclass(slots=True)
class MatchResult:
    recommendation_type: RecommendationType
    alias: str
    score: float
    method: str


@dataclass(slots=True)
class ParseCandidate:
    recommendation_type: RecommendationType = "unknown"
    text: str = ""
    normalized_text: str = ""
    value: float | str | None = None
    value_min: float | None = None
    value_max: float | None = None
    unit: str | None = None
    time_start: str | None = None
    time_end: str | None = None
    condition: str | None = None
    confidence: float = 0.0
    parse_method: str = "rule_regex"
    errors_or_warnings: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 4)
        return payload

