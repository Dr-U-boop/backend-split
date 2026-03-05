from __future__ import annotations

import re

from app.recommendation_extraction.dictionaries import (
    COMMON_TYPO_REPLACEMENTS,
    UNIT_NORMALIZATION_RULES,
)


_HOMOGLYPHS = str.maketrans(
    {
        "a": "а",
        "e": "е",
        "o": "о",
        "p": "р",
        "c": "с",
        "y": "у",
        "x": "х",
        "k": "к",
        "m": "м",
        "t": "т",
        "h": "н",
        "b": "в",
    }
)


def _normalize_time_token(token: str) -> str | None:
    token = token.strip()
    if not token:
        return None

    if re.fullmatch(r"\d{1,2}", token):
        hour = int(token)
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"
        return None

    if re.fullmatch(r"\d{1,2}[:.]\d{1,2}", token):
        h_raw, m_raw = re.split(r"[:.]", token, maxsplit=1)
        hour = int(h_raw)
        minute = int(m_raw)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return None


def _normalize_inline_time_formats(text: str) -> str:
    def time_sub(match: re.Match[str]) -> str:
        raw = match.group(0)
        normalized = _normalize_time_token(raw)
        return normalized or raw

    text = re.sub(r"\b\d{1,2}[.:]\d{2}\b", time_sub, text)

    def interval_sub(match: re.Match[str]) -> str:
        start = _normalize_time_token(match.group("start")) or match.group("start")
        end = _normalize_time_token(match.group("end")) or match.group("end")
        return f"с {start} до {end}"

    text = re.sub(
        r"\bс\s*(?P<start>\d{1,2}(?::\d{2})?)\s*до\s*(?P<end>\d{1,2}(?::\d{2})?)\b",
        interval_sub,
        text,
    )
    return text


def normalize_text(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    normalized = (text or "").strip().lower()

    normalized = normalized.translate(_HOMOGLYPHS)
    normalized = normalized.replace("ё", "е")
    normalized = re.sub(r"[–—−‑‒]", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\bминус\s+(?=\d)", "-", normalized)

    # Decimal commas: 0,8 -> 0.8
    normalized = re.sub(r"(?<=\d),(?=\d)", ".", normalized)

    for wrong, right in COMMON_TYPO_REPLACEMENTS.items():
        if wrong in normalized:
            normalized = normalized.replace(wrong, right)
            warnings.append(f"autocorrect:{wrong}->{right}")

    extra_typos = {
        "корект": "коррект",
        "интрвал": "интервал",
        "ранше": "раньше",
        "предболус": "предболюс",
        "коррегировать": "корректировать",
        "корегировать": "корректировать",
    }
    for wrong, right in extra_typos.items():
        if wrong in normalized:
            normalized = normalized.replace(wrong, right)
            warnings.append(f"autocorrect:{wrong}->{right}")

    # Split merged number+unit tokens: 10гр -> 10 гр, 1ед -> 1 ед.
    normalized = re.sub(r"(?<=\d)(ед|гр|г|ммольл|ммоль|мин|ч)\b", r" \1", normalized)

    normalized = _normalize_inline_time_formats(normalized)

    for pattern, replacement in UNIT_NORMALIZATION_RULES:
        normalized = re.sub(pattern, replacement, normalized)

    # Harmonize separators and punctuation noise.
    normalized = re.sub(r"\s*[:]\s*", ":", normalized)
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized, warnings
