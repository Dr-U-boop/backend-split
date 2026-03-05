from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth_utils import get_current_doctor
from app.recommendation_parser import parse_recommendation_text, parse_recommendation_text_multi

router = APIRouter()


class RecommendationText(BaseModel):
    text: str


@router.post("/interpret")
async def interpret_recommendation(
    recommendation: RecommendationText,
    current_doctor: dict = Depends(get_current_doctor),
):
    """
    Single-best parse for backward compatibility.
    """
    try:
        return parse_recommendation_text(recommendation.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")


@router.post("/interpret-multi")
async def interpret_recommendation_multi(
    recommendation: RecommendationText,
    current_doctor: dict = Depends(get_current_doctor),
):
    """
    Multi-entity parse: one text can produce many recommendation objects.
    """
    try:
        items = parse_recommendation_text_multi(recommendation.text)
        return {"count": len(items), "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-parse error: {e}")

