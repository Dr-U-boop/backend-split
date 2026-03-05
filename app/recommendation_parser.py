from __future__ import annotations

from app.recommendation_extraction.extractor import (
    parse_batch,
    parse_batch_multi,
    parse_recommendation,
    parse_recommendations,
)


def parse_recommendation_text(text: str) -> dict:
    """
    Backward-compatible API for existing router integrations.
    """
    return parse_recommendation(text)


def parse_recommendations_batch(texts: list[str]) -> list[dict]:
    return parse_batch(texts)


def parse_recommendation_text_multi(text: str) -> list[dict]:
    return parse_recommendations(text)


def parse_recommendations_batch_multi(texts: list[str]) -> list[list[dict]]:
    return parse_batch_multi(texts)
