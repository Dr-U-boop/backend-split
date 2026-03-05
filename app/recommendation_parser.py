from __future__ import annotations

from app.recommendation_extraction.extractor import parse_batch, parse_recommendation


def parse_recommendation_text(text: str) -> dict:
    """
    Backward-compatible API for existing router integrations.
    """
    return parse_recommendation(text)


def parse_recommendations_batch(texts: list[str]) -> list[dict]:
    return parse_batch(texts)

