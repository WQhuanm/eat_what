from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserProfile
from schemas import UserProfileCreate, UserProfileOut
from utils import get_current_user

router = APIRouter(prefix="/api/profile", tags=["用户画像"])


@router.get("/", response_model=UserProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="尚未创建画像")
    return profile


@router.post("/", response_model=UserProfileOut)
def create_profile(body: UserProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="画像已存在，请使用PUT更新")
    profile = UserProfile(user_id=user.id, **body.model_dump(exclude_none=True))
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/", response_model=UserProfileOut)
def update_profile(body: UserProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="尚未创建画像")
    # 使用 exclude_unset 而非 exclude_none，允许用户显式传空值来清空字段
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(profile, key, val)
    db.commit()
    db.refresh(profile)
    return profile
