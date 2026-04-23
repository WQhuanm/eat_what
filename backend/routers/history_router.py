from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from database import get_db
from models import User, HistoryRecord, Dish
from schemas import HistoryRecordOut
from utils import get_current_user

router = APIRouter(prefix="/api/history", tags=["历史记录"])


@router.get("/", response_model=List[HistoryRecordOut])
def get_history(
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(HistoryRecord)
        .options(joinedload(HistoryRecord.dish))
        .filter(HistoryRecord.user_id == user.id)
        .order_by(HistoryRecord.dining_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    result = []
    for r in records:
        out = HistoryRecordOut.model_validate(r)
        if r.dish:
            out.dish_name = r.dish.name
            out.price = float(r.dish.price) if r.dish.price is not None else None
            out.city = r.dish.city
            out.cuisine = r.dish.cuisine
            out.taste_tags = r.dish.taste_tags
            out.description = r.dish.description
            out.image_url = (r.dish.image_urls or [None])[0]
            if r.dish.shop:
                out.shop_name = r.dish.shop.name
        result.append(out)
    return result


@router.get("/{record_id}", response_model=HistoryRecordOut)
def get_history_detail(
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(HistoryRecord)
        .options(joinedload(HistoryRecord.dish))
        .filter(HistoryRecord.id == record_id, HistoryRecord.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    out = HistoryRecordOut.model_validate(record)
    if record.dish:
        out.dish_name = record.dish.name
        out.price = float(record.dish.price) if record.dish.price is not None else None
        out.city = record.dish.city
        out.cuisine = record.dish.cuisine
        out.taste_tags = record.dish.taste_tags
        out.description = record.dish.description
        out.image_url = (record.dish.image_urls or [None])[0]
        if record.dish.shop:
            out.shop_name = record.dish.shop.name
    return out
