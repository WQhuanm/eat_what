from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime, DECIMAL, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    registration_time = Column(DateTime, nullable=False)
    account_status = Column(String(10), default='正常')  # 正常/封禁
    role_id = Column(Integer, ForeignKey('roles.id'))

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    history_records = relationship("HistoryRecord", back_populates="user")
    interaction_logs = relationship("InteractionLog", back_populates="user")
    role = relationship("Role", back_populates="users")


class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, unique=True)
    age = Column(Integer)
    gender = Column(Integer)  # 0: 女, 1: 男
    height = Column(Float)   # cm
    weight = Column(Float)   # kg
    activity_factor = Column(Float)  # 1.2/1.375/1.55/1.725
    health_goal = Column(String(20))  # 减脂/增肌/维持现状/养生饮食
    dietary_restrictions = Column(JSON)  # ["清真","纯素食","蛋奶素食","花生","海鲜","乳糖","麸质"]
    taste_preferences = Column(JSON)  # {"酸":3,"甜":4,"苦":1,"辣":5,"咸":2}
    cuisine_preferences = Column(JSON)  # ["川湘菜","江浙菜","日韩料理","西餐","快餐便当"]
    avoid_foods = Column(JSON)  # ["香菜","葱","蒜","姜","动物内脏"]

    user = relationship("User", back_populates="profile")


class Shop(Base):
    __tablename__ = 'shops'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255))
    source_url = Column(Text)
    source_shop_id = Column(String(64), unique=True, index=True)
    city = Column(String(50), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    contact = Column(String(50))
    is_approved = Column(Boolean, default=False)  # 是否通过审核

    dishes = relationship("Dish", back_populates="shop")


class Dish(Base):
    __tablename__ = 'dishes'
    __table_args__ = (
        UniqueConstraint('shop_id', 'name', 'price', name='uq_dish_shop_name_price'),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    shop_id = Column(Integer, ForeignKey('shops.id'))
    city = Column(String(50), index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    cuisine = Column(String(50))  # 菜系
    taste_tags = Column(JSON)     # ["酸","辣"]
    price = Column(DECIMAL(10, 2))
    calories = Column(Float)      # kcal
    protein = Column(Float)       # g
    fat = Column(Float)           # g
    carbohydrate = Column(Float)  # g
    ingredients = Column(JSON)    # ["猪肉","辣椒","大蒜"]
    image_urls = Column(JSON)     # 宣传图片URL列表
    description = Column(Text)    # 口味描述
    dining_forms = Column(JSON)   # ["外卖配送","到店堂食","打包带走"]
    vector = Column(JSON)         # 768维菜品嵌入向量
    is_approved = Column(Boolean, default=False)  # 是否通过审核

    shop = relationship("Shop", back_populates="dishes")


class HistoryRecord(Base):
    __tablename__ = 'history_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    recommendation_batch_id = Column(String(36), index=True)
    selected_dish_id = Column(Integer, ForeignKey('dishes.id'))
    dining_time = Column(DateTime)
    question_snapshot = Column(JSON)  # 即时问答快照
    instant_profile_vector = Column(JSON)  # 即时画像向量
    recommended_top_n = Column(JSON)  # 推荐列表前N项
    is_first_recommendation = Column(Boolean)

    user = relationship("User", back_populates="history_records")
    dish = relationship("Dish")


class InteractionLog(Base):
    __tablename__ = 'interaction_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    recommendation_batch_id = Column(String(36), index=True)
    recommended_dishes = Column(JSON)  # 推荐菜品ID列表
    interaction_timestamp = Column(DateTime)
    clicked_dish_id = Column(Integer)
    result = Column(Boolean)  # 1: 正样本, 0: 负样本
    question_snapshot = Column(JSON)  # 即时问答快照

    user = relationship("User", back_populates="interaction_logs")


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)  # 角色名称，如 "管理员"
    users = relationship("User", back_populates="role")
