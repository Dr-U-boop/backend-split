# backend/app/routers/recommendations.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth_utils import get_current_doctor
# Импортируем наш новый локальный парсер
from app.recommendation_parser import parse_recommendation_text

router = APIRouter()

class RecommendationText(BaseModel):
    text: str

@router.post("/interpret")
async def interpret_recommendation(
    recommendation: RecommendationText,
    current_doctor: dict = Depends(get_current_doctor)
):
    """
    Принимает текстовую рекомендацию и возвращает ее структурированную
    интерпретацию с помощью ЛОКАЛЬНОГО NLP-парсера.
    """
    try:
        parsed_json = parse_recommendation_text(recommendation.text)
        return parsed_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при парсинге текста: {e}")