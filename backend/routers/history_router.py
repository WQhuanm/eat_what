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
        out.dish_name = r.dish.name if r.dish else None
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
    out.dish_name = record.dish.name if record.dish else None
    return out
