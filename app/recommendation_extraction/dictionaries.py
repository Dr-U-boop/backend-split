from __future__ import annotations

from app.recommendation_extraction.schemas import RecommendationType


RECOMMENDATION_ALIASES: dict[RecommendationType, list[str]] = {
    "basal_rate": [
        "базальная скорость",
        "базал",
        "баз скорость",
        "базал скорость",
        "basal",
        "базальная",
    ],
    "carb_ratio": [
        "углеводный коэффициент",
        "угл коэффициент",
        "угл коэф",
        "ук",
        "carb ratio",
    ],
    "correction_factor": [
        "фактор чувствительности",
        "фактор чуствит",
        "коэффициент чувствительности",
        "чувствительность",
        "isf",
    ],
    "target_glucose": [
        "целевая глюкоза",
        "целевая",
        "таргет",
        "target glucose",
    ],
    "target_range": [
        "целевой диапазон",
        "целев диап",
        "диапазон глюкозы",
        "target range",
    ],
    "prebolus_time": [
        "предболюс",
        "преболюс",
        "prebolus",
        "до еды",
    ],
    "temp_basal_percent": [
        "временная базальная",
        "врем базал",
        "temp basal",
        "временный базал",
    ],
    "active_insulin_time": [
        "активный инсулин",
        "аит",
        "длительность инсулина",
        "dia",
    ],
    "dual_bolus_split": [
        "двойной болюс",
        "dual bolus",
        "квадро",
        "сразу и",
    ],
    "correction_interval": [
        "не корригировать раньше",
        "интервал коррекции",
        "коррекция не раньше",
        "между коррекциями",
    ],
    "low_glucose_alert_threshold": [
        "порог низкой глюкозы",
        "низкий порог",
        "гипо порог",
        "low alert",
    ],
    "high_glucose_alert_threshold": [
        "порог высокой глюкозы",
        "высокий порог",
        "гипер порог",
        "high alert",
    ],
    "unknown": [],
}


COMMON_TYPO_REPLACEMENTS: dict[str, str] = {
    "базалную": "базальную",
    "скросоть": "скорость",
    "базалн": "базальн",
    "чуствит": "чувствит",
    "ммольл": "ммоль/л",
    "коэф": "коэффициент",
    "угл": "углеводный",
    "врем ": "временная ",
    "корригировать": "корректировать",
}


CONDITION_ALIASES: dict[str, list[str]] = {
    "ночью": ["ночью", "в ночь", "ночной"],
    "днем": ["днем", "днём", "дневной"],
    "утром": ["утром", "на завтрак", "завтрак"],
    "вечером": ["вечером", "вечерний", "на ужин", "ужин"],
    "после ужина": ["после ужина"],
    "при физической нагрузке": ["при нагрузке", "при физической нагрузке", "при трен", "нагрузке"],
    "в дни болезни": ["в дни болезни", "при болезни", "болезни"],
    "до еды": ["до еды", "перед едой"],
}


UNIT_NORMALIZATION_RULES: list[tuple[str, str]] = [
    (r"\b(ед|ед\.|eд|единиц[аы]?)(\s*/\s*ч|\s+ч|ч)\b", "ед/ч"),
    (r"\b(ед|ед\.|eд|единиц[аы]?)\b", "ед"),
    (r"\b(ммольл|ммоль\/л|ммоль|mmol\/l|mmol)\b", "ммоль/л"),
    (r"\b(гр|грамм[аыов]*|г)\b", "г"),
    (r"\b(минут[аы]?|мин\.?|mин)\b", "мин"),
    (r"\b(час(а|ов)?|ч)\b", "ч"),
    (r"\b(процентов|проц)\b", "%"),
]


EXPECTED_UNITS: dict[RecommendationType, set[str]] = {
    "basal_rate": {"Ед/ч"},
    "carb_ratio": {"г/Ед"},
    "correction_factor": {"ммоль/л/Ед"},
    "target_glucose": {"ммоль/л"},
    "target_range": {"ммоль/л"},
    "prebolus_time": {"мин"},
    "temp_basal_percent": {"%"},
    "active_insulin_time": {"ч"},
    "dual_bolus_split": {"%/% + ч"},
    "correction_interval": {"ч", "мин"},
    "low_glucose_alert_threshold": {"ммоль/л"},
    "high_glucose_alert_threshold": {"ммоль/л"},
    "unknown": set(),
}

