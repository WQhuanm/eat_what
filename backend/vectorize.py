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

CUISINE_EXPANSION = {
    "米粉面条": "粉面主食 汤面拌面 米线河粉 面食快餐 碳水主食 面条米线",
    "麻辣烫冒菜": "麻辣烫 冒菜 麻辣口味 辣味快餐 川味小吃 麻辣鲜香 烫菜煮菜",
    "地方菜系": "地方特色菜 中式炒菜 家常菜 川湘菜 赣菜 粤菜 地方风味",
    "烧烤烤肉": "烧烤 烤肉 BBQ 炭烤 铁板烧 烤串 明火炙烤",
    "快餐便当": "快餐 便当 盒饭 简餐 快速用餐 盖浇饭",
    "汉堡薯条": "汉堡 薯条 炸鸡 西式快餐 可乐套餐 面包肉饼",
    "炸鸡炸串": "炸鸡 炸串 油炸食品 香脆 酥脆 裹粉油炸",
    "饺子馄饨": "饺子 馄饨 抄手 水饺 蒸饺 面食 带馅面点",
    "粥食点心": "粥 点心 包子 馒头 蒸品 清淡早餐 稀饭面点",
    "奶茶果汁": "奶茶 果汁 饮品 甜品 饮料 冰品 甜饮",
    "特色小吃": "小吃 零食 街头美食 地方小吃 风味小食",
    "鸭脖卤味": "鸭脖 卤味 卤制品 酱卤 卤菜 凉菜 卤制熟食",
}

TASTE_EXPANSION = {
    "辣": "辛辣 辣味十足 麻辣 香辣 火辣 辣味浓郁",
    "麻": "麻味 花椒麻 麻辣 麻感 椒麻",
    "酸": "酸味 酸爽 醋香 酸香 酸辣 酸甜",
    "甜": "甜味 甜美 香甜 甜香 糖甜 奶甜",
    "咸": "咸味 咸香 鲜美 咸鲜 咸香浓郁",
    "清淡": "清淡 清爽 原味 不油腻 健康低脂 少油少盐 清鲜",
    "炸": "油炸 香脆 酥脆 外酥里嫩 金黄酥脆",
    "烤": "炭烤 烧烤 炙烤 焦香 烟熏 烤制",
    "煎": "香煎 油煎 铁板煎 焦香 煎制",
    "卤": "卤制 酱卤 卤香 卤味浓郁 卤煮",
    "蒸": "清蒸 蒸制 蒸汽烹饪 原味鲜嫩",
    "汤": "汤品 汤底浓郁 鲜汤 高汤 骨汤",
}

DINING_FORM_EXPANSION = {
    "快餐简餐": "快速简餐 快餐 便捷用餐 单人快餐 速食 简单快捷 出餐快",
    "正餐主食": "正餐 主餐 丰盛正餐 米饭炒菜 正式用餐 饱腹主食",
    "小吃点心": "小吃 点心 零食 解馋小食 街头小吃 风味小食",
    "甜品/饮品": "甜品 饮品 甜食 冰品 奶茶 果汁 甜饮",
    "轻食": "轻食 健康低卡 沙拉 减脂餐 清淡饮食 低脂低油 高蛋白轻食",
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
    shop_specialties: Optional[Iterable[str]] = None,
    shop_taste_context: Optional[Iterable[str]] = None,
    shop_scene: Optional[str] = None,
) -> str:
    cuisine = cuisine or ""
    cuisine_expanded = CUISINE_EXPANSION.get(cuisine, "")
    tags_str = ",".join(taste_tags or [])
    ings = ",".join(ingredients or [])
    specialties = ",".join(shop_specialties or [])
    taste_context_str = ",".join(shop_taste_context or [])
    score_map = taste_scores or infer_taste_scores(name, description, taste_tags, cuisine)
    score_text = " ".join([f"{k}:{score_map.get(k, 0):.1f}" for k in TASTE_DIMENSIONS])

    # 口味自然语言
    taste_desc_parts = []
    for tag in (taste_tags or []):
        exp = TASTE_EXPANSION.get(tag)
        if exp:
            taste_desc_parts.append(f"{exp}的{tag}味")
        else:
            taste_desc_parts.append(tag)
    taste_desc = "，".join(taste_desc_parts) if taste_desc_parts else "口味适中"

    loc_token = ""
    if latitude is not None and longitude is not None:
        loc_token = f"位置网格:{round(latitude, 2)}_{round(longitude, 2)}"

    lines = [
        f"这是一道属于{cuisine}类的菜品。这种{cuisine}菜的特点就是{cuisine_expanded}。口味是{taste_desc}。",
        f"菜名:{name}",
        f"菜系:{cuisine}",
        f"口味标签:{tags_str}",
        f"口味强度:{score_text}",
        f"描述:{description or ''}",
        f"食材:{ings or ''}",
        f"店铺:{shop_name or ''}",
        f"商家主营品类:{specialties or ''}",
        f"商家口味:{taste_context_str or ''}",
        f"商家场景:{shop_scene or ''}",
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
    shop_specialties: Optional[Iterable[str]] = None,
    shop_taste_context: Optional[Iterable[str]] = None,
    shop_scene: Optional[str] = None,
    vectorizer: str = "auto",
    nlp_url: Optional[str] = None,
    vector_dim: Optional[int] = None,
) -> List[float]:
    dim = vector_dim or int(os.getenv("DISH_VECTOR_DIM", "768"))
    nlp_service_url = nlp_url or os.getenv("NLP_VECTOR_URL", "http://nlp-service/v1/vectorize")

    # 根据商家类型增强口味分数
    from shop_name_parser import enhance_taste_scores
    base_scores = infer_taste_scores(name, description, taste_tags, cuisine)
    taste_scores = enhance_taste_scores(shop_name or "", base_scores)
    
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
        shop_specialties=shop_specialties,
        shop_taste_context=shop_taste_context,
        shop_scene=shop_scene,
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
        "shop_specialties": list(shop_specialties or []),
        "shop_taste_context": list(shop_taste_context or []),
        "shop_scene": shop_scene,
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
    historical_cuisines: Optional[Dict[str, float]] = None,
    historical_tastes: Optional[Dict[str, float]] = None,
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

    # 从强度滑块推导当前口味描述（新问卷无 taste_preference 字段，由滑块值反推）
    taste_desc_parts = []
    spicy = answers.get("spicy_level")
    if spicy is not None and int(spicy) >= 3:
        taste_desc_parts.append("重辣")
    elif spicy is not None and int(spicy) >= 1:
        taste_desc_parts.append("微辣")
    numbing = answers.get("numbing_level")
    if numbing is not None and int(numbing) >= 3:
        taste_desc_parts.append("重麻")
    sour = answers.get("sour_level")
    if sour is not None and int(sour) >= 3:
        taste_desc_parts.append("酸味突出")
    sweet = answers.get("sweet_level")
    if sweet is not None and int(sweet) >= 3:
        taste_desc_parts.append("偏甜")
    salty = answers.get("salty_level")
    if salty is not None and int(salty) >= 3:
        taste_desc_parts.append("重咸")
    oily = answers.get("oily_level")
    if oily is not None and int(oily) >= 4:
        taste_desc_parts.append("油腻浓烈")
    elif oily is not None and int(oily) <= 1:
        taste_desc_parts.append("清淡少油")
    slider_taste = ",".join(taste_desc_parts) if taste_desc_parts else "无特殊口味偏好"
    # 合并旧字段值（如有）与滑块推导值
    if taste_pref:
        combined_taste = taste_pref + ";" + slider_taste
    else:
        combined_taste = slider_taste

    cuisine_pref_raw = answers.get("cuisine_preference", [])
    if isinstance(cuisine_pref_raw, list):
        cuisine_pref = ",".join(cuisine_pref_raw)
    else:
        cuisine_pref = str(cuisine_pref_raw or "")

    # 菜系偏好扩展为丰富自然语言
    cuisine_expanded_text = ""
    if cuisine_pref and cuisine_pref_raw:
        cuis_list = cuisine_pref_raw if isinstance(cuisine_pref_raw, list) else [cuisine_pref]
        exp_parts = []
        for c in cuis_list:
            exp = CUISINE_EXPANSION.get(c, c)
            exp_parts.append(f"{c}也就是{exp}")
        cuisine_expanded_text = "用户想吃" + "，也喜欢".join(exp_parts) + "之类的食物。"

    # 用餐形态扩展
    form = str(answers.get("dining_form", ""))
    form_expanded = DINING_FORM_EXPANSION.get(form, form)
    form_desc_text = f"用户就餐形式是{form}，想要{form_expanded}。"

    # 口味强度转自然语言
    spicy_raw = answers.get("spicy_level")
    oily_raw = answers.get("oily_level")
    numbing_raw = answers.get("numbing_level")
    sour_raw = answers.get("sour_level")
    sweet_raw = answers.get("sweet_level")
    salty_raw = answers.get("salty_level")

    spicy_v = int(spicy_raw) if spicy_raw is not None else None
    oily_v = int(oily_raw) if oily_raw is not None else None
    numbing_v = int(numbing_raw) if numbing_raw is not None else None
    sour_v = int(sour_raw) if sour_raw is not None else None
    sweet_v = int(sweet_raw) if sweet_raw is not None else None
    salty_v = int(salty_raw) if salty_raw is not None else None

    taste_nl_parts = []
    if spicy_v is not None and spicy_v >= 4:
        taste_nl_parts.append("喜欢重辣口味无辣不欢")
    elif spicy_v is not None and spicy_v >= 2:
        taste_nl_parts.append("喜欢中辣带点辣味的食物")
    elif spicy_v is not None and spicy_v <= 1:
        taste_nl_parts.append("不吃辣")
    if numbing_v is not None and numbing_v >= 3:
        taste_nl_parts.append("喜欢麻味喜欢花椒")
    if oily_v is not None and oily_v >= 4:
        taste_nl_parts.append("喜欢重油浓烈油炸香脆口感")
    elif oily_v is not None and oily_v <= 1:
        taste_nl_parts.append("喜欢清淡少油清爽不油腻")
    taste_nl_text = "，".join(taste_nl_parts) if taste_nl_parts else "口味无特殊偏好"

    fullness = "中"
    form2 = str(answers.get("dining_form", ""))
    goal = str(answers.get("dining_goal", ""))
    scene = str(answers.get("dining_scene", ""))
    if any(k in form2 for k in ["正餐", "快餐"]) or any(k in scene for k in ["多人", "家庭"]) or "填饱" in goal:
        fullness = "高"
    if any(k in form2 for k in ["甜品", "轻食", "加餐"]):
        fullness = "低"

    richness = "中"
    if (
        (spicy_v is not None and spicy_v >= 4) or
        (salty_v is not None and salty_v >= 4) or
        (oily_v is not None and oily_v >= 4)
    ):
        richness = "高"
    elif (
        spicy_v is not None and salty_v is not None and oily_v is not None and
        spicy_v <= 1 and salty_v <= 1 and oily_v <= 1
    ):
        richness = "低"

    social = "低"
    if any(k in scene for k in ["多人", "聚餐", "宴请", "约会", "小聚"]):
        social = "高"
    elif "家庭" in scene:
        social = "中"
    # 历史偏好文本
    hist_cuisine_text = ""
    hist_taste_text = ""
    if historical_cuisines:
        top_cuisines = sorted(historical_cuisines.items(), key=lambda x: x[1], reverse=True)[:5]
        hist_cuisine_text = ",".join([f"{c}({n}次)" for c, n in top_cuisines])
    if historical_tastes:
        top_tastes = sorted(historical_tastes.items(), key=lambda x: x[1], reverse=True)[:8]
        hist_taste_text = ",".join([f"{t}({n}次)" for t, n in top_tastes])

    follow_up = answers.get("follow_up_answers", {}) or {}
    follow_up_text = " ".join([f"{k}:{v}" for k, v in follow_up.items()]) if isinstance(follow_up, dict) else str(follow_up)

    text = "\n".join(
        [
            # 菜系偏好放在最前，用扩展描述增强向量权重
            cuisine_expanded_text,
            f"当前菜系偏好:{cuisine_pref}",
            # 用餐形态扩展描述
            form_desc_text,
            # 口味强度自然语言
            f"口味强度要求:{taste_nl_text}",
            f"强度数值:辣度{spicy_v if spicy_v is not None else '未选'}麻度{numbing_v if numbing_v is not None else '未选'}酸度{sour_v if sour_v is not None else '未选'}甜度{sweet_v if sweet_v is not None else '未选'}咸度{salty_v if salty_v is not None else '未选'}油度{oily_v if oily_v is not None else '未选'}",
            # 其他上下文
            f"用户口味偏好:{tastes}",
            f"用户菜系偏好:{cuisines}",
            f"用户忌口:{avoids}",
            f"当前时段:{answers.get('meal_time', '')}",
            f"当前场景人数:{answers.get('dining_scene', '')}",
            f"当前用餐目标:{answers.get('dining_goal', '')}",
            f"当前决策偏好:{answers.get('decision_style', '')}",
            f"当前口味需求:{combined_taste}",
            f"当前预算:{','.join(answers.get('budget', []))}",
            f"追问回答:{follow_up_text}",
            f"衍生饱腹度:{fullness}",
            f"衍生浓郁度:{richness}",
            f"衍生社交属性:{social}",
            f"历史偏好菜系:{hist_cuisine_text}",
            f"历史偏好口味:{hist_taste_text}",
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
