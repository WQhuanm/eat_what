from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Dish, Shop, User
from schemas import DishCreate, DishOut, ShopCreate, ShopOut
from utils import get_current_user
from vectorize import generate_dish_vector
from nlp_engine import ModelUnavailableError

router = APIRouter(prefix="/api", tags=["菜品管理"])


# ========== 店铺（独立前缀，避免与 dish_id 冲突） ==========
@router.post("/shops", response_model=ShopOut)
def create_shop(body: ShopCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    shop = Shop(**body.model_dump(exclude_none=True))
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


@router.get("/shops", response_model=List[ShopOut])
def list_shops(city: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Shop)
    if city:
        q = q.filter(Shop.city == city)
    return q.all()


# ========== 菜品 ==========
@router.get("/dishes", response_model=List[DishOut])
def list_dishes(
    city: Optional[str] = None,
    cuisine: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Dish)
    if city:
        q = q.filter(Dish.city == city)
    if cuisine:
        q = q.filter(Dish.cuisine == cuisine)
    if min_price is not None:
        q = q.filter(Dish.price >= min_price)
    if max_price is not None:
        q = q.filter(Dish.price <= max_price)
    return q.offset(skip).limit(limit).all()


@router.post("/dishes", response_model=DishOut)
def create_dish(body: DishCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dish = Dish(**body.model_dump(exclude_none=True))

    # 调用 NLP 模型生成菜品向量
    shop_name = None
    if dish.shop_id:
        shop = db.query(Shop).filter(Shop.id == dish.shop_id).first()
        shop_name = shop.name if shop else None

    try:
        dish.vector = generate_dish_vector(
            name=dish.name,
            cuisine=dish.cuisine,
            taste_tags=dish.taste_tags,
            description=dish.description,
            ingredients=dish.ingredients,
            city=dish.city,
            latitude=dish.latitude,
            longitude=dish.longitude,
            shop_name=shop_name,
        )
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(dish)
    db.commit()
    db.refresh(dish)
    return dish

@router.get("/dishes/{dish_id}", response_model=DishOut)
def get_dish(dish_id: int, db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")
    return dish


@router.delete("/dishes/{dish_id}")
def delete_dish(dish_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")
    db.delete(dish)
    db.commit()
    return {"message": "删除成功"}


@router.put("/dishes/{dish_id}/approve", response_model=dict)
def approve_dish(dish_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.name != "管理员":
        raise HTTPException(status_code=403, detail="无权限")
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    if not dish:
        raise HTTPException(status_code=404, detail="菜品不存在")
    dish.is_approved = True
    db.commit()
    return {"message": "菜品已审核通过"}


@router.put("/shops/{shop_id}/approve", response_model=dict)
def approve_shop(shop_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role.name != "管理员":
        raise HTTPException(status_code=403, detail="无权限")
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="店铺不存在")
    shop.is_approved = True
    db.commit()
    return {"message": "店铺已审核通过"}
