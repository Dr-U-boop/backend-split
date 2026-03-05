from pathlib import Path

from app.recommendation_extraction.extractor import parse_recommendations


def test_user_dataset_multi_recommendations():
    dataset_path = Path("tests/data/mixed_recommendations_ru.txt")
    lines = [x.strip() for x in dataset_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(lines) >= 20

    for text in lines:
        items = parse_recommendations(text)
        assert len(items) >= 1, text
        types = {item["recommendation_type"] for item in items}
        assert "unknown" not in types, (text, items)

        # Most records in dataset contain multiple recommendation types.
        if "," in text or ";" in text:
            assert len(items) >= 2, (text, items)

