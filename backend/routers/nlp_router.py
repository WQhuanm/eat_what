from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from nlp_engine import ModelUnavailableError, active_model_name, vectorize_text


class VectorizeRequest(BaseModel):
    text: Optional[str] = None
    name: Optional[str] = None
    cuisine: Optional[str] = None
    taste_tags: Optional[List[str]] = None
    taste_scores: Optional[Dict[str, float]] = None
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shop_name: Optional[str] = None
    vector_dim: Optional[int] = 768


router = APIRouter(prefix="/v1", tags=["NLP 向量服务"])


@router.post("/vectorize")
def vectorize(body: VectorizeRequest) -> Dict[str, Any]:
    text = body.text
    if not text:
        tags = ",".join(body.taste_tags or [])
        ingredients = ",".join(body.ingredients or [])
        scores = ""
        if body.taste_scores:
            scores = " ".join([f"{k}:{v}" for k, v in body.taste_scores.items()])
        loc_token = ""
        if body.latitude is not None and body.longitude is not None:
            loc_token = f"位置网格:{round(body.latitude, 2)}_{round(body.longitude, 2)}"

        text = "\n".join(
            [
                f"菜名:{body.name or ''}",
                f"菜系:{body.cuisine or ''}",
                f"口味标签:{tags}",
                f"口味强度:{scores}",
                f"描述:{body.description or ''}",
                f"食材:{ingredients}",
                f"店铺:{body.shop_name or ''}",
                f"城市:{body.city or ''}",
                loc_token,
            ]
        )

    dim = body.vector_dim or 768
    try:
        vector = vectorize_text(text, dim=dim)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "vector": vector,
        "vector_dim": len(vector),
        "model": active_model_name(),
    }
