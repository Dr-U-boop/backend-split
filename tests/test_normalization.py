from app.recommendation_extraction.normalization import normalize_text


def test_normalize_time_and_units():
    text = "базалную скросоть 0,8 ед ч с 23 до 2"
    normalized, warnings = normalize_text(text)
    assert "0.8" in normalized
    assert "ед/ч" in normalized
    assert "с 23:00 до 02:00" in normalized
    assert warnings


def test_normalize_mmol_noise():
    text = "фактор чуствит 1eд/2,2 ммольл"
    normalized, _ = normalize_text(text)
    assert "ммоль/л" in normalized
    assert "1 ед/2.2" in normalized
