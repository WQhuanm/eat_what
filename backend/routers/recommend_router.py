from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict
import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from database import get_db
from models import User, UserProfile, Dish, HistoryRecord, InteractionLog
from schemas import (
    QuestionOption, QuestionnaireAnswers, RecommendationResponse,
    RecommendationItem, SelectionConfirm, InteractionLogCreate,
)
from utils import get_current_user, gen_uuid, haversine_km, BUDGET_RANGE
from vectorize import generate_user_vector
from nlp_engine import ModelUnavailableError

router = APIRouter(prefix="/api/recommend", tags=["推荐系统"])

TASTE_TAG_SPICY = {"辣", "麻辣", "香辣", "剁椒", "藤椒", "泡椒", "红油", "酸辣"}
TASTE_TAG_LIGHT = {"清淡", "清汤", "原味", "白灼", "蒸", "养胃", "低脂"}
TASTE_TAG_HEAVY = {"炸", "烤", "煎", "卤", "红烧", "酱香", "孜然", "芝士", "奶", "油"}

FAST_FOOD_CUISINES = {"米粉面条", "快餐便当", "麻辣烫冒菜", "饺子馄饨", "汉堡薯条", "炸鸡炸串", "特色小吃"}
LIGHT_FOOD_PENALTY_CUISINES = {"烧烤烤肉", "炸鸡炸串", "麻辣烫冒菜", "鸭脖卤味", "汉堡薯条"}

BEVERAGE_CUISINES = {"奶茶果汁"}
BEVERAGE_KEYWORDS = {
    "奶茶", "果汁", "咖啡", "拿铁", "美式", "饮品", "柠檬茶", "奶昔", "苏打", "可乐", "酸奶昔", "气泡水", "乌龙茶", "冷萃"
}
STAPLE_KEYWORDS = {
    "饭", "面", "粉", "米线", "冒菜", "麻辣烫", "饺", "馄饨", "粥", "套餐", "便当", "盖饭", "炒饭", "拌饭", "沙拉", "鸡胸", "三明治"
}

LIGHT_FOOD_KEYWORDS = {
    "轻食", "减脂", "低脂", "健康", "沙拉", "蔬菜", "鸡胸", "杂粮", "全麦", "清汤", "水煮", "蒸",
    "低卡", "代餐", "原味", "少油", "清淡"
}

HEAVY_FOOD_KEYWORDS = {
    "炸", "油炸", "香辣", "麻辣", "红烧", "肥牛", "肥肠", "烧烤", "烤肉", "鸡排", "汉堡", "薯条",
    "奶油", "芝士", "卤", "重油", "火锅"
}

SPICY_TEXT_KEYWORDS = {"辣", "麻辣", "香辣", "剁椒", "泡椒", "藤椒", "红油", "冒菜", "麻辣烫", "火锅"}
OILY_TEXT_KEYWORDS = {"炸", "油", "油腻", "肥", "红烧", "奶油", "芝士", "卤", "重油", "烧烤"}

# 菜系精细化权重：越具体的菜系权重越高，避免“地方菜系”这类大类泛化过度
CUISINE_SPECIFICITY = {
    "麻辣烫冒菜": 1.00,
    "米粉面条": 0.95,
    "饺子馄饨": 0.90,
    "特色小吃": 0.85,
    "快餐便当": 0.80,
    "地方菜系": 0.55,
}

CUISINE_INTENT_KEYWORDS = {
    "麻辣烫冒菜": ["麻辣烫", "冒菜", "麻辣拌", "串串", "火锅"],
    "米粉面条": ["面", "粉", "米线", "小面", "拉面", "拌面", "炒粉"],
    "地方菜系": ["小炒", "煲仔", "川", "湘", "赣", "成都", "重庆"],
    "烧烤烤肉": ["烧烤", "烤串", "生蚝", "肉筋", "羊肉串", "牛肉串", "鸡翅", "烤肉", "掌中宝", "五花肉", "鸭肠", "鱿鱼", "烤鱼"],
    "炸鸡炸串": ["炸鸡", "鸡排", "鸡米花", "炸串", "薯条", "鸡翅", "鸡腿", "盐酥鸡", "鸡块"],
    "鸭脖卤味": ["鸭脖", "卤味", "鸭架", "鸭锁骨", "鸭肠", "鸭头", "凤爪", "卤蛋", "鸭掌"],
}

SNACK_POSITIVE_KEYWORDS = {
    "烧烤", "烤串", "生蚝", "肉筋", "羊肉串", "牛肉串", "鸭肠", "掌中宝", "卤味", "鸭脖", "炸串", "鸡排", "鸡米花", "小吃", "夜宵"
}
SNACK_NEGATIVE_KEYWORDS = {
    "米饭", "盖饭", "便当", "炒饭", "拌饭", "套餐", "整只", "半只", "披萨", "汉堡", "三明治", "奶茶", "果汁", "饮品"
}

DUCK_BRAISE_KEYWORDS = {"鸭脖", "鸭锁骨", "鸭掌", "鸭头", "鸭架", "凤爪", "卤蛋", "豆干", "卤味", "鸭肠"}
MAIN_MEAL_SHAPE_KEYWORDS = {"饭", "面", "堡", "披萨", "便当", "套餐", "盖饭", "炒饭"}


# ---------- 1. 获取问答题目 ----------
@router.get("/questions", response_model=List[QuestionOption])
def get_questions():
    """返回增强版问答题目列表"""
    return [
        QuestionOption(question_key="meal_time", question_text="当前用餐时段（必选）", options=["早餐", "午餐", "下午加餐", "晚餐", "夜宵", "随机/非正餐"]),
        QuestionOption(question_key="dining_scene", question_text="用餐人数与场景（必选）", options=["单人简餐（快速解决）", "单人精致餐（慢食）", "双人约会/小聚", "朋友小聚（3-5人）", "多人聚餐（6人以上）", "家庭日常用餐", "家庭正式聚餐/宴请"]),
        QuestionOption(question_key="dining_goal", question_text="本次用餐核心目的（必选）", options=["简单填饱肚子", "日常家常餐", "享受美味大餐", "解馋/满足欲望"]),
        QuestionOption(question_key="decision_style", question_text="本次选择偏好（必选）", options=["只吃熟悉口味", "愿意尝试新口味", "优先热门爆款", "无所谓，好吃就行"]),
        QuestionOption(question_key="dining_form", question_text="用餐形态（必选）", options=["正餐主食", "快餐简餐", "小吃点心", "甜品/饮品", "轻食"]),
        QuestionOption(question_key="budget", question_text="预算范围（多选）", options=["20元以下", "20-50元", "50-100元", "100元以上"], multi_select=True, question_type="multi"),
        QuestionOption(question_key="cuisine_preference", question_text="意向菜系/品类（多选，可选）", options=["烧烤烤肉", "奶茶果汁", "炸鸡炸串", "鸭脖卤味", "特色小吃", "米粉面条", "快餐便当", "汉堡薯条", "粥食点心", "地方菜系", "麻辣烫冒菜", "饺子馄饨"], multi_select=True, question_type="multi", required=False),
        QuestionOption(
            question_key="taste_levels",
            question_text="口味强度偏好（可选，不选表示无特别偏好）",
            question_type="multi_scale",
            required=False,
            sub_questions=[
                {"key": "spicy_level", "label": "辣度", "min_value": 0, "max_value": 5, "step": 1},
                {"key": "numbing_level", "label": "麻度", "min_value": 0, "max_value": 5, "step": 1},
                {"key": "sour_level", "label": "酸度", "min_value": 0, "max_value": 5, "step": 1},
                {"key": "sweet_level", "label": "甜度", "min_value": 0, "max_value": 5, "step": 1},
                {"key": "salty_level", "label": "咸度", "min_value": 0, "max_value": 5, "step": 1},
                {"key": "oily_level", "label": "油度", "min_value": 0, "max_value": 5, "step": 1},
            ]
        ),
    ]


# ---------- 2. 提交问答 → 获取推荐 ----------
@router.post("/submit", response_model=RecommendationResponse)
def submit_and_recommend(
    answers: QuestionnaireAnswers,
    latitude: float = 0.0,
    longitude: float = 0.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    batch_id = gen_uuid()

    # ----- 硬性过滤 -----
    q = db.query(Dish).filter(Dish.is_approved == True)

    # 预算多选：取并集范围
    budget_list = answers.budget if answers.budget else []
    if budget_list:
        budget_ranges = [BUDGET_RANGE.get(b, (0, 99999)) for b in budget_list]
        min_price = min(r[0] for r in budget_ranges)
        max_price = max(r[1] for r in budget_ranges)
        q = q.filter(Dish.price >= min_price, Dish.price <= max_price)

    candidates: List[Dish] = q.all()

    # ----- 获取历史偏好（按当前问卷相似度加权）-----
    current_answers_dict = answers.model_dump()
    hist_cuisines, hist_tastes = _get_user_history_prefs(user.id, db, current_answers_dict)

    # ----- 向量召回 -----
    try:
        user_vector = _build_user_vector(answers, profile, hist_cuisines, hist_tastes)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    candidate_vectors = [np.array(d.vector) for d in candidates if d.vector]
    if not candidate_vectors:
        raise HTTPException(status_code=404, detail="没有符合条件的菜品")

    similarities = cosine_similarity([user_vector], candidate_vectors)[0]
    vector_scores = {candidates[i].id: similarities[i] for i in range(len(candidates))}

    # ----- 综合排序 -----
    scored: List[tuple] = []
    for d in candidates:
        if d.id not in vector_scores:
            continue
        sim_score = vector_scores[d.id]

        # 距离惩罚
        dist = haversine_km(latitude, longitude, d.latitude or 0, d.longitude or 0) if latitude else 0
        dist_penalty = max(0, 1 - dist / 10)

        # 历史去重
        history_counts = _batch_history_counts(user.id, [d.id], db)
        count = history_counts.get(d.id, 0)
        history_score = 1.0 if count == 0 else max(0.1, 1.0 - count * 0.3)

        # 历史偏好匹配加分（当前问卷与历史越相似，历史选择的参考权重越大）
        history_affinity = 0.0
        if hist_cuisines and d.cuisine and d.cuisine in hist_cuisines:
            history_affinity += 0.15 * min(1.0, hist_cuisines[d.cuisine] / 1.5)
        if hist_tastes and d.taste_tags:
            matched = [t for t in d.taste_tags if t in hist_tastes]
            if matched:
                total_weight = sum(hist_tastes[t] for t in matched)
                history_affinity += 0.10 * min(1.0, total_weight / 3)

        # 菜系匹配加分（按菜系精细度加权，避免大类过强）
        cuisine_bonus = 0.0
        if answers.cuisine_preference and d.cuisine:
            if d.cuisine in answers.cuisine_preference:
                cuisine_bonus = 0.30 * CUISINE_SPECIFICITY.get(d.cuisine, 0.75)

        # 画像菜系补偿：当问卷未选菜系时，使用用户画像菜系偏好参与重排
        profile_cuisine_bonus = 0.0
        profile_cuisine_prefs: List[str] = []
        if profile and profile.cuisine_preferences:
            if isinstance(profile.cuisine_preferences, list):
                profile_cuisine_prefs = [str(x) for x in profile.cuisine_preferences if str(x).strip()]
            elif isinstance(profile.cuisine_preferences, str):
                profile_cuisine_prefs = [
                    p.strip()
                    for p in re.split(r"[,，、\s]+", profile.cuisine_preferences)
                    if p and p.strip()
                ]

        if (not answers.cuisine_preference) and profile_cuisine_prefs and d.cuisine:
            if d.cuisine in profile_cuisine_prefs:
                profile_cuisine_bonus += 0.26 * CUISINE_SPECIFICITY.get(d.cuisine, 0.75)
            else:
                # 中性问卷下给非画像菜系轻微惩罚，避免画像偏好被淹没
                profile_cuisine_bonus -= 0.05

        # 意图关键词加分：优先使用当前问卷菜系；若未选则回退到画像菜系
        intent_bonus = 0.0
        active_cuisine_prefs = answers.cuisine_preference if answers.cuisine_preference else profile_cuisine_prefs
        if active_cuisine_prefs:
            text_for_match = f"{d.name or ''} {d.description or ''}"
            source_factor = 1.0 if answers.cuisine_preference else 0.85
            for pref in active_cuisine_prefs:
                words = CUISINE_INTENT_KEYWORDS.get(pref, [])
                if words and any(w in text_for_match for w in words):
                    if pref == "麻辣烫冒菜":
                        intent_bonus = max(intent_bonus, 0.22 * source_factor)
                    elif pref == "米粉面条":
                        intent_bonus = max(intent_bonus, 0.18 * source_factor)
                    elif pref == "鸭脖卤味":
                        intent_bonus = max(intent_bonus, 0.20 * source_factor)
                    elif pref == "烧烤烤肉":
                        intent_bonus = max(intent_bonus, 0.18 * source_factor)
                    elif pref == "炸鸡炸串":
                        intent_bonus = max(intent_bonus, 0.17 * source_factor)
                    else:
                        intent_bonus = max(intent_bonus, 0.12 * source_factor)

        # 子类型精确度：如用户选“鸭脖卤味”时，鸭货卤味要明显高于“鸭头饭/鸡腿堡”
        subtype_bonus = 0.0
        if answers.cuisine_preference and "鸭脖卤味" in answers.cuisine_preference:
            subtype_text = f"{d.name or ''} {d.description or ''}"
            duck_hits = sum(1 for k in DUCK_BRAISE_KEYWORDS if k in subtype_text)
            main_meal_hits = sum(1 for k in MAIN_MEAL_SHAPE_KEYWORDS if k in subtype_text)
            subtype_bonus += min(0.35, duck_hits * 0.12)
            subtype_bonus -= min(0.45, main_meal_hits * 0.15)
            if duck_hits == 0 and d.cuisine in {"特色小吃", "快餐便当"}:
                subtype_bonus -= 0.12
            subtype_bonus = max(-0.50, min(0.40, subtype_bonus))

        # 用餐形态软兼容度
        dining_form_score = 1.0
        form = answers.dining_form
        if form == "快餐简餐" and d.cuisine in FAST_FOOD_CUISINES:
            dining_form_score = 1.10
        elif form == "轻食":
            text_for_form = f"{d.name or ''} {d.description or ''} {d.cuisine or ''} {' '.join(d.taste_tags or [])}"
            light_hit = sum(1 for k in LIGHT_FOOD_KEYWORDS if k in text_for_form)
            heavy_hit = sum(1 for k in HEAVY_FOOD_KEYWORDS if k in text_for_form)

            # 基础惩罚：轻食下重口味菜系明显降权
            if d.cuisine in LIGHT_FOOD_PENALTY_CUISINES:
                dining_form_score -= 0.35
            if d.cuisine in {"快餐便当", "特色小吃"}:
                dining_form_score -= 0.15

            # 关键词加减分
            dining_form_score += min(0.28, light_hit * 0.08)
            dining_form_score -= min(0.45, heavy_hit * 0.09)

            # 口味标签信号
            if d.taste_tags and ("清淡" in d.taste_tags or "蒸" in d.taste_tags):
                dining_form_score += 0.12
            if d.taste_tags and (d.taste_tags and any(t in TASTE_TAG_SPICY for t in d.taste_tags)):
                dining_form_score -= 0.12

            dining_form_score = max(0.25, min(1.35, dining_form_score))

        # 口味兼容度：用户口味强度偏好与菜品标签的匹配
        taste_compat = 1.0
        spicy_level = answers.spicy_level
        numbing_level = answers.numbing_level
        oily_level = answers.oily_level
        dish_tags = set(d.taste_tags or [])
        if spicy_level is not None and spicy_level >= 3 and not (dish_tags & TASTE_TAG_SPICY):
            taste_compat -= 0.25
        if numbing_level is not None and numbing_level >= 3 and "麻" not in dish_tags:
            taste_compat -= 0.20
        if oily_level is not None and oily_level >= 4 and not (dish_tags & {"炸", "烤", "煎", "油", "红烧", "芝士"}):
            taste_compat -= 0.15
        if spicy_level is not None and spicy_level <= 1 and (dish_tags & TASTE_TAG_SPICY):
            taste_compat -= 0.25
        if oily_level is not None and spicy_level is not None and oily_level <= 1 and spicy_level <= 1:
            if not (dish_tags & TASTE_TAG_LIGHT):
                taste_compat -= 0.20
            if dish_tags & TASTE_TAG_HEAVY:
                taste_compat -= 0.25
        if form == "轻食" and dish_tags and (dish_tags & TASTE_TAG_HEAVY):
            taste_compat -= 0.20
        taste_compat = max(0.1, taste_compat)

        # 用餐语境兼容度：午/晚餐 + 填饱类目标时，饮品不应排太前
        meal_context_score = 1.0
        dish_text = f"{d.name or ''} {d.description or ''} {d.cuisine or ''}"
        is_beverage = (d.cuisine in BEVERAGE_CUISINES) or any(k in dish_text for k in BEVERAGE_KEYWORDS)
        is_staple = any(k in dish_text for k in STAPLE_KEYWORDS) and not is_beverage

        if answers.dining_form != "甜品/饮品" and is_beverage:
            meal_context_score -= 0.45
        if answers.meal_time in {"午餐", "晚餐"} and is_beverage:
            meal_context_score -= 0.20
        if answers.dining_goal in {"简单填饱肚子", "日常家常餐"} and not is_staple:
            meal_context_score -= 0.20
        if answers.dining_form in {"正餐主食", "快餐简餐"} and is_beverage:
            meal_context_score -= 0.15

        meal_context_score = max(0.1, min(1.2, meal_context_score))

        # 忌口/限制兼容度：将用户画像中的“不吃辣/不吃油腻”等限制显式纳入重排
        avoid_score = 1.0
        profile_avoids = profile.avoid_foods if profile and profile.avoid_foods else []
        if profile_avoids:
            avoid_set = {str(a).strip() for a in profile_avoids if str(a).strip()}
            dish_text_full = f"{d.name or ''} {d.description or ''} {d.cuisine or ''} {' '.join(d.taste_tags or [])}"
            is_spicy_dish = bool((dish_tags & TASTE_TAG_SPICY) or any(k in dish_text_full for k in SPICY_TEXT_KEYWORDS))
            is_oily_dish = bool((dish_tags & TASTE_TAG_HEAVY) or any(k in dish_text_full for k in OILY_TEXT_KEYWORDS))

            if "不吃辣" in avoid_set and is_spicy_dish:
                avoid_score -= 0.70
            if "不吃油腻" in avoid_set and is_oily_dish:
                avoid_score -= 0.55
            if "素食" in avoid_set and any(k in dish_text_full for k in ["牛", "猪", "鸡", "鸭", "鱼", "虾", "羊", "肉"]):
                avoid_score -= 0.80

        avoid_score = max(0.05, min(1.1, avoid_score))

        # 画像口味兼容度：在中性问卷下，保证用户画像可显著影响排序
        profile_taste_score = 0.5
        if profile and profile.taste_preferences and dish_tags:
            matched_pref = []
            for t in dish_tags:
                if t in profile.taste_preferences:
                    try:
                        pref_v = float(profile.taste_preferences.get(t, 2.5))
                    except Exception:
                        pref_v = 2.5
                    pref_v = max(0.0, min(5.0, pref_v))
                    matched_pref.append(pref_v / 5.0)
            if matched_pref:
                profile_taste_score = sum(matched_pref) / len(matched_pref)
            else:
                profile_taste_score = 0.45

        # 夜宵/小吃场景兼容度：鼓励串烤卤味，抑制“主食套餐/整鸡/饮品”霸榜
        snack_scene_score = 1.0
        if answers.dining_form == "小吃点心" or answers.meal_time == "夜宵" or answers.dining_goal == "解馋/满足欲望":
            snack_text = f"{d.name or ''} {d.description or ''} {d.cuisine or ''} {d.shop.name if d.shop else ''}"
            pos_hits = sum(1 for k in SNACK_POSITIVE_KEYWORDS if k in snack_text)
            neg_hits = sum(1 for k in SNACK_NEGATIVE_KEYWORDS if k in snack_text)
            snack_scene_score += min(0.35, pos_hits * 0.10)
            snack_scene_score -= min(0.45, neg_hits * 0.12)

            # 小吃点心场景下，含“米饭/便当/盖饭/披萨”等主食形态额外降权
            if answers.dining_form == "小吃点心" and any(k in snack_text for k in ["米饭", "便当", "盖饭", "炒饭", "披萨"]):
                snack_scene_score -= 0.20

        snack_scene_score = max(0.1, min(1.35, snack_scene_score))

        # 预算匹配度（越接近预算上限越推荐）
        budget_score = 1.0
        if answers.budget and d.price is not None:
            budget_ranges = [BUDGET_RANGE.get(b, (0, 99999)) for b in answers.budget]
            min_price = min(r[0] for r in budget_ranges)
            max_price = max(r[1] for r in budget_ranges)
            price_value = float(d.price)
            if min_price <= price_value <= max_price:
                # 价格越接近预算中位数，得分越高
                budget_mid = (min_price + max_price) / 2
                max_price_value = max(float(max_price), 1.0)
                budget_score = max(0.5, 1.0 - abs(price_value - budget_mid) / max_price_value)

        # 综合得分
        final = (0.16 * sim_score +           # 语义相似度
                0.07 * dist_penalty +         # 距离
                0.12 * cuisine_bonus +        # 问卷菜系精细匹配
                0.08 * profile_cuisine_bonus +# 画像菜系补偿（问卷未选菜系时）
                0.08 * intent_bonus +         # 菜名/描述意图命中
                0.11 * taste_compat +         # 当前问卷口味兼容度
                0.09 * dining_form_score +    # 用餐形态兼容度
                0.08 * meal_context_score +   # 用餐语境兼容度
                0.12 * avoid_score +          # 画像忌口/限制兼容度
                0.06 * snack_scene_score +    # 夜宵小吃场景兼容度
                0.06 * subtype_bonus +        # 子类型精确度（鸭脖卤味等）
                0.10 * profile_taste_score +  # 用户画像口味兼容度
                0.04 * history_affinity +     # 历史偏好匹配
                0.01 * history_score +        # 历史去重
                0.02 * budget_score)          # 预算匹配

        scored.append((d, final, dist))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_n = _select_diverse_top_n(scored, answers, top_n=20)

    items = [
        RecommendationItem(
            dish_id=d.id,
            dish_name=d.name,
            shop_name=d.shop.name if d.shop else None,
            price=float(d.price) if d.price else None,
            score=round(min(score, 1.0), 4),
            distance_km=round(dist, 2),
            image_url=d.image_urls[0] if d.image_urls else None,
            cuisine=d.cuisine,
            taste_tags=d.taste_tags,
            description=d.description,
        )
        for d, score, dist in top_n
    ]

    # 构建问答快照
    question_snapshot = answers.model_dump()

    log = InteractionLog(
        user_id=user.id,
        recommendation_batch_id=batch_id,
        recommended_dishes=[d.id for d, _, _ in top_n],
        interaction_timestamp=datetime.utcnow(),
        question_snapshot=question_snapshot,
        result=None,
    )
    db.add(log)
    db.commit()

    return RecommendationResponse(batch_id=batch_id, items=items)


def _build_user_vector(answers: QuestionnaireAnswers, profile: UserProfile,
                      hist_cuisines: Dict[str, float] = None,
                      hist_tastes: Dict[str, float] = None) -> np.ndarray:
    """构建用户画像向量（与菜品向量同构文本编码）"""
    answers_dict = answers.model_dump()
    tastes = profile.taste_preferences if profile and profile.taste_preferences else None
    cuisines = profile.cuisine_preferences if profile and profile.cuisine_preferences else None
    avoids = profile.avoid_foods if profile and profile.avoid_foods else None

    vector = generate_user_vector(
        taste_preferences=tastes,
        cuisine_preferences=cuisines,
        avoid_foods=avoids,
        answers=answers_dict,
        historical_cuisines=hist_cuisines,
        historical_tastes=hist_tastes,
    )
    arr = np.array(vector, dtype=np.float32)
    return arr / np.linalg.norm(arr) if np.linalg.norm(arr) > 0 else arr


# ---------- 3. 用户确认选择 ----------
@router.post("/confirm")
def confirm_selection(
    body: SelectionConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dish = db.query(Dish).filter(Dish.id == body.selected_dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")

    log = db.query(InteractionLog).filter(
        InteractionLog.recommendation_batch_id == body.batch_id,
        InteractionLog.user_id == user.id,
    ).first()

    is_first = False
    if log and log.recommended_dishes:
        is_first = log.recommended_dishes[0] == body.selected_dish_id
        log.clicked_dish_id = body.selected_dish_id
        log.result = True

    instant_weights = None
    if body.question_snapshot and isinstance(body.question_snapshot, dict):
        instant_weights = body.question_snapshot.get('instant_weights')

    record = HistoryRecord(
        user_id=user.id,
        recommendation_batch_id=body.batch_id,
        selected_dish_id=body.selected_dish_id,
        dining_time=datetime.utcnow(),
        question_snapshot=body.question_snapshot,
        instant_profile_vector=instant_weights,
        recommended_top_n=log.recommended_dishes if log else None,
        is_first_recommendation=is_first,
    )
    db.add(record)
    db.commit()
    return {"message": "选择已记录", "dish_name": dish.name}


# ---------- 4. 记录交互日志 ----------
@router.post("/interaction")
def log_interaction(
    body: InteractionLogCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log = InteractionLog(
        user_id=user.id,
        recommendation_batch_id=body.recommendation_batch_id,
        clicked_dish_id=body.clicked_dish_id,
        interaction_timestamp=datetime.utcnow(),
        result=body.result,
    )
    db.add(log)
    db.commit()
    return {"message": "交互已记录"}


# ---------- 5. 附近美食 ----------
@router.get("/nearby", response_model=List[RecommendationItem])
def get_nearby_dishes(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 30,
    skip: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dishes = db.query(Dish).filter(Dish.is_approved == True).all()
    rows = []
    for d in dishes:
        if d.latitude is None or d.longitude is None:
            continue
        dist = haversine_km(latitude, longitude, d.latitude, d.longitude)
        if dist <= radius_km:
            rows.append((d, dist))

    rows.sort(key=lambda x: x[1])
    rows = rows[skip: skip + limit]
    return [
        RecommendationItem(
            dish_id=d.id,
            dish_name=d.name,
            shop_name=d.shop.name if d.shop else None,
            price=float(d.price) if d.price is not None else None,
            score=0.0,
            distance_km=round(dist, 2),
            image_url=d.image_urls[0] if d.image_urls else None,
            cuisine=d.cuisine,
            taste_tags=d.taste_tags,
            description=d.description,
        )
        for d, dist in rows
    ]


@router.get("/nearby-shops")
def get_nearby_shops(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    limit: int = 30,
    skip: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from models import Shop
    shops = db.query(Shop).filter(Shop.is_approved == True).all()
    rows = []
    for shop in shops:
        if shop.latitude is None or shop.longitude is None:
            continue
        dist = haversine_km(latitude, longitude, shop.latitude, shop.longitude)
        if dist <= radius_km:
            dish_count = db.query(Dish).filter(Dish.shop_id == shop.id, Dish.is_approved == True).count()
            rows.append((shop, dist, dish_count))

    rows.sort(key=lambda x: x[1])
    rows = rows[skip: skip + limit]
    return [
        {
            "shop_id": shop.id,
            "shop_name": shop.name,
            "address": shop.address,
            "distance_km": round(dist, 2),
            "dish_count": dish_count,
            "image_url": None,
        }
        for shop, dist, dish_count in rows
    ]


@router.get("/shop/{shop_id}/dishes")
def get_shop_dishes(
    shop_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from models import Shop
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="商家不存在")
    
    dishes = db.query(Dish).filter(Dish.shop_id == shop_id, Dish.is_approved == True).all()
    return {
        "shop_id": shop.id,
        "shop_name": shop.name,
        "address": shop.address,
        "dishes": [
            {
                "dish_id": d.id,
                "dish_name": d.name,
                "price": float(d.price) if d.price is not None else None,
                "cuisine": d.cuisine,
                "taste_tags": d.taste_tags,
                "description": d.description,
                "image_url": d.image_urls[0] if d.image_urls else None,
            }
            for d in dishes
        ]
    }


def _compute_form_similarity(current: dict, historical: dict) -> float:
    """计算当前问卷与历史问卷的相似度 (0~1)，决定历史选择的参考权重"""
    score = 0.0
    total = 0.0

    # 1. 用餐时段匹配 (权重 1)
    total += 1.0
    if current.get('meal_time') == historical.get('meal_time'):
        score += 1.0

    # 2. 场景匹配 (权重 1.5)
    total += 1.5
    cur_scene = current.get('dining_scene', '')
    hist_scene = historical.get('dining_scene', '')
    if cur_scene == hist_scene:
        score += 1.5
    elif ('单人' in cur_scene and '单人' in hist_scene) or \
         ('多人' in cur_scene and '多人' in hist_scene) or \
         ('家庭' in cur_scene and '家庭' in hist_scene):
        score += 0.75

    # 3. 用餐目标匹配 (权重 1)
    total += 1.0
    if current.get('dining_goal') == historical.get('dining_goal'):
        score += 1.0

    # 4. 决策偏好匹配 (权重 0.5)
    total += 0.5
    if current.get('decision_style') == historical.get('decision_style'):
        score += 0.5

    # 5. 用餐形态匹配 (权重 1)
    total += 1.0
    if current.get('dining_form') == historical.get('dining_form'):
        score += 1.0

    # 6. 预算重叠 (Jaccard, 权重 1)
    cur_budget = set(current.get('budget') or [])
    hist_budget = set(historical.get('budget') or [])
    if cur_budget or hist_budget:
        total += 1.0
        if cur_budget and hist_budget:
            overlap = len(cur_budget & hist_budget)
            union = len(cur_budget | hist_budget)
            score += overlap / union if union > 0 else 0

    # 7. 菜系偏好重叠 (Jaccard, 权重 1)
    cur_cuisine = set(current.get('cuisine_preference') or [])
    hist_cuisine = set(historical.get('cuisine_preference') or [])
    if cur_cuisine or hist_cuisine:
        total += 1.0
        if cur_cuisine and hist_cuisine:
            overlap = len(cur_cuisine & hist_cuisine)
            union = len(cur_cuisine | hist_cuisine)
            score += overlap / union if union > 0 else 0

    # 8. 口味强度余弦相似度 (权重 2.5，口味是核心维度)
    taste_keys = ['spicy_level', 'numbing_level', 'sour_level', 'sweet_level', 'salty_level', 'oily_level']
    cur_vec = []
    hist_vec = []
    for k in taste_keys:
        cv = current.get(k)
        hv = historical.get(k)
        cur_vec.append(float(cv) if cv is not None else 0.0)
        hist_vec.append(float(hv) if hv is not None else 0.0)
    dot = sum(a * b for a, b in zip(cur_vec, hist_vec))
    norm1 = sum(a * a for a in cur_vec) ** 0.5
    norm2 = sum(b * b for b in hist_vec) ** 0.5
    cos_sim = dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
    total += 2.5
    score += 2.5 * max(0, cos_sim)

    return score / total if total > 0 else 0.0


def _normalize_dish_name(name: str) -> str:
    if not name:
        return ""
    v = name
    v = re.sub(r"（[^）]*）", "", v)
    v = re.sub(r"\([^)]*\)", "", v)
    v = re.sub(r"\+.*$", "", v)
    v = re.sub(r"\s+", "", v)
    return v.strip().lower()


def _select_diverse_top_n(scored: List[tuple], answers: QuestionnaireAnswers, top_n: int = 20) -> List[tuple]:
    """在高分基础上做轻量多样化：覆盖已选菜系、限制同店铺刷屏、去重近似菜名。"""
    if not scored:
        return []

    result: List[tuple] = []
    used_ids = set()
    shop_count: Dict[int, int] = {}
    seen_name_shop = set()

    per_shop_cap = 2

    def can_add(dish) -> bool:
        if dish.id in used_ids:
            return False
        if dish.shop_id is not None and shop_count.get(dish.shop_id, 0) >= per_shop_cap:
            return False
        key = (dish.shop_id, _normalize_dish_name(dish.name or ""))
        if key in seen_name_shop:
            return False
        return True

    def add_item(item: tuple):
        d, _, _ = item
        used_ids.add(d.id)
        if d.shop_id is not None:
            shop_count[d.shop_id] = shop_count.get(d.shop_id, 0) + 1
        seen_name_shop.add((d.shop_id, _normalize_dish_name(d.name or "")))
        result.append(item)

    # 第一轮：若用户选了菜系，优先覆盖每个已选菜系，避免单一菜系霸榜
    selected_cuisines = list(answers.cuisine_preference or [])
    for cuisine in selected_cuisines:
        for item in scored:
            d, _, _ = item
            if d.cuisine == cuisine and can_add(d):
                add_item(item)
                break
        if len(result) >= top_n:
            return result[:top_n]

    # 第二轮：按分数补齐，应用轻量去重与店铺上限
    for item in scored:
        d, _, _ = item
        if can_add(d):
            add_item(item)
        if len(result) >= top_n:
            break

    return result[:top_n]


def _get_user_history_prefs(user_id: str, db: Session, current_answers: dict, days: int = 30):
    """提取用户历史偏好，每条历史按当前问卷相似度加权（越相似权重越高）"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    records = (
        db.query(HistoryRecord)
        .filter(
            HistoryRecord.user_id == user_id,
            HistoryRecord.dining_time >= cutoff,
        )
        .all()
    )
    cuisines: Dict[str, float] = {}
    tastes: Dict[str, float] = {}

    for r in records:
        if not r.selected_dish_id or not r.question_snapshot:
            continue
        dish = db.query(Dish).filter(Dish.id == r.selected_dish_id).first()
        if not dish:
            continue

        form_sim = _compute_form_similarity(current_answers, r.question_snapshot)
        if form_sim < 0.15:
            continue

        weight = form_sim
        if dish.cuisine:
            cuisines[dish.cuisine] = cuisines.get(dish.cuisine, 0.0) + weight
        if dish.taste_tags:
            for t in dish.taste_tags:
                tastes[t] = tastes.get(t, 0.0) + weight

    return cuisines, tastes


def _batch_history_counts(user_id: str, dish_ids: list, db: Session) -> Dict[int, int]:
    """批量查询最近7天内各菜品的历史选择次数"""
    if not dish_ids:
        return {}
    week_ago = datetime.utcnow() - timedelta(days=7)
    rows = (
        db.query(HistoryRecord.selected_dish_id, func.count(HistoryRecord.id))
        .filter(
            HistoryRecord.user_id == user_id,
            HistoryRecord.selected_dish_id.in_(dish_ids),
            HistoryRecord.dining_time >= week_ago,
        )
        .group_by(HistoryRecord.selected_dish_id)
        .all()
    )
    return {dish_id: cnt for dish_id, cnt in rows}
