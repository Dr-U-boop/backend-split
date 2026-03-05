from app.recommendation_extraction.extractor import parse_recommendations


MULTI_CASES = [
    (
        "Изм базал 0,8 ед/ч с 23 до 02, угл коэф 1ед/9гр на завтрак, предболюс 15 мин до еды",
        {"basal_rate", "carb_ratio", "prebolus_time"},
        3,
    ),
    (
        "баз скорость 0.95 в 04.00-07.00; целев глюк 6,0 ммольл ночью и не корригир. раньше 3 ч после болюса",
        {"basal_rate", "target_glucose", "correction_interval"},
        2,
    ),
    (
        "врем базал -20 проц на 20:00-06:00 при вечерн нагрузке, порог низк глюк 4.4 с 00 до 06",
        {"temp_basal_percent", "low_glucose_alert_threshold"},
        2,
    ),
    (
        "углеводный коэф 1 ед/10 г в 6-11, фактор чуствит 1eд/2,2 ммоль/л утром, целев диапазон 5,5-7,0 днем",
        {"carb_ratio", "correction_factor", "target_range"},
        3,
    ),
    (
        "активный инсулин 4 часа, не делать повтор коррекцию ранше 3ч, порог высокой глюк 10 днем",
        {"active_insulin_time", "correction_interval", "high_glucose_alert_threshold"},
        2,
    ),
    (
        "базалную скросоть 1.10 ед ч 17:00-21:00, ужин коэф 1:12, предболюс за 10мин к ужину",
        {"basal_rate", "carb_ratio", "prebolus_time"},
        2,
    ),
    (
        "чувствит. 1 ед = 1,8 ммольл с 06 до 12; целев. глюкоза 5.8 в тот же период",
        {"correction_factor", "target_glucose"},
        2,
    ),
    (
        "60% сразу и 40% за 2 часа на ужын, врем базал +10% 18-22 если жирная еда",
        {"dual_bolus_split", "temp_basal_percent"},
        2,
    ),
    (
        "базал 0,75 ед/ч 00:00–03:00, порог низкой 4,4, активн инсул 4ч",
        {"basal_rate", "low_glucose_alert_threshold", "active_insulin_time"},
        2,
    ),
    (
        "угл коэфф 1ед/8гр с 7 до 10 , предболус 20 мин утром, целев диапаз 5.5—7.0 ммоль/л",
        {"carb_ratio", "prebolus_time", "target_range"},
        2,
    ),
    (
        "порог высок глюк 11.0 в день, порог низк 4,0 в ночь, коррекцию не раньше чем через 3ч",
        {"high_glucose_alert_threshold", "low_glucose_alert_threshold", "correction_interval"},
        2,
    ),
    (
        "базальная скорость 0,9 ЕД/Ч в 4-7 утра и 1.0 ед/ч в 17-21, углеводн коэф 1ед/12г вечером",
        {"basal_rate", "carb_ratio"},
        2,
    ),
    (
        "комб болюс: 50% сразу 50% за 3ч на ужин 18-22, актив инсул 4ч, пред-болюс 10 мин",
        {"dual_bolus_split", "active_insulin_time", "prebolus_time"},
        2,
    ),
    (
        "базал 0.8 ед/ч 23-02, угл коэф 1ед/9гр 06-11, фактор чувствит 1ед/2.2 ммольл 00-06, целев диапазон 5,5-7,0 06-23, предболюс 15 мин, актив инсулин 4ч, не корриг раньше 3ч, 60% сразу 40% за 2ч на ужин, порог низк 4,4 ночь, порог высок 10 день",
        {
            "basal_rate",
            "carb_ratio",
            "correction_factor",
            "target_range",
            "prebolus_time",
            "active_insulin_time",
            "correction_interval",
            "dual_bolus_split",
            "low_glucose_alert_threshold",
            "high_glucose_alert_threshold",
        },
        6,
    ),
]


def test_parse_recommendations_multi_cases():
    for text, expected_types, expected_min_count in MULTI_CASES:
        items = parse_recommendations(text)
        assert len(items) >= expected_min_count, (text, items)

        actual_types = {x["recommendation_type"] for x in items}
        assert expected_types & actual_types, (text, items)

