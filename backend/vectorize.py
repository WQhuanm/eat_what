import os
from typing import Dict, Iterable, List, Optional

import numpy as np

from nlp_engine import ModelUnavailableError, vectorize_text


TASTE_DIMENSIONS = ["酸", "甜", "辣", "咸", "清淡", "苦"]

TASTE_HINTS = {
    "酸": ["酸", "柠檬", "番茄", "酸菜", "醋", "开胃"],
    "甜": ["甜", "蜜", "奶", "糖", "巧克力", "焦糖", "奶油"],
    "辣": ["辣", "麻辣", "香辣", "剁椒", "藤椒", "泡椒"],
    "咸": ["咸", "酱", "卤", "咸香", "蚝油", "椒盐"],
    "清淡": ["清淡", "清汤", "原味", "白灼", "蒸", "养胃"],
    "苦": ["苦", "苦瓜", "黑咖啡"],
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _l2_normalize(values: List[float]) -> List[float]:
    arr = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12:
        return arr.tolist()
    return (arr / norm).tolist()


def infer_taste_scores(
    name: str,
    description: Optional[str] = None,
    taste_tags: Optional[Iterable[str]] = None,
    cuisine: Optional[str] = None,
) -> Dict[str, float]:
    text = " ".join([name or "", description or "", cuisine or ""])
    scores = {k: 0.0 for k in TASTE_DIMENSIONS}

    for tag in (taste_tags or []):
        if tag in scores:
            scores[tag] += 4.0

    for dim, hints in TASTE_HINTS.items():
        for hint in hints:
            if hint and hint in text:
                scores[dim] += 1.2

    if cuisine and "饮品甜点" in cuisine and scores["甜"] < 1.0:
        scores["甜"] += 2.0

    if sum(scores.values()) <= 0 and (not cuisine or "饮品甜点" not in cuisine):
        scores["咸"] = 2.0

    return {k: round(_clamp(v, 0.0, 5.0), 3) for k, v in scores.items()}


def build_dish_text(
    name: str,
    cuisine: Optional[str] = None,
    taste_tags: Optional[Iterable[str]] = None,
    description: Optional[str] = None,
    ingredients: Optional[Iterable[str]] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    shop_name: Optional[str] = None,
    taste_scores: Optional[Dict[str, float]] = None,
) -> str:
    tags = ",".join(taste_tags or [])
    ings = ",".join(ingredients or [])
    score_map = taste_scores or infer_taste_scores(name, description, taste_tags, cuisine)
    score_text = " ".join([f"{k}:{score_map.get(k, 0):.1f}" for k in TASTE_DIMENSIONS])

    loc_token = ""
    if latitude is not None and longitude is not None:
        loc_token = f"位置网格:{round(latitude, 2)}_{round(longitude, 2)}"

    lines = [
        f"菜名:{name}",
        f"菜系:{cuisine or '未知'}",
        f"口味标签:{tags or '无'}",
        f"口味强度:{score_text}",
        f"描述:{description or ''}",
        f"食材:{ings or ''}",
        f"店铺:{shop_name or ''}",
        f"城市:{city or ''}",
        loc_token,
    ]
    return "\n".join([x for x in lines if x])


def _nlp_service_vectorize(text: str, payload: Dict, nlp_url: str, dim: int) -> Optional[List[float]]:
    try:
        import requests
    except Exception:
        return None


def _local_model_vectorize(text: str, dim: int) -> Optional[List[float]]:
    vec = vectorize_text(text, dim=dim)
    return vec if vec else None
    try:
        resp = requests.post(
            nlp_url,
            json={
                "text": text,
                **payload,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        vec = resp.json().get("vector")
        if not isinstance(vec, list) or not vec:
            return None
        if len(vec) > dim:
            vec = vec[:dim]
        elif len(vec) < dim:
            vec = vec + [0.0] * (dim - len(vec))
        normed = _l2_normalize([float(v) for v in vec])
        return [round(float(x), 8) for x in normed]
    except Exception:
        return None


def generate_dish_vector(
    name: str,
    cuisine: Optional[str] = None,
    taste_tags: Optional[Iterable[str]] = None,
    description: Optional[str] = None,
    ingredients: Optional[Iterable[str]] = None,
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    shop_name: Optional[str] = None,
    vectorizer: str = "auto",
    nlp_url: Optional[str] = None,
    vector_dim: Optional[int] = None,
) -> List[float]:
    dim = vector_dim or int(os.getenv("DISH_VECTOR_DIM", "768"))
    nlp_service_url = nlp_url or os.getenv("NLP_VECTOR_URL", "http://nlp-service/v1/vectorize")

    taste_scores = infer_taste_scores(name, description, taste_tags, cuisine)
    text = build_dish_text(
        name=name,
        cuisine=cuisine,
        taste_tags=taste_tags,
        description=description,
        ingredients=ingredients,
        city=city,
        latitude=latitude,
        longitude=longitude,
        shop_name=shop_name,
        taste_scores=taste_scores,
    )
    payload = {
        "name": name,
        "cuisine": cuisine,
        "taste_tags": list(taste_tags or []),
        "taste_scores": taste_scores,
        "description": description,
        "ingredients": list(ingredients or []),
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "shop_name": shop_name,
    }

    if vectorizer == "nlp-service":
        result = _nlp_service_vectorize(text, payload, nlp_service_url, dim)
        if result is None:
            raise ModelUnavailableError("nlp-service 不可用，无法生成菜品向量")
        return result

    if vectorizer == "local-model":
        result = _local_model_vectorize(text, dim)
        if result is None:
            raise ModelUnavailableError("本地模型不可用，无法生成菜品向量")
        return result

    if vectorizer == "hashing":
        raise ModelUnavailableError("已禁用 hashing 向量化")

    result = _nlp_service_vectorize(text, payload, nlp_service_url, dim)
    if result is not None:
        return result
    local = _local_model_vectorize(text, dim)
    if local is not None:
        return local
    raise ModelUnavailableError("所有向量化通道不可用，无法生成菜品向量")


def generate_user_vector(
    taste_preferences: Optional[Dict[str, float]],
    cuisine_preferences: Optional[Iterable[str]],
    avoid_foods: Optional[Iterable[str]],
    answers: Dict,
    vector_dim: Optional[int] = None,
    vectorizer: str = "auto",
    nlp_url: Optional[str] = None,
) -> List[float]:
    dim = vector_dim or int(os.getenv("DISH_VECTOR_DIM", "768"))
    tastes = " ".join([f"{k}:{v}" for k, v in (taste_preferences or {}).items()])
    cuisines = ",".join(cuisine_preferences or [])
    avoids = ",".join(avoid_foods or [])
    taste_pref_raw = answers.get("taste_preference", [])
    if isinstance(taste_pref_raw, list):
        taste_pref = ",".join(taste_pref_raw)
    else:
        taste_pref = str(taste_pref_raw or "")

    cuisine_pref_raw = answers.get("cuisine_preference", [])
    if isinstance(cuisine_pref_raw, list):
        cuisine_pref = ",".join(cuisine_pref_raw)
    else:
        cuisine_pref = str(cuisine_pref_raw or "")

    avoid_raw = answers.get("avoid_foods", [])
    if isinstance(avoid_raw, list):
        avoid_now = ",".join(avoid_raw)
    else:
        avoid_now = str(avoid_raw or "")

    follow_up = answers.get("follow_up_answers", {}) or {}
    follow_up_text = " ".join([f"{k}:{v}" for k, v in follow_up.items()]) if isinstance(follow_up, dict) else str(follow_up)

    numeric_text = " ".join(
        [
            f"辣度:{answers.get('spicy_level', 0)}",
            f"麻度:{answers.get('numbing_level', 0)}",
            f"酸度:{answers.get('sour_level', 0)}",
            f"甜度:{answers.get('sweet_level', 0)}",
            f"咸度:{answers.get('salty_level', 0)}",
            f"油度:{answers.get('oily_level', 0)}",
        ]
    )

    fullness = "中"
    form = str(answers.get("dining_form", ""))
    goal = str(answers.get("dining_goal", ""))
    scene = str(answers.get("dining_scene", ""))
    if any(k in form for k in ["正餐", "快餐"]) or any(k in scene for k in ["多人", "家庭"]) or "填饱" in goal:
        fullness = "高"
    if any(k in form for k in ["甜品", "轻食", "加餐"]):
        fullness = "低"

    richness = "中"
    if any(k in str(answers.get("taste_preference", "")) for k in ["重口", "酱香", "孜然", "肉食"]):
        richness = "高"
    if "清淡" in str(answers.get("taste_preference", "")):
        richness = "低"

    social = "低"
    if any(k in scene for k in ["多人", "聚餐", "宴请", "约会", "小聚"]):
        social = "高"
    elif "家庭" in scene:
        social = "中"
    text = "\n".join(
        [
            f"用户口味偏好:{tastes}",
            f"用户菜系偏好:{cuisines}",
            f"用户忌口:{avoids}",
            f"当前时段:{answers.get('meal_time', '')}",
            f"当前场景人数:{answers.get('dining_scene', '')}",
            f"当前用餐目标:{answers.get('dining_goal', '')}",
            f"当前决策偏好:{answers.get('decision_style', '')}",
            f"当前口味需求:{taste_pref}",
            f"当前就餐形式:{answers.get('dining_form', '')}",
            f"当前预算:{answers.get('budget', '')}",
            f"当前特殊状态:{answers.get('special_state', '')}",
            f"当前菜系偏好:{cuisine_pref}",
            f"当前食材偏好:{answers.get('ingredient_preference', '')}",
            f"当前忌口:{avoid_now}",
            f"当前口感偏好:{answers.get('texture_preference', '')}",
            f"当前温度偏好:{answers.get('temperature_preference', '')}",
            f"当前特殊需求:{answers.get('special_requirements', '')}",
            f"追问回答:{follow_up_text}",
            f"强度向量:{numeric_text}",
            f"衍生饱腹度:{fullness}",
            f"衍生浓郁度:{richness}",
            f"衍生社交属性:{social}",
        ]
    )

    if vectorizer == "local-model":
        result = _local_model_vectorize(text, dim)
        if result is None:
            raise ModelUnavailableError("本地模型不可用，无法生成用户向量")
        return result

    if vectorizer == "nlp-service":
        result = _nlp_service_vectorize(text, {"text": text}, nlp_url or os.getenv("NLP_VECTOR_URL", "http://nlp-service/v1/vectorize"), dim)
        if result is None:
            raise ModelUnavailableError("nlp-service 不可用，无法生成用户向量")
        return result

    if vectorizer == "hashing":
        raise ModelUnavailableError("已禁用 hashing 向量化")

    result = _nlp_service_vectorize(text, {"text": text}, nlp_url or os.getenv("NLP_VECTOR_URL", "http://nlp-service/v1/vectorize"), dim)
    if result is not None:
        return result
    local = _local_model_vectorize(text, dim)
    if local is not None:
        return local
    raise ModelUnavailableError("所有向量化通道不可用，无法生成用户向量")
