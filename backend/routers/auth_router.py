from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User
from schemas import UserRegister, UserLogin, TokenResponse
from utils import hash_password, verify_password, create_access_token, gen_uuid

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=dict)
def register(body: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        id=gen_uuid(),
        username=body.username,
        password_hash=hash_password(body.password),
        registration_time=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    return {"message": "注册成功", "user_id": user.id}


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id)
    is_admin = user.role.name == "管理员" if user.role else False  # 确保正确判断管理员角色
    return TokenResponse(access_token=token, username=user.username, is_admin=is_admin)
