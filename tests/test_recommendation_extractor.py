import pytest

from app.recommendation_extraction.extractor import parse_recommendation


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_unit", "expected_value"),
    [
        ("Изменить базальную скорость до 0.80 Ед/ч в период 23:00–02:00", "basal_rate", "Ед/ч", 0.8),
        ("базал 0,8 ед/ч с 23 до 2", "basal_rate", "Ед/ч", 0.8),
        ("баз скорость 0.95 в 04.00-07.00", "basal_rate", "Ед/ч", 0.95),
        ("углеводный коэффициент 1 ед/9 г на завтрак", "carb_ratio", "г/Ед", 9.0),
        ("угл коэф 1ед/10гр с 6 до 11", "carb_ratio", "г/Ед", 10.0),
        ("фактор чувствительности 1 Ед/2.2 ммоль/л в период 00:00–06:00", "correction_factor", "ммоль/л/Ед", 2.2),
        ("фактор чуствит 1eд/2,2 ммольл ночью", "correction_factor", "ммоль/л/Ед", 2.2),
        ("целевой диапазон 5.5-7.0 ммоль/л днем", "target_range", "ммоль/л", None),
        ("предболюс 15 мин до еды утром", "prebolus_time", "мин", 15.0),
        ("врем базал -20% при вечерней нагрузке", "temp_basal_percent", "%", -20.0),
        ("активный инсулин 4 часа", "active_insulin_time", "ч", 4.0),
        ("не корригировать раньше 3 ч после предыдущего болюса", "correction_interval", "ч", 3.0),
        ("порог низкой глюкозы 4.4 ночью", "low_glucose_alert_threshold", "ммоль/л", 4.4),
        ("порог высокой глюкозы 10 днем", "high_glucose_alert_threshold", "ммоль/л", 10.0),
        ("60% сразу и 40% за 2 часа на ужин", "dual_bolus_split", "%/% + ч", None),
        ("чувствит. 1 ед = 2.5 ммоль", "correction_factor", "ммоль/л/Ед", 2.5),
        ("целев диап 5,5-7,0", "target_range", "ммоль/л", None),
        ("предболюс за 15 мин утром", "prebolus_time", "мин", 15.0),
        ("врем базал минус 30 проц при нагр вечером", "temp_basal_percent", "%", None),
        ("не корректировать раньше 180 мин", "correction_interval", "ч", 3.0),
        ("таргет 6.4 ммоль/л ночью", "target_glucose", "ммоль/л", 6.4),
        ("низкий порог 3.9", "low_glucose_alert_threshold", "ммоль/л", 3.9),
        ("высокий порог 11.2", "high_glucose_alert_threshold", "ммоль/л", 11.2),
        ("ук 1ед/12г", "carb_ratio", "г/Ед", 12.0),
        ("базальная 1.1 ед ч 22-02", "basal_rate", "Ед/ч", 1.1),
    ],
)
def test_parse_dirty_inputs(text, expected_type, expected_unit, expected_value):
    parsed = parse_recommendation(text)
    assert parsed["recommendation_type"] == expected_type
    assert parsed["unit"] == expected_unit
    assert parsed["confidence"] >= 0.45
    assert parsed["parse_method"] in {"rule_regex", "rule_fuzzy", "ml_classifier", "hybrid"}

    if expected_type == "target_range":
        assert parsed["value_min"] is not None
        assert parsed["value_max"] is not None
    elif expected_type == "dual_bolus_split":
        assert isinstance(parsed["value"], str)
    elif expected_value is not None:
        assert parsed["value"] == pytest.approx(expected_value, abs=1e-3)


def test_time_interval_normalized():
    parsed = parse_recommendation("базал 0,8 ед/ч с 23 до 2")
    assert parsed["time_start"] == "23:00"
    assert parsed["time_end"] == "02:00"

