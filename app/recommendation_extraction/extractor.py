from __future__ import annotations

import re
from dataclasses import replace

from app.recommendation_extraction.dictionaries import CONDITION_ALIASES
from app.recommendation_extraction.fuzzy_match import match_recommendation_types
from app.recommendation_extraction.ml import MLTypeClassifier
from app.recommendation_extraction.normalization import normalize_text
from app.recommendation_extraction.patterns import (
    RE_ACTIVE_INSULIN,
    RE_ANY_TIME_DASH,
    RE_BASAL_PERCENT,
    RE_BASAL_RATE,
    RE_BASAL_RATE_SOFT,
    RE_CARB_RATIO,
    RE_CARB_RATIO_COLON,
    RE_CORRECTION_FACTOR,
    RE_CORRECTION_FACTOR_COLON,
    RE_CORRECTION_FACTOR_EQ,
    RE_CORRECTION_INTERVAL,
    RE_DUAL_BOLUS,
    RE_HIGH_ALERT,
    RE_LOW_ALERT,
    RE_PREBOLUS,
    RE_TARGET_RANGE,
    RE_TARGET_SINGLE,
    RE_TEMP_BASAL,
    RE_TIME_INTERVAL,
    parse_float,
    parse_time_token,
)
from app.recommendation_extraction.schemas import ParseCandidate, ParseConfig
from app.recommendation_extraction.validation import validate_candidate


CLAUSE_SPLIT_RE = re.compile(
    r"(?:[;\n]+|,\s*(?=(?:баз|угл|ук\b|коэф|коэфф|фактор|чувств|цел|таргет|предбол|врем|актив|не\s+корр|порог|\d{1,3}\s*%)))"
)


def _extract_condition(normalized_text: str) -> str | None:
    for canonical, aliases in CONDITION_ALIASES.items():
        for alias in aliases:
            if alias in normalized_text:
                return canonical
    return None


def _extract_time_bounds(normalized_text: str) -> tuple[str | None, str | None]:
    match = RE_TIME_INTERVAL.search(normalized_text) or RE_ANY_TIME_DASH.search(normalized_text)
    if not match:
        return None, None
    return parse_time_token(match.group("start")), parse_time_token(match.group("end"))


def _base_candidate(text: str, normalized_text: str) -> ParseCandidate:
    time_start, time_end = _extract_time_bounds(normalized_text)
    return ParseCandidate(
        text=text,
        normalized_text=normalized_text,
        time_start=time_start,
        time_end=time_end,
        condition=_extract_condition(normalized_text),
    )


def _iter_clauses(normalized_text: str) -> list[str]:
    clauses = [c.strip(" ,.") for c in CLAUSE_SPLIT_RE.split(normalized_text) if c.strip(" ,.")]
    return clauses or [normalized_text]


def _append_candidate(out: list[ParseCandidate], candidate: ParseCandidate) -> None:
    key = (
        candidate.recommendation_type,
        candidate.value,
        candidate.value_min,
        candidate.value_max,
        candidate.unit,
        candidate.time_start,
        candidate.time_end,
        candidate.condition,
    )
    for existing in out:
        e_key = (
            existing.recommendation_type,
            existing.value,
            existing.value_min,
            existing.value_max,
            existing.unit,
            existing.time_start,
            existing.time_end,
            existing.condition,
        )
        if key == e_key:
            return
    out.append(candidate)


def _rule_extract(text: str, normalized_text: str) -> list[ParseCandidate]:
    out: list[ParseCandidate] = []
    for clause in _iter_clauses(normalized_text):
        for match in RE_BASAL_RATE.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "basal_rate"
            c.value = parse_float(match.group("value"))
            c.unit = "Ед/ч"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_BASAL_RATE")
            _append_candidate(out, c)

        if not RE_BASAL_RATE.search(clause):
            for match in RE_BASAL_RATE_SOFT.finditer(clause):
                c = _base_candidate(text, clause)
                c.recommendation_type = "basal_rate"
                c.value = parse_float(match.group("value"))
                c.unit = "Ед/ч"
                c.parse_method = "rule_regex"
                c.trace.append("matched RE_BASAL_RATE_SOFT")
                _append_candidate(out, c)

        for match in RE_CARB_RATIO.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "carb_ratio"
            c.value = parse_float(match.group("grams"))
            c.unit = "г/Ед"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_CARB_RATIO")
            _append_candidate(out, c)
        for match in RE_CARB_RATIO_COLON.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "carb_ratio"
            c.value = parse_float(match.group("grams"))
            c.unit = "г/Ед"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_CARB_RATIO_COLON")
            _append_candidate(out, c)

        for match in RE_CORRECTION_FACTOR.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "correction_factor"
            c.value = parse_float(match.group("mmol"))
            c.unit = "ммоль/л/Ед"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_CORRECTION_FACTOR")
            _append_candidate(out, c)
        for pattern_name, pattern in (
            ("RE_CORRECTION_FACTOR_EQ", RE_CORRECTION_FACTOR_EQ),
            ("RE_CORRECTION_FACTOR_COLON", RE_CORRECTION_FACTOR_COLON),
        ):
            for match in pattern.finditer(clause):
                c = _base_candidate(text, clause)
                c.recommendation_type = "correction_factor"
                c.value = parse_float(match.group("mmol"))
                c.unit = "ммоль/л/Ед"
                c.parse_method = "rule_regex"
                c.trace.append(f"matched {pattern_name}")
                _append_candidate(out, c)

        if "диапазон" in clause or "диап" in clause:
            for match in RE_TARGET_RANGE.finditer(clause):
                c = _base_candidate(text, clause)
                c.recommendation_type = "target_range"
                c.value_min = parse_float(match.group("min"))
                c.value_max = parse_float(match.group("max"))
                c.unit = "ммоль/л"
                c.parse_method = "rule_regex"
                c.trace.append("matched RE_TARGET_RANGE")
                _append_candidate(out, c)
        elif "цел" in clause or "таргет" in clause:
            for match in RE_TARGET_SINGLE.finditer(clause):
                c = _base_candidate(text, clause)
                c.recommendation_type = "target_glucose"
                c.value = parse_float(match.group("value"))
                c.unit = "ммоль/л"
                c.parse_method = "rule_regex"
                c.trace.append("matched RE_TARGET_SINGLE")
                _append_candidate(out, c)
                break

        for match in RE_PREBOLUS.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "prebolus_time"
            c.value = parse_float(match.group("value"))
            c.unit = "мин" if match.group("unit") == "мин" else "ч"
            if c.unit == "ч" and isinstance(c.value, float):
                c.value = c.value * 60.0
                c.unit = "мин"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_PREBOLUS")
            _append_candidate(out, c)

        for pattern_name, pattern in (("RE_TEMP_BASAL", RE_TEMP_BASAL), ("RE_BASAL_PERCENT", RE_BASAL_PERCENT)):
            for match in pattern.finditer(clause):
                c = _base_candidate(text, clause)
                c.recommendation_type = "temp_basal_percent"
                c.value = parse_float(match.group("value"))
                c.unit = "%"
                c.parse_method = "rule_regex"
                c.trace.append(f"matched {pattern_name}")
                _append_candidate(out, c)

        for match in RE_ACTIVE_INSULIN.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "active_insulin_time"
            c.value = parse_float(match.group("value"))
            c.unit = "ч" if match.group("unit") == "ч" else "мин"
            if c.unit == "мин" and isinstance(c.value, float):
                c.value = round(c.value / 60.0, 3)
                c.unit = "ч"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_ACTIVE_INSULIN")
            _append_candidate(out, c)

        for match in RE_DUAL_BOLUS.finditer(clause):
            c = _base_candidate(text, clause)
            first = parse_float(match.group("first"))
            second = parse_float(match.group("second"))
            duration = parse_float(match.group("duration"))
            unit = match.group("unit")
            c.recommendation_type = "dual_bolus_split"
            c.value = f"{first}%/{second}%"
            c.value_min = duration
            c.unit = "%/% + ч"
            if unit == "мин" and duration is not None:
                c.value_min = round(duration / 60.0, 3)
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_DUAL_BOLUS")
            _append_candidate(out, c)

        for match in RE_CORRECTION_INTERVAL.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "correction_interval"
            c.value = parse_float(match.group("value"))
            c.unit = "ч" if match.group("unit") == "ч" else "мин"
            if c.unit == "мин" and isinstance(c.value, float):
                c.value = round(c.value / 60.0, 3)
                c.unit = "ч"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_CORRECTION_INTERVAL")
            _append_candidate(out, c)

        for match in RE_LOW_ALERT.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "low_glucose_alert_threshold"
            c.value = parse_float(match.group("value"))
            c.unit = "ммоль/л"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_LOW_ALERT")
            _append_candidate(out, c)

        for match in RE_HIGH_ALERT.finditer(clause):
            c = _base_candidate(text, clause)
            c.recommendation_type = "high_glucose_alert_threshold"
            c.value = parse_float(match.group("value"))
            c.unit = "ммоль/л"
            c.parse_method = "rule_regex"
            c.trace.append("matched RE_HIGH_ALERT")
            _append_candidate(out, c)

    return out


def _compute_confidence(candidate: ParseCandidate, fuzzy_score: float | None, used_ml: bool) -> float:
    score = 0.15
    if candidate.recommendation_type != "unknown":
        score += 0.2
    if candidate.value is not None or (candidate.value_min is not None and candidate.value_max is not None):
        score += 0.26
    if candidate.unit:
        score += 0.18
    if candidate.time_start or candidate.time_end:
        score += 0.08
    if candidate.condition:
        score += 0.05
    if fuzzy_score is not None:
        score += min(fuzzy_score / 100.0, 1.0) * 0.15
    if used_ml:
        score -= 0.07
    score -= min(len(candidate.errors_or_warnings) * 0.05, 0.2)
    return max(0.0, min(1.0, score))


class RecommendationExtractor:
    def __init__(self, config: ParseConfig | None = None, ml_classifier: MLTypeClassifier | None = None):
        self.config = config or ParseConfig()
        self.ml_classifier = ml_classifier

    def parse_recommendations(self, text: str) -> list[dict]:
        normalized_text, norm_warnings = normalize_text(text)
        candidates = _rule_extract(text, normalized_text)

        if candidates:
            for idx, candidate in enumerate(candidates):
                c = replace(candidate)
                fuzzy_hits = match_recommendation_types(c.normalized_text, threshold=self.config.fuzzy_threshold)
                best_fuzzy = fuzzy_hits[0] if fuzzy_hits else None
                if best_fuzzy is not None and c.recommendation_type == best_fuzzy.recommendation_type:
                    c.parse_method = "hybrid"
                    c.trace.append(f"fuzzy aligned alias={best_fuzzy.alias} score={best_fuzzy.score}")
                c.errors_or_warnings.extend(norm_warnings)
                c.errors_or_warnings.extend(validate_candidate(c))
                c.confidence = _compute_confidence(
                    c,
                    fuzzy_score=best_fuzzy.score if best_fuzzy else None,
                    used_ml=False,
                )
                candidates[idx] = c
            return [c.to_dict() for c in candidates]

        # No rule candidates: fallback single record
        best_fuzzy = match_recommendation_types(normalized_text, threshold=self.config.fuzzy_threshold)
        best = best_fuzzy[0] if best_fuzzy else None
        fallback = _base_candidate(text, normalized_text)
        if best is not None:
            fallback.recommendation_type = best.recommendation_type
            fallback.parse_method = "rule_fuzzy"
            fallback.trace.append(f"fuzzy alias={best.alias} score={best.score}")
        elif self.config.enable_ml_fallback and self.ml_classifier is not None and self.ml_classifier.available():
            pred_type, pred_score = self.ml_classifier.predict(normalized_text)
            if pred_type != "unknown":
                fallback.recommendation_type = pred_type
                fallback.parse_method = "ml_classifier"
                fallback.trace.append(f"ml_type={pred_type} score={pred_score:.3f}")
                fallback.confidence = max(0.3, min(0.8, pred_score))
        fallback.errors_or_warnings.extend(norm_warnings)
        fallback.errors_or_warnings.append("no robust value pattern found")
        if fallback.confidence == 0.0:
            fallback.confidence = _compute_confidence(
                fallback,
                fuzzy_score=best.score if best else None,
                used_ml=fallback.parse_method == "ml_classifier",
            )
        return [fallback.to_dict()]

    def parse_recommendation(self, text: str) -> dict:
        items = self.parse_recommendations(text)
        return sorted(items, key=lambda x: x.get("confidence", 0.0), reverse=True)[0]

    def parse_batch(self, texts: list[str]) -> list[dict]:
        return [self.parse_recommendation(text) for text in texts]

    def parse_batch_multi(self, texts: list[str]) -> list[list[dict]]:
        return [self.parse_recommendations(text) for text in texts]


_DEFAULT_EXTRACTOR = RecommendationExtractor()


def parse_recommendation(text: str) -> dict:
    return _DEFAULT_EXTRACTOR.parse_recommendation(text)


def parse_recommendations(text: str) -> list[dict]:
    return _DEFAULT_EXTRACTOR.parse_recommendations(text)


def parse_batch(texts: list[str]) -> list[dict]:
    return _DEFAULT_EXTRACTOR.parse_batch(texts)


def parse_batch_multi(texts: list[str]) -> list[list[dict]]:
    return _DEFAULT_EXTRACTOR.parse_batch_multi(texts)

