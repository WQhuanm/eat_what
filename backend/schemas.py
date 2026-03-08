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
    dietary_restrictions: Optional[List[str]] = None
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
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cuisine: Optional[str] = None
    taste_tags: Optional[List[str]] = None
    price: Optional[float] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    carbohydrate: Optional[float] = None
    ingredients: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    description: Optional[str] = None
    dining_forms: Optional[List[str]] = None

class DishOut(DishCreate):
    id: int
    vector: Optional[List[float]] = None
    class Config:
        from_attributes = True


# ========== Questionnaire (问答引导) ==========
class QuestionOption(BaseModel):
    question_key: str
    question_text: str
    options: List[str]
    multi_select: bool = False

class QuestionnaireAnswers(BaseModel):
    meal_time: str          # 早餐/午餐/晚餐/夜宵/下午茶
    taste_preference: List[str]  # 清爽解腻/麻辣刺激/酸甜开胃/浓郁咸香
    dining_scene: str       # 单人简餐/双人约会/团建聚餐/家庭聚餐
    dining_form: str        # 外卖配送/到店堂食/打包带走
    budget: str             # 20元以下/20-50元/50-100元/100元以上
    special_state: Optional[str] = None  # 需要解压/正在减脂/胃不舒服
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
