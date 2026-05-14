"""
重新向量化数据库中已有菜品（向量化逻辑更新后执行）
用法: python backend/scripts/revectorize_dishes.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models import Dish
from vectorize import generate_dish_vector


def main():
    db = SessionLocal()
    try:
        dishes = db.query(Dish).all()
        total = len(dishes)
        if total == 0:
            print("数据库中没有菜品，跳过。")
            return

        print(f"共 {total} 道菜品，开始重新向量化...")
        success = 0
        failed = 0

        for i, dish in enumerate(dishes):
            try:
                shop_name = dish.shop.name if dish.shop else None
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
                success += 1
            except Exception as e:
                failed += 1
                print(f"  [{i+1}/{total}] 失败: {dish.name} - {e}")

            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{total} (成功 {success}, 失败 {failed})")

        db.commit()
        print(f"\n完成! 成功 {success} 道，失败 {failed} 道。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
