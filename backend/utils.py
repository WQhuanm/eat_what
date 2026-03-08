from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
import math, os, uuid

# ========== 密码 ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ========== JWT ==========
SECRET_KEY = os.getenv("SECRET_KEY", "eat-what-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效凭证")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效凭证")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.account_status != "正常":
        raise HTTPException(status_code=403, detail="账号已封禁")
    return user

# ========== 工具 ==========
def gen_uuid() -> str:
    return str(uuid.uuid4())

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点间距离(km)"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ========== 问答权重映射 ==========
TASTE_WEIGHT_MAP = {
    "清爽解腻": {"咸": -0.3, "辣": -0.5, "酸": 0.4, "清淡": 0.8},
    "麻辣刺激": {"辣": 0.9, "咸": 0.3},
    "酸甜开胃": {"酸": 0.7, "甜": 0.6},
    "浓郁咸香": {"咸": 0.8, "甜": -0.2},
}

BUDGET_RANGE = {
    "20元以下": (0, 20),
    "20-50元": (20, 50),
    "50-100元": (50, 100),
    "100元以上": (100, 99999),
}
