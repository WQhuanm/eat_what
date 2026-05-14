from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# ========== Auth ==========
class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str = ""
    is_admin: bool = False  # 添加管理员标识字段


# ========== UserProfile ==========
class UserProfileCreate(BaseModel):
    age: Optional[int] = None
    gender: Optional[int] = None  # 0女 1男
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_factor: Optional[float] = Field(None, description="1.2/1.375/1.55/1.725")
    health_goal: Optional[str] = None
    taste_preferences: Optional[Dict[str, int]] = None  # {"酸":3,"甜":4,...}
    cuisine_preferences: Optional[List[str]] = None
    avoid_foods: Optional[List[str]] = None

class UserProfileOut(UserProfileCreate):
    id: int
    user_id: str
    class Config:
        from_attributes = True


# ========== Shop ==========
class ShopCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact: Optional[str] = None

class ShopOut(ShopCreate):
    id: int
    class Config:
        from_attributes = True


# ========== Dish ==========
class DishCreate(BaseModel):
    name: str
    shop_id: Optional[int] = None
    cuisine: Optional[str] = None
    taste_tags: Optional[List[str]] = None
    price: Optional[float] = None
    ingredients: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    description: Optional[str] = None

class DishOut(DishCreate):
    id: int
    vector: Optional[List[float]] = None
    class Config:
        from_attributes = True


# ========== Questionnaire (问答引导) ==========
class QuestionOption(BaseModel):
    question_key: str
    question_text: str
    options: List[str] = []
    multi_select: bool = False
    question_type: str = "single"  # single/multi/scale/text/multi_scale
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    step: Optional[int] = None
    required: bool = True
    sub_questions: Optional[List[dict]] = None  # 用于 multi_scale 复合题型

class QuestionnaireAnswers(BaseModel):
    meal_time: str
    dining_scene: str
    dining_goal: str
    decision_style: str
    dining_form: str
    budget: List[str] = []  # 多选预算
    cuisine_preference: List[str] = []
    spicy_level: Optional[int] = None
    numbing_level: Optional[int] = None
    sour_level: Optional[int] = None
    sweet_level: Optional[int] = None
    salty_level: Optional[int] = None
    oily_level: Optional[int] = None
    follow_up_answers: Optional[Dict[str, str]] = None  # 动态追问的回答
    instant_weights: Optional[Dict[str, float]] = None  # 即时画像权重


# ========== Recommendation ==========
class RecommendationItem(BaseModel):
    dish_id: int
    dish_name: str
    shop_name: Optional[str] = None
    price: Optional[float] = None
    score: float
    distance_km: Optional[float] = None
    image_url: Optional[str] = None
    cuisine: Optional[str] = None
    taste_tags: Optional[List[str]] = None
    description: Optional[str] = None

class RecommendationResponse(BaseModel):
    batch_id: str
    items: List[RecommendationItem]


# ========== 用户选择确认 ==========
class SelectionConfirm(BaseModel):
    batch_id: str
    selected_dish_id: int
    question_snapshot: Optional[dict] = None  # 问答快照


# ========== History ==========
class HistoryRecordOut(BaseModel):
    id: int
    selected_dish_id: Optional[int]
    dish_name: Optional[str] = None
    shop_name: Optional[str] = None
    city: Optional[str] = None
    distance_km: Optional[float] = None
    price: Optional[float] = None
    cuisine: Optional[str] = None
    taste_tags: Optional[List[str]] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    dining_time: Optional[datetime]
    question_snapshot: Optional[dict] = None
    is_first_recommendation: Optional[bool] = None
    class Config:
        from_attributes = True


# ========== InteractionLog ==========
class InteractionLogCreate(BaseModel):
    recommendation_batch_id: str
    clicked_dish_id: int
    result: bool  # True=正样本
