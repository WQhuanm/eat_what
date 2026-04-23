from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from database import get_db
from models import User, UserProfile, Dish, HistoryRecord, InteractionLog
from schemas import (
    QuestionOption, QuestionnaireAnswers, RecommendationResponse,
    RecommendationItem, SelectionConfirm, InteractionLogCreate,
)
from utils import get_current_user, gen_uuid, haversine_km, BUDGET_RANGE, TASTE_WEIGHT_MAP
from vectorize import generate_user_vector
from nlp_engine import ModelUnavailableError

router = APIRouter(prefix="/api/recommend", tags=["推荐系统"])


# ---------- 1. 获取问答题目 ----------
@router.get("/questions", response_model=List[QuestionOption])
def get_questions():
    """返回增强版问答题目列表"""
    return [
        QuestionOption(question_key="meal_time", question_text="当前用餐时段", options=["早餐", "午餐", "下午加餐", "晚餐", "夜宵", "凌晨加餐", "随机/非正餐"]),
        QuestionOption(question_key="dining_scene", question_text="用餐人数与场景", options=["单人简餐（快速解决）", "单人精致餐（慢食）", "双人约会/小聚", "朋友小聚（3-5人）", "多人聚餐（6人以上）", "家庭日常用餐", "家庭正式聚餐/宴请"]),
        QuestionOption(question_key="dining_goal", question_text="本次用餐核心目的", options=["简单填饱肚子", "日常家常餐", "享受美味大餐", "解馋/满足欲望", "轻食垫肚子", "解酒/暖胃/安抚肠胃"]),
        QuestionOption(question_key="decision_style", question_text="本次选择偏好", options=["只吃熟悉口味", "愿意尝试新口味", "优先热门爆款", "无所谓，好吃就行"]),
        QuestionOption(question_key="dining_form", question_text="用餐形态", options=["正餐主食", "快餐简餐", "小吃点心", "甜品/奶茶/饮品/冰品", "轻食/代餐/水果/养生"]),
        QuestionOption(question_key="budget", question_text="预算范围", options=["20元以下", "20-50元", "50-100元", "100元以上"]),
        QuestionOption(question_key="taste_preference", question_text="此刻核心口味倾向", options=["重口过瘾", "清淡本味", "酸甜开胃", "鲜香汤粥", "肉食满足", "奶甜香腻", "酱香卤香", "孜然烧烤"]),
        QuestionOption(question_key="cuisine_preference", question_text="意向菜系/品类（最多选2项）", options=["川渝", "湘鄂", "粤菜", "江浙本帮", "闽鲜海鲜", "西北风味", "东北菜", "云贵风味", "家常菜", "日韩料理", "东南亚", "清真", "粉面专属", "煲仔/砂锅"], multi_select=True, question_type="multi"),
        QuestionOption(question_key="ingredient_preference", question_text="核心食材偏好", options=["猪肉类", "牛羊肉类", "鸡鸭禽类", "海鲜/水产/河鲜", "素菜/菌菇/豆制品", "蛋类/奶类", "五谷主食类", "丸子/加工肉制品", "滋补类"]),
        QuestionOption(question_key="avoid_foods", question_text="饮食忌口（可多选）", options=["忌辛辣", "忌麻", "忌葱/蒜/香菜/芹菜", "忌牛羊肉", "忌海鲜水产", "忌甜食", "忌油腻", "忌油炸", "忌蛋奶", "忌生冷", "素食全素", "清真", "无忌口"], multi_select=True, question_type="multi"),
        QuestionOption(question_key="spicy_level", question_text="辣度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="numbing_level", question_text="麻度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="sour_level", question_text="酸度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="sweet_level", question_text="甜度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="salty_level", question_text="咸度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="oily_level", question_text="油度（0-5）", question_type="scale", min_value=0, max_value=5, step=1),
        QuestionOption(question_key="texture_preference", question_text="口感偏好", options=["酥脆焦香", "劲道弹牙", "软烂脱骨", "脆嫩爽口", "软糯绵密", "丝滑细腻", "多汁水嫩", "干香有嚼劲"]),
        QuestionOption(question_key="temperature_preference", question_text="食用温度偏好", options=["冷食/常温", "温凉", "温热", "滚烫热食", "可冰可热无所谓"]),
        QuestionOption(question_key="special_requirements", question_text="特殊场景需求（可选）", question_type="text"),
        QuestionOption(question_key="special_state", question_text="特殊状态（可选）", options=["无", "需要解压", "正在减脂", "胃不舒服"]),
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

    budget_range = BUDGET_RANGE.get(answers.budget, (0, 99999))
    q = q.filter(Dish.price >= budget_range[0], Dish.price <= budget_range[1])

    candidates: List[Dish] = q.all()

    # ----- 向量召回 -----
    try:
        user_vector = _build_user_vector(answers, profile)
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
        special_bonus = _special_state_bonus(answers.special_state, d)
        sim_score = sim_score * 0.8 + special_bonus * 0.2

        dist = haversine_km(latitude, longitude, d.latitude or 0, d.longitude or 0) if latitude else 0
        dist_penalty = max(0, 1 - dist / 10)

        history_counts = _batch_history_counts(user.id, [d.id], db)
        count = history_counts.get(d.id, 0)
        history_score = max(0.1, 1.0 - count * 0.3) if count > 0 else 1.0

        final = 0.6 * sim_score + 0.3 * dist_penalty + 0.1 * history_score
        scored.append((d, final, dist))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_n = scored[:20]

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


def _build_user_vector(answers: QuestionnaireAnswers, profile: UserProfile) -> np.ndarray:
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
    )
    arr = np.array(vector, dtype=np.float32)
    return arr / np.linalg.norm(arr) if np.linalg.norm(arr) > 0 else arr


def _get_vector_index(tag: str) -> int:
    """将标签映射到向量索引"""
    # 假设有一个标签到索引的映射表
    TAG_TO_INDEX = {
        "酸": 0, "甜": 1, "辣": 2, "咸": 3, "清淡": 4,
        # ...其他标签...
    }
    return TAG_TO_INDEX.get(tag, 0)


# ---------- 3. 用户确认选择（"就决定是你了"） ----------
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

    # 提取即时画像权重
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


# ---------- 4. 记录交互日志（负样本等） ----------
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


# ========== 内部辅助函数 ==========
def _has_conflict(restrictions: list, avoid: list, ingredients: list) -> bool:
    if avoid:
        for item in avoid:
            if item in ingredients:
                return True
    meat_keywords = ["猪肉", "牛肉", "鸡肉", "羊肉", "鱼", "虾", "蟹"]
    if restrictions:
        if "纯素食" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in meat_keywords + ["蛋", "奶", "乳"]):
                    return True
        if "蛋奶素食" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in meat_keywords):
                    return True
        if "海鲜" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in ["虾", "蟹", "鱼", "贝", "海"]):
                    return True
        if "花生" in restrictions:
            for ing in ingredients:
                if "花生" in ing:
                    return True
        if "乳糖" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in ["牛奶", "奶", "乳"]):
                    return True
        if "麸质" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in ["面粉", "小麦", "面包", "麸"]):
                    return True
        if "清真" in restrictions:
            for ing in ingredients:
                if any(m in ing for m in ["猪肉", "猪", "火腿", "培根", "猪油"]):
                    return True
    return False


def _tag_similarity(answers: QuestionnaireAnswers, dish: Dish, profile) -> float:
    """基于标签的简单匹配打分 (0~1)，向量召回后续替换"""
    score = 0.0
    total = 0.0

    # 口味匹配
    if dish.taste_tags and answers.taste_preference:
        for pref in answers.taste_preference:
            weights = TASTE_WEIGHT_MAP.get(pref, {})
            for tag in dish.taste_tags:
                if tag in weights:
                    score += max(0, weights[tag])
                    total += 1.0

    # 用户画像口味偏好
    if profile and profile.taste_preferences and dish.taste_tags:
        for tag in dish.taste_tags:
            if tag in profile.taste_preferences:
                score += profile.taste_preferences[tag] / 5.0
                total += 1.0

    # 菜系偏好
    if profile and profile.cuisine_preferences and dish.cuisine:
        if dish.cuisine in profile.cuisine_preferences:
            score += 1.0
        total += 1.0

    return score / total if total > 0 else 0.5


def _special_state_bonus(state: str, dish: Dish) -> float:
    """特殊状态匹配加分"""
    if not state or state == '无':
        return 0.5
    if state == '需要解压':
        bonus = 0.0
        if dish.calories and dish.calories > 400:
            bonus += 0.4
        if dish.taste_tags:
            if '甜' in dish.taste_tags:
                bonus += 0.3
            if any(t in dish.taste_tags for t in ['炸', '烤']):
                bonus += 0.3
        return min(bonus, 1.0)
    if state == '正在减脂':
        if dish.calories and dish.calories < 300:
            return 0.8
        if dish.taste_tags and '清淡' in dish.taste_tags:
            return 0.6
        return 0.2
    if state == '胃不舒服':
        bonus = 0.0
        if dish.taste_tags:
            if '清淡' in dish.taste_tags:
                bonus += 0.4
        if dish.cuisine and any(k in dish.cuisine for k in ['粥', '面', '汤']):
            bonus += 0.4
        if dish.name and any(k in dish.name for k in ['粥', '面', '汤', '蒸']):
            bonus += 0.3
        return min(bonus, 1.0)
    return 0.5


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
