import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from vectorize import generate_dish_vector, infer_taste_scores


CUISINE_KEYWORDS = {
    "烧烤": ["烧烤", "烤", "串", "炭烤", "烤鱼"],
    "川湘菜": ["川", "湘", "麻辣", "水煮", "香辣", "辣子"],
    "粤菜": ["粤", "广式", "烧腊", "早茶"],
    "江浙菜": ["江浙", "本帮", "杭帮", "宁波"],
    "日韩料理": ["日式", "寿司", "刺身", "韩", "泡菜", "石锅"],
    "西餐": ["披萨", "意面", "牛排", "汉堡", "薯条", "沙拉"],
    "快餐便当": ["便当", "套餐", "快餐", "盖饭", "炒饭", "简餐"],
    "火锅": ["火锅", "冒菜", "串串", "麻辣烫"],
    "饮品甜点": ["奶茶", "咖啡", "甜品", "蛋糕", "冰淇淋", "果茶"],
}

TASTE_KEYWORDS = {
    "辣": ["辣", "麻辣", "香辣", "剁椒", "藤椒", "泡椒"],
    "甜": ["甜", "蜜", "糖", "奶油", "可可", "巧克力", "蛋糕", "奶茶", "果茶", "水果", "芒果", "草莓"],
    "酸": ["酸", "柠檬", "醋", "酸菜", "番茄"],
    "咸": ["咸", "酱", "卤", "蚝油", "咸香"],
    "清淡": ["清淡", "原味", "清汤", "蒸", "水煮", "白灼", "养胃"],
}

DETAILED_TASTE_KEYWORDS = {
    "麻辣": ["麻辣", "麻辣烫", "麻辣香锅"],
    "香辣": ["香辣", "红油", "糊辣"],
    "酸辣": ["酸辣", "泡椒", "剁椒"],
    "甜辣": ["甜辣"],
    "藤椒": ["藤椒"],
    "糖醋": ["糖醋"],
    "酸甜": ["酸甜", "荔枝味", "茄汁", "番茄"],
    "咸鲜": ["咸鲜", "鲜香", "鲜"],
    "清淡": ["清淡", "原味", "白灼", "清蒸", "清汤"],
    "酱香": ["酱香", "红烧", "卤", "京酱"],
    "五香": ["五香"],
    "蒜香": ["蒜香", "蒜蓉", "蒜泥"],
    "孜然": ["孜然", "烧烤", "焦香"],
    "咖喱": ["咖喱"],
    "椒盐": ["椒盐"],
    "黑椒": ["黑椒"],
    "奶香": ["奶香", "奶油", "芝士"],
}

BASE_TAG_FROM_DETAIL = {
    "麻辣": ["辣", "咸"],
    "香辣": ["辣", "咸"],
    "酸辣": ["酸", "辣"],
    "甜辣": ["甜", "辣"],
    "藤椒": ["辣", "咸"],
    "糖醋": ["酸", "甜"],
    "酸甜": ["酸", "甜"],
    "咸鲜": ["咸"],
    "清淡": ["清淡"],
    "酱香": ["咸"],
    "五香": ["咸"],
    "蒜香": ["咸"],
    "孜然": ["咸", "辣"],
    "咖喱": ["咸", "辣"],
    "椒盐": ["咸"],
    "黑椒": ["咸", "辣"],
    "奶香": ["甜"],
}

JIANGZHE_DISH_TASTE_PATTERNS = {
    "西湖醋鱼": ["酸", "甜"],
    "东坡肉": ["甜", "咸"],
    "糖醋": ["酸", "甜"],
    "红烧": ["甜", "咸"],
    "油焖": ["甜", "咸"],
    "清蒸": ["清淡", "咸"],
    "白灼": ["清淡", "咸"],
    "葱油": ["咸"],
    "醉": ["咸"],
    "酱鸭": ["甜", "咸"],
    "醉鸡": ["咸"],
    "杭三鲜": ["咸"],
    "腌笃鲜": ["咸", "清淡"],
    "雪菜": ["咸"],
    "梅干菜": ["咸"],
}

CUISINE_TASTE_PRIOR = {
    "川湘菜": ["辣", "咸"],
    "火锅": ["辣", "咸"],
    "烧烤": ["咸", "辣"],
    "粤菜": ["清淡", "甜"],
    "江浙菜": ["甜", "咸"],
    "日韩料理": ["咸", "清淡"],
    "西餐": ["咸"],
    "快餐便当": ["咸"],
    "饮品甜点": ["甜"],
}

NAME_TASTE_PRIOR = {
    "水煮": ["辣", "咸"],
    "麻婆": ["辣", "咸"],
    "香辣": ["辣"],
    "藤椒": ["辣", "麻"],
    "酸菜": ["酸", "咸"],
    "番茄": ["酸", "甜"],
    "金汤": ["酸", "咸"],
    "烤": ["咸"],
    "炸": ["咸"],
    "蒸": ["清淡"],
    "粥": ["清淡"],
    "蛋糕": ["甜"],
    "奶茶": ["甜"],
}

INGREDIENT_KEYWORDS = [
    "鸡肉", "牛肉", "羊肉", "猪肉", "鸭肉", "鱼", "虾", "蟹", "贝", "鱿鱼",
    "鸡蛋", "豆腐", "土豆", "番茄", "洋葱", "青椒", "辣椒", "香菜", "葱", "蒜",
    "米饭", "面条", "粉", "菌菇", "花生", "芝士", "奶油", "牛奶", "酸奶",
]


@dataclass
class DishFeature:
    shop_source_id: str
    shop_name: str
    shop_latitude: Optional[float]
    shop_longitude: Optional[float]
    name: str
    description: str
    category: str
    price: Optional[float]
    month_sales: Optional[int]
    cuisine: Optional[str]
    taste_tags: List[str]
    ingredients: List[str]
    image_url: Optional[str]
    taste_hint: Optional[str]
    taste_detail: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将饿了么抓取菜单转换为可导入数据库的种子文件")
    parser.add_argument("--input", default=str(Path(__file__).resolve().parents[2] / "get_data" / ".generated" / "menus_around.json"), help="抓取菜单 JSON 文件路径")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parents[1] / ".generated" / "eleme_seed_payload.json"), help="输出种子文件路径")
    parser.add_argument("--city", default=None, help="城市（可选，不传则为空）")
    parser.add_argument("--latitude", type=float, default=None, help="默认纬度")
    parser.add_argument("--longitude", type=float, default=None, help="默认经度")
    parser.add_argument("--meta", default=str(Path(__file__).resolve().parents[2] / "get_data" / ".generated" / "menus_meta.json"), help="抓取批次元数据路径")
    parser.add_argument("--vectorizer", choices=["auto", "nlp-service", "local-model"], default="auto", help="向量化方式")
    parser.add_argument("--nlp-url", default="http://nlp-service/v1/vectorize", help="NLP 向量服务地址")
    parser.add_argument("--vector-dim", type=int, default=768, help="向量维度")
    parser.add_argument("--import-db", action="store_true", help="转换后直接写入数据库")
    parser.add_argument("--clear-before-import", action="store_true", help="导入前清空 shops/dishes 表")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def apply_meta_defaults(args: argparse.Namespace) -> argparse.Namespace:
    meta_path = Path(args.meta)
    if not meta_path.exists():
        return args
    try:
        meta = load_json(meta_path)
    except Exception:
        return args

    if args.city is None and isinstance(meta, dict) and meta.get("city"):
        args.city = meta.get("city")
    if args.latitude is None and isinstance(meta, dict):
        args.latitude = meta.get("latitude")
    if args.longitude is None and isinstance(meta, dict):
        args.longitude = meta.get("longitude")
    return args


def normalize_text(value: Optional[str]) -> str:
    return (value or "").strip()


def parse_month_sales(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else None


def detect_cuisine(*texts: str) -> Optional[str]:
    text = " ".join([t for t in texts if t])
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cuisine
    return "快餐便当"


def normalize_taste_hint_to_tags(taste_hint: Optional[str]) -> List[str]:
    if not taste_hint:
        return []
    text = str(taste_hint)
    tags: List[str] = []
    mapping = {
        "酸": ["酸", "酸爽", "酸甜"],
        "甜": ["甜", "奶香", "果香", "香甜"],
        "辣": ["辣", "麻辣", "香辣", "微辣", "中辣", "重辣"],
        "咸": ["咸", "咸香", "鲜香", "鲜"],
        "清淡": ["清淡", "原味", "不辣", "少油"],
    }
    for t, kws in mapping.items():
        if any(k in text for k in kws):
            tags.append(t)
    return tags


def extract_detail_taste_tags(taste_hint: Optional[str], *texts: str) -> List[str]:
    text = " ".join([t for t in [taste_hint, *texts] if t])
    found: List[str] = []
    for tag, kws in DETAILED_TASTE_KEYWORDS.items():
        if any(k in text for k in kws) and tag not in found:
            found.append(tag)
    return found


def detect_taste_tags(cuisine: Optional[str], taste_hint: Optional[str], *texts: str) -> List[str]:
    detail_tags = extract_detail_taste_tags(taste_hint, *texts)
    if detail_tags:
        base_tags: List[str] = []
        for dt in detail_tags:
            for bt in BASE_TAG_FROM_DETAIL.get(dt, []):
                if bt not in base_tags:
                    base_tags.append(bt)
        if base_tags:
            return base_tags

    hint_tags = normalize_taste_hint_to_tags(taste_hint)
    if hint_tags:
        return hint_tags

    text = " ".join([t for t in texts if t])
    tags: List[str] = []
    for tag, keywords in TASTE_KEYWORDS.items():
        if any(k in text for k in keywords):
            tags.append(tag)
    if tags:
        return tags

    # 菜系兜底
    if cuisine == "江浙菜":
        jiangzhe_tags: List[str] = []
        for k, vals in JIANGZHE_DISH_TASTE_PATTERNS.items():
            if k in text:
                for v in vals:
                    if v in ["酸", "甜", "辣", "咸", "清淡"] and v not in jiangzhe_tags:
                        jiangzhe_tags.append(v)
        if jiangzhe_tags:
            return jiangzhe_tags

    if cuisine in CUISINE_TASTE_PRIOR:
        return [t for t in CUISINE_TASTE_PRIOR[cuisine] if t in ["酸", "甜", "辣", "咸", "清淡"]]

    # 菜名模板兜底
    fallback: List[str] = []
    for k, vals in NAME_TASTE_PRIOR.items():
        if k in text:
            for v in vals:
                if v in ["酸", "甜", "辣", "咸", "清淡"] and v not in fallback:
                    fallback.append(v)
    return fallback


def detect_ingredients(*texts: str) -> List[str]:
    text = " ".join([t for t in texts if t])
    return [kw for kw in INGREDIENT_KEYWORDS if kw in text]


def build_features(raw_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[DishFeature]]:
    shops: List[Dict[str, Any]] = []
    dishes: List[DishFeature] = []

    for shop in raw_data:
        shop_name = normalize_text(shop.get("shop_name"))
        source_shop_id = normalize_text(shop.get("shop_id"))
        shop_url = normalize_text(shop.get("shop_url"))
        if not shop_name or not source_shop_id:
            continue

        shops.append(
            {
                "source_shop_id": source_shop_id,
                "name": shop_name,
                "address": normalize_text(shop.get("shop_address")) or None,
                "source_url": shop_url or None,
                "is_approved": True,
                "latitude": shop.get("shop_latitude"),
                "longitude": shop.get("shop_longitude"),
            }
        )

        for menu_item in shop.get("menu", []):
            dish_name = normalize_text(menu_item.get("name"))
            if not dish_name:
                continue
            description = normalize_text(menu_item.get("description"))
            category = normalize_text(menu_item.get("category"))
            cuisine = detect_cuisine(shop_name, category, dish_name, description)
            taste_hint = normalize_text(menu_item.get("taste_hint"))
            taste_detail = extract_detail_taste_tags(taste_hint, category, dish_name, description)
            taste_tags = detect_taste_tags(cuisine, taste_hint, category, dish_name, description)
            ingredients = detect_ingredients(dish_name, description, category)
            raw_price = menu_item.get("price")
            try:
                price = float(raw_price) if raw_price is not None else None
            except (TypeError, ValueError):
                price = None

            dishes.append(
                DishFeature(
                    shop_source_id=source_shop_id,
                    shop_name=shop_name,
                    shop_latitude=shop.get("shop_latitude"),
                    shop_longitude=shop.get("shop_longitude"),
                    name=dish_name,
                    description=description,
                    category=category,
                    price=price,
                    month_sales=parse_month_sales(menu_item.get("month_sales")),
                    cuisine=cuisine,
                    taste_tags=taste_tags,
                    ingredients=ingredients,
                    image_url=normalize_text(menu_item.get("image_url")) or None,
                    taste_hint=taste_hint or None,
                    taste_detail=taste_detail,
                )
            )

    return list({s["source_shop_id"]: s for s in shops}.values()), dishes


def build_vectors(features: List[DishFeature], args: argparse.Namespace) -> Tuple[List[List[float]], str]:
    vectors: List[List[float]] = []
    used = args.vectorizer

    if args.vectorizer == "auto":
        if not features:
            used = "local-model"
        else:
            trial = generate_dish_vector(
                name=features[0].name,
                cuisine=features[0].cuisine,
                taste_tags=features[0].taste_tags,
                description=features[0].description,
                ingredients=features[0].ingredients,
                city=args.city,
                latitude=args.latitude,
                longitude=args.longitude,
                shop_name=features[0].shop_name,
                vectorizer="nlp-service",
                nlp_url=args.nlp_url,
                vector_dim=args.vector_dim,
            )
            used = "nlp-service" if any(abs(x) > 1e-9 for x in trial) else "local-model"

    for feature in features:
        vectors.append(
            generate_dish_vector(
                name=feature.name,
                cuisine=feature.cuisine,
                taste_tags=feature.taste_tags,
                description=feature.description,
                ingredients=feature.ingredients,
                city=args.city,
                latitude=args.latitude,
                longitude=args.longitude,
                shop_name=feature.shop_name,
                vectorizer=used,
                nlp_url=args.nlp_url,
                vector_dim=args.vector_dim,
            )
        )

    return vectors, used


def prepare_payload(args: argparse.Namespace) -> Dict[str, Any]:
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_data = load_json(input_path)
    shops, dish_features = build_features(raw_data)
    vectors, vectorizer_used = build_vectors(dish_features, args)

    dishes_payload: List[Dict[str, Any]] = []
    seen_dish_keys = set()
    for feature, vector in zip(dish_features, vectors):
        dedupe_key = (feature.shop_source_id, feature.name, feature.price)
        if dedupe_key in seen_dish_keys:
            continue
        seen_dish_keys.add(dedupe_key)

        taste_scores = infer_taste_scores(feature.name, feature.description, feature.taste_tags, feature.cuisine)
        dishes_payload.append(
            {
                "shop_source_id": feature.shop_source_id,
                "name": feature.name,
                "city": args.city,
                "latitude": feature.shop_latitude if feature.shop_latitude is not None else args.latitude,
                "longitude": feature.shop_longitude if feature.shop_longitude is not None else args.longitude,
                "cuisine": feature.cuisine,
                "taste_tags": feature.taste_tags,
                "taste_scores": taste_scores,
                "taste_detail": feature.taste_detail,
                "price": feature.price,
                "calories": None,
                "protein": None,
                "fat": None,
                "carbohydrate": None,
                "ingredients": feature.ingredients,
                "image_urls": [feature.image_url] if feature.image_url else [],
                "description": feature.description,
                "taste_hint": feature.taste_hint,
                "dining_forms": ["外卖配送", "打包带走"],
                "vector": vector,
                "is_approved": True,
            }
        )

    for shop in shops:
        shop["city"] = args.city
        shop["latitude"] = shop.get("latitude") if shop.get("latitude") is not None else args.latitude
        shop["longitude"] = shop.get("longitude") if shop.get("longitude") is not None else args.longitude

    payload = {
        "meta": {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": str(input_path),
            "shop_count": len(shops),
            "dish_count": len(dishes_payload),
            "vector_dim": args.vector_dim,
            "vectorizer": vectorizer_used,
        },
        "shops": shops,
        "dishes": dishes_payload,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


def import_payload_to_db(payload: Dict[str, Any], clear_before_import: bool = False) -> Tuple[int, int]:
    from database import SessionLocal
    from models import Dish, Shop

    db = SessionLocal()
    inserted_shops = 0
    inserted_dishes = 0
    try:
        if clear_before_import:
            db.query(Dish).delete(synchronize_session=False)
            db.query(Shop).delete(synchronize_session=False)
            db.flush()

        source_to_shop_id: Dict[str, int] = {}
        for shop_item in payload.get("shops", []):
            source_shop_id = shop_item.get("source_shop_id")
            existing = db.query(Shop).filter(Shop.source_shop_id == source_shop_id).first()
            if existing:
                source_to_shop_id[source_shop_id] = existing.id
                continue
            shop = Shop(
                name=shop_item.get("name"),
                address=shop_item.get("address"),
                source_url=shop_item.get("source_url"),
                source_shop_id=source_shop_id,
                city=shop_item.get("city"),
                latitude=shop_item.get("latitude"),
                longitude=shop_item.get("longitude"),
                contact=None,
                is_approved=bool(shop_item.get("is_approved", True)),
            )
            db.add(shop)
            db.flush()
            source_to_shop_id[source_shop_id] = shop.id
            inserted_shops += 1

        for dish_item in payload.get("dishes", []):
            source_shop_id = dish_item.get("shop_source_id")
            shop_id = source_to_shop_id.get(source_shop_id)
            if not shop_id:
                continue
            exists = db.query(Dish).filter(Dish.shop_id == shop_id, Dish.name == dish_item.get("name"), Dish.price == dish_item.get("price")).first()
            if exists:
                continue
            dish = Dish(
                name=dish_item.get("name"),
                shop_id=shop_id,
                city=dish_item.get("city"),
                latitude=dish_item.get("latitude"),
                longitude=dish_item.get("longitude"),
                cuisine=dish_item.get("cuisine"),
                taste_tags=dish_item.get("taste_tags"),
                price=dish_item.get("price"),
                calories=dish_item.get("calories"),
                protein=dish_item.get("protein"),
                fat=dish_item.get("fat"),
                carbohydrate=dish_item.get("carbohydrate"),
                ingredients=dish_item.get("ingredients"),
                image_urls=dish_item.get("image_urls"),
                description=dish_item.get("description"),
                dining_forms=dish_item.get("dining_forms"),
                vector=dish_item.get("vector"),
                is_approved=bool(dish_item.get("is_approved", True)),
            )
            db.add(dish)
            inserted_dishes += 1

        db.commit()
        return inserted_shops, inserted_dishes
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    args = parse_args()
    args = apply_meta_defaults(args)
    payload = prepare_payload(args)
    print(json.dumps({"status": "ok", "output": args.output, "shop_count": payload["meta"]["shop_count"], "dish_count": payload["meta"]["dish_count"], "vectorizer": payload["meta"]["vectorizer"]}, ensure_ascii=False))
    if args.import_db:
        shops, dishes = import_payload_to_db(payload, clear_before_import=args.clear_before_import)
        print(json.dumps({"db_imported_shops": shops, "db_imported_dishes": dishes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
