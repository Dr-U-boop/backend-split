from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.recommendation_extraction.dictionaries import RECOMMENDATION_ALIASES
from app.recommendation_extraction.schemas import MatchResult, RecommendationType

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover
    fuzz = None


def _norm_for_match(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zа-я0-9/+% ]+", " ", value.lower())).strip()


def _char_trigrams(value: str) -> set[str]:
    src = f"  {value}  "
    return {src[i : i + 3] for i in range(len(src) - 2)}


def _jaccard(a: str, b: str) -> float:
    a_grams = _char_trigrams(a)
    b_grams = _char_trigrams(b)
    if not a_grams or not b_grams:
        return 0.0
    return len(a_grams & b_grams) / len(a_grams | b_grams)


def _fuzzy_score(alias: str, text: str) -> float:
    if fuzz is not None:
        partial = float(fuzz.partial_ratio(alias, text))
        token = float(fuzz.token_set_ratio(alias, text))
    else:
        partial = 100.0 * SequenceMatcher(None, alias, text).ratio()
        token = partial
    jaccard = _jaccard(alias, text) * 100.0
    score = (0.5 * partial) + (0.3 * token) + (0.2 * jaccard)
    if alias in text:
        score += 8.0
    return min(score, 100.0)


def match_recommendation_types(
    text: str,
    threshold: float = 62.0,
) -> list[MatchResult]:
    text_norm = _norm_for_match(text)
    out: list[MatchResult] = []

    for rec_type, aliases in RECOMMENDATION_ALIASES.items():
        if rec_type == "unknown":
            continue
        best_alias = ""
        best_score = 0.0
        for alias in aliases:
            alias_norm = _norm_for_match(alias)
            if not alias_norm:
                continue
            # For very short aliases (e.g. "ук"), require exact token hit.
            if len(alias_norm) <= 3:
                if re.search(rf"\b{re.escape(alias_norm)}\b", text_norm):
                    score = 100.0
                else:
                    continue
            else:
                score = _fuzzy_score(alias_norm, text_norm)

            if score > best_score:
                best_score = score
                best_alias = alias

        if best_score >= threshold:
            out.append(
                MatchResult(
                    recommendation_type=rec_type,
                    alias=best_alias,
                    score=round(best_score, 3),
                    method="fuzzy_alias",
                )
            )

    out.sort(key=lambda x: x.score, reverse=True)
    return out

