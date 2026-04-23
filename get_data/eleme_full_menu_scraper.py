import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Response
from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="自动打开饿了么商家并抓取点餐页完整菜品")
    p.add_argument("--state-file", type=Path, default=Path(".playwright/eleme_state.json"))
    p.add_argument("--limit", type=int, default=10, help="目标商家数")
    p.add_argument("--latitude", type=float, default=None, help="可选：指定纬度；不传则使用页面当前位置")
    p.add_argument("--longitude", type=float, default=None, help="可选：指定经度；不传则使用页面当前位置")
    p.add_argument("--strict-limit", action="store_true", help="若最终商家数小于 limit，则报错退出")
    p.add_argument("--max-dishes-per-shop", type=int, default=0, help="每家最多保留菜品数（0 表示不限制）")
    p.add_argument("--output-json", type=Path, default=Path(".generated/menus_around.json"))
    p.add_argument("--output-csv", type=Path, default=Path(".generated/menus_around.csv"))
    p.add_argument("--output-debug", type=Path, default=Path(".generated/menus_debug.json"))
    p.add_argument("--output-meta", type=Path, default=Path(".generated/menus_meta.json"), help="输出抓取批次元数据")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=30000)
    p.add_argument("--manual-login", action="store_true", help="打开页面后先手动登录，再按回车继续")
    return p.parse_args()


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except Exception:
        return None


def _month_sales_score(raw: Any) -> int:
    if raw is None:
        return -1
    text = str(raw)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return -1
    try:
        return int(digits)
    except Exception:
        return -1


def _pick_top_dishes(dishes: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or len(dishes) <= limit:
        return dishes
    ranked = sorted(
        dishes,
        key=lambda d: (
            _month_sales_score(d.get("month_sales")),
            _safe_float(d.get("price")) or 0.0,
        ),
        reverse=True,
    )
    return ranked[:limit]


def _infer_location_from_results(results: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    for shop in results:
        shop_url = shop.get("shop_url")
        if not isinstance(shop_url, str) or not shop_url:
            continue
        try:
            parsed = urlparse(shop_url)
            qs = parse_qs(parsed.query)
            lat_raw = (qs.get("__locLat") or qs.get("latitude") or [None])[0]
            lng_raw = (qs.get("__locLng") or qs.get("longitude") or [None])[0]
            lat = _safe_float(lat_raw)
            lng = _safe_float(lng_raw)
            if lat is not None and lng is not None:
                return lat, lng
        except Exception:
            continue
    return None, None


def _image_hash_to_url(image_hash: str) -> str:
    lower = image_hash.lower()
    exts = ["jpeg", "jpg", "png", "webp", "gif"]
    ext = None
    for e in exts:
        if lower.endswith(e):
            ext = e
            break

    if len(image_hash) < 4:
        return ""

    dir1 = image_hash[0]
    dir2 = image_hash[1:3]
    stem = image_hash[3:]

    if ext is None:
        filename = stem
    else:
        filename = stem if "." in stem else f"{stem}.{ext}"

    return (
        f"https://cube.elemecdn.com/{dir1}/{dir2}/{filename}"
        "?x-oss-process=image/resize,m_mfit,w_192,h_192/format,webp/quality,q_90"
    )


def _menu_from_body_query(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result_map = payload.get("data", {}).get("resultMap", {})
    menu = result_map.get("menu", {}) if isinstance(result_map, dict) else {}
    groups = menu.get("itemGroups", []) if isinstance(menu, dict) else []

    categories: list[dict[str, Any]] = []
    dishes: list[dict[str, Any]] = []
    seen = set()

    for group in groups:
        if not isinstance(group, dict):
            continue
        gname = group.get("name") or ""
        items = group.get("items") or []
        valid_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or len(name.strip()) < 2:
                continue

            price = item.get("price")
            if price is None:
                spec_foods = item.get("specFoods") or item.get("specfoods") or []
                if isinstance(spec_foods, list) and spec_foods and isinstance(spec_foods[0], dict):
                    price = spec_foods[0].get("price")

            # 只保留点餐商品，过滤配送/活动等非菜品条目
            if price is None:
                continue

            key = (name.strip(), str(price), gname)
            if key in seen:
                continue
            seen.add(key)

            valid_count += 1

            image_url = item.get("imageUrl") or item.get("image") or ""
            image_hash = item.get("imageHash") or ""
            if not image_url and isinstance(image_hash, str) and image_hash:
                image_url = _image_hash_to_url(image_hash)

            taste_hint = _extract_taste_hint(item)

            dishes.append(
                {
                    "category": gname,
                    "name": name.strip(),
                    "price": _safe_float(price) if _safe_float(price) is not None else price,
                    "description": item.get("description") or "",
                    "month_sales": (item.get("tipTextList") or [None])[0],
                    "image_url": image_url,
                    "image_hash": image_hash,
                    "taste_hint": taste_hint,
                }
            )

        if valid_count > 0:
            categories.append({"name": gname, "dish_count": valid_count})

    return categories, dishes


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_csv(path: Path, shops: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "shop_name",
                "shop_id",
                "shop_url",
                "dish_category",
                "dish_name",
                "dish_price",
                "dish_month_sales",
                "dish_description",
                "dish_image_url",
                "dish_image_hash",
                "dish_taste_hint",
            ],
        )
        writer.writeheader()
        for shop in shops:
            base = {
                "shop_name": shop.get("shop_name"),
                "shop_id": shop.get("shop_id"),
                "shop_url": shop.get("shop_url"),
            }
            menu = shop.get("menu") or []
            if not menu:
                writer.writerow({**base, "dish_category": "", "dish_name": "", "dish_price": "", "dish_month_sales": "", "dish_description": "", "dish_image_url": "", "dish_image_hash": ""})
                continue
            for d in menu:
                writer.writerow(
                    {
                        **base,
                        "dish_category": d.get("category", ""),
                        "dish_name": d.get("name", ""),
                        "dish_price": d.get("price", ""),
                        "dish_month_sales": d.get("month_sales", ""),
                        "dish_description": d.get("description", ""),
                        "dish_image_url": d.get("image_url", ""),
                        "dish_image_hash": d.get("image_hash", ""),
                        "dish_taste_hint": d.get("taste_hint", ""),
                    }
                )


def _flatten_pairs(node: Any) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if isinstance(node, dict):
        name = str(node.get("name") or node.get("title") or node.get("key") or "").strip()
        value = node.get("value") or node.get("text") or node.get("content") or node.get("desc")
        if name and value is not None:
            pairs.append((name, str(value).strip()))
        for v in node.values():
            pairs.extend(_flatten_pairs(v))
    elif isinstance(node, list):
        for x in node:
            pairs.extend(_flatten_pairs(x))
    return pairs


def _extract_taste_hint(item: dict[str, Any]) -> str:
    # 1) 先从结构化键值对里找“口味/味道/flavor/taste”
    pairs = _flatten_pairs(item)
    hints: list[str] = []
    for k, v in pairs:
        lk = k.lower()
        if ("口味" in k) or ("味道" in k) or ("flavor" in lk) or ("taste" in lk):
            if v and v not in hints:
                hints.append(v)

    # 2) 从描述文本中补充提取
    desc = str(item.get("description") or "")
    m = re.search(r"口味[:：]\s*([^，。；\n]+)", desc)
    if m:
        val = m.group(1).strip()
        if val and val not in hints:
            hints.append(val)

    return " / ".join(hints[:3])


def _parse_distance_km(raw: str) -> float | None:
    text = raw.strip().lower()
    if not text:
        return None
    try:
        if text.endswith("km"):
            return float(text[:-2])
        if text.endswith("m"):
            return float(text[:-1]) / 1000.0
    except Exception:
        return None
    return None


def _collect_shop_cards(page) -> list[dict[str, Any]]:
    rows = page.evaluate(
        """
        () => {
            const cards = Array.from(document.querySelectorAll('.card-takeaway-big'));
            return cards.map(card => {
              const title = (card.querySelector('.card-takeaway__title')?.textContent || '').trim();
              const distance = (card.querySelector('.card-takeaway__store-distance')?.textContent || '').trim();
              const href = card.getAttribute('href') || card.closest('a')?.getAttribute('href') || '';
              return { title, distance, href };
            }).filter(x => x.title);
        }
        """
    )
    out: list[dict[str, Any]] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        distance_text = str(row.get("distance") or "").strip()
        out.append(
            {
                "title": title,
                "distance_text": distance_text,
                "distance_km": _parse_distance_km(distance_text),
                "href": str(row.get("href") or "").strip(),
            }
        )
    return out


def _is_login_or_verify_page(page) -> bool:
    try:
        url = page.url or ""
    except Exception:
        url = ""
    # minisite 既可能是登录入口，也可能是正常首页容器，不能仅靠 minisite 判定
    if "ebridge.login" in url or "zebra-ele-login" in url or "passport" in url or "login" in url:
        return True
    try:
        txt = page.inner_text("body")
    except Exception:
        txt = ""
    keywords = ["验证码", "请验证", "安全验证", "滑块", "登录"]
    return any(k in txt for k in keywords)


def _is_home_ready(page) -> bool:
    try:
        count = page.locator(".card-takeaway-big").count()
        if count > 0:
            return True
    except Exception:
        pass
    try:
        body = page.inner_text("body")
    except Exception:
        body = ""
    return "为你推荐附近的商家" in body


def _safe_goto(page, url: str, timeout_ms: int, retries: int = 3) -> bool:
    last_err = None
    for _ in range(retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            return True
        except Exception as exc:
            last_err = exc
            msg = str(exc)
            if "interrupted by another navigation" in msg:
                page.wait_for_timeout(1500)
                continue
            page.wait_for_timeout(1200)
    if last_err:
        print(f"  ! 导航失败: {last_err}")
    return False


def _safe_goto_home(page, timeout_ms: int) -> bool:
    ok = _safe_goto(page, "https://h5.ele.me/", timeout_ms=timeout_ms, retries=4)
    if not ok:
        return False
    page.wait_for_timeout(2500)
    _best_effort_prepare_home(page)
    if _is_home_ready(page):
        return True
    return not _is_login_or_verify_page(page)


def _build_shop_page_url(href: str) -> str | None:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://h5.ele.me{href}"
    return f"https://h5.ele.me/{href}"


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _valid_cn_coord(lat: float | None, lng: float | None) -> bool:
    if lat is None or lng is None:
        return False
    return 15.0 <= lat <= 55.0 and 70.0 <= lng <= 140.0


def _extract_shop_geo_from_payload(payload: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
    # 优先尝试常见结构路径
    candidate_paths = [
        ("data", "storeInfo", "latitude"),
        ("data", "storeInfo", "longitude"),
        ("data", "result", "storeInfo", "latitude"),
        ("data", "result", "storeInfo", "longitude"),
        ("data", "store", "latitude"),
        ("data", "store", "longitude"),
    ]

    def _get_path(d: dict[str, Any], path: tuple[str, ...]) -> Any:
        cur: Any = d
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    direct_lat = None
    direct_lng = None
    for p in candidate_paths:
        val = _get_path(payload, p)
        if p[-1] in {"latitude", "lat"}:
            direct_lat = direct_lat if direct_lat is not None else _to_float(val)
        if p[-1] in {"longitude", "lng", "lon"}:
            direct_lng = direct_lng if direct_lng is not None else _to_float(val)

    addr = None
    for p in [
        ("data", "storeInfo", "address"),
        ("data", "result", "storeInfo", "address"),
        ("data", "store", "address"),
    ]:
        v = _get_path(payload, p)
        if isinstance(v, str) and v.strip():
            addr = v.strip()
            break

    if _valid_cn_coord(direct_lat, direct_lng):
        return direct_lat, direct_lng, addr

    # 兜底：递归搜索任意含坐标字段的对象
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            lat = _to_float(node.get("latitude") or node.get("lat"))
            lng = _to_float(node.get("longitude") or node.get("lng") or node.get("lon"))
            if _valid_cn_coord(lat, lng):
                if not addr:
                    a = node.get("address")
                    if isinstance(a, str) and a.strip():
                        addr = a.strip()
                return lat, lng, addr
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)

    return None, None, addr


def _best_effort_prepare_home(page) -> None:
    # 若首页没有卡片，尝试点击“更新定位”并等待
    try:
        body_text = page.inner_text("body")
    except Exception:
        body_text = ""
    if "定位信息获取失败" in body_text:
        try:
            page.get_by_text("更新定位", exact=True).click(timeout=3000)
            page.wait_for_timeout(4000)
        except Exception:
            pass


def _wait_for_manual_login(page, timeout_ms: int) -> None:
    print("检测到可能需要重新登录。请在打开的浏览器中完成登录。")
    print("登录完成后，回到终端按回车继续抓取...")
    for _ in range(5):
        input()
        if _safe_goto_home(page, timeout_ms):
            return
        print("仍在登录/验证页，请先完成验证后再回车继续...")
    raise RuntimeError("手动登录后仍未进入首页，可能被风控限制，请稍后重试")


def _save_login_state(context, state_file: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(state_file))
    print(f"已保存登录态: {state_file}")


def main() -> None:
    args = parse_args()
    if not args.state_file.exists() and not (args.manual_login and not args.headless):
        raise RuntimeError(f"缺少登录态文件: {args.state_file}")
    if (args.latitude is None) ^ (args.longitude is None):
        raise RuntimeError("--latitude 与 --longitude 需要同时提供，或都不提供")

    results: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context_kwargs: dict[str, Any] = {
            "locale": "zh-CN",
            "viewport": {"width": 430, "height": 932},
        }
        if args.state_file.exists():
            context_kwargs["storage_state"] = str(args.state_file)
        if args.latitude is not None and args.longitude is not None:
            context_kwargs["geolocation"] = {"latitude": args.latitude, "longitude": args.longitude}
            context_kwargs["permissions"] = ["geolocation"]

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        print("[1/4] 打开首页并等待商家卡片")
        if not _safe_goto_home(page, args.timeout_ms):
            if args.manual_login and not args.headless:
                _wait_for_manual_login(page, args.timeout_ms)
            else:
                raise RuntimeError("当前处于登录/验证页，请先使用 --manual-login 完成登录")

        if args.manual_login and not args.headless:
            _wait_for_manual_login(page, args.timeout_ms)
            _save_login_state(context, args.state_file)

        target_cards: list[dict[str, Any]] = []
        for _ in range(8):
            cards = _collect_shop_cards(page)
            existing_titles = {x["title"] for x in target_cards}
            for c in cards:
                if c["title"] not in existing_titles:
                    target_cards.append(c)

            if len(target_cards) >= args.limit:
                break
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(1200)

        # 首次未采集到卡片，回首页再尝试一次
        if not target_cards:
            _safe_goto_home(page, args.timeout_ms)
            for _ in range(5):
                cards = _collect_shop_cards(page)
                existing_titles = {x["title"] for x in target_cards}
                for c in cards:
                    if c["title"] not in existing_titles:
                        target_cards.append(c)
                if target_cards:
                    break
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1200)

        if not target_cards:
            if not args.headless:
                _wait_for_manual_login(page, args.timeout_ms)
                _save_login_state(context, args.state_file)
                for _ in range(8):
                    cards = _collect_shop_cards(page)
                    existing_titles = {x["title"] for x in target_cards}
                    for c in cards:
                        if c["title"] not in existing_titles:
                            target_cards.append(c)
                    if len(target_cards) >= args.limit:
                        break
                    page.mouse.wheel(0, 2200)
                    page.wait_for_timeout(1200)

        if not target_cards:
            page.screenshot(path="full_menu_home_fail.png", full_page=True)
            raise RuntimeError("未获取到商家标题，请确认登录与定位是否正常")

        target_cards = target_cards[: args.limit]
        target_items = target_cards[: args.limit]
        print(f"[2/4] 准备抓取商家: {len(target_items)} 家")

        for idx, target in enumerate(target_items, start=1):
            shop_name = target["title"]
            captured: dict[str, Any] | None = None

            def on_response(resp: Response) -> None:
                nonlocal captured
                if captured is not None:
                    return
                if "store.detail.body.query.v2" not in resp.url:
                    return
                try:
                    payload = resp.json()
                except Exception:
                    return
                captured = {"url": resp.url, "payload": payload}

            page.on("response", on_response)

            # 优先使用卡片 href 直达店铺，降低重复滚动和误点
            found = False
            target_url = _build_shop_page_url(target.get("href") or "")
            if target_url:
                if _safe_goto(page, target_url, timeout_ms=args.timeout_ms, retries=3):
                    page.wait_for_timeout(3500)
                    found = True

            # 无 href 时回退：回首页后按标题查找点击
            if not found:
                if not _safe_goto_home(page, args.timeout_ms):
                    if args.manual_login and not args.headless:
                        _wait_for_manual_login(page, args.timeout_ms)
                    else:
                        debug.append({"shop_name": shop_name, "ok": False, "error": "命中登录/验证页"})
                        print(f"  - [{idx}/{len(target_items)}] {shop_name} -> 需要验证，已跳过")
                        page.remove_listener("response", on_response)
                        continue

                for _ in range(10):
                    cards = page.locator(".card-takeaway-big")
                    count = cards.count()
                    for i in range(count):
                        card = cards.nth(i)
                        try:
                            title = card.locator(".card-takeaway__title").first.inner_text(timeout=1200).strip()
                        except Exception:
                            continue
                        if title == shop_name:
                            card.scroll_into_view_if_needed(timeout=3000)
                            card.click(timeout=6000)
                            found = True
                            break
                    if found:
                        break
                    page.mouse.wheel(0, 2400)
                    page.wait_for_timeout(1200)

            if not found:
                debug.append({"shop_name": shop_name, "ok": False, "error": "未在列表中定位到店铺"})
                print(f"  - [{idx}/{len(target_items)}] {shop_name} -> 未找到")
                page.remove_listener("response", on_response)
                continue

            if _is_login_or_verify_page(page):
                debug.append({"shop_name": shop_name, "ok": False, "error": "访问店铺时进入登录/验证页"})
                print(f"  - [{idx}/{len(target_items)}] {shop_name} -> 命中验证页，已跳过")
                page.remove_listener("response", on_response)
                continue

            page.wait_for_timeout(4500)

            # 点击点餐标签，确保加载点餐接口
            try:
                page.get_by_text("点餐", exact=True).click(timeout=3000)
                page.wait_for_timeout(1200)
            except Exception:
                pass

            # 在店铺页稍微滚动，确保点餐数据加载
            for _ in range(3):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(1200)
            page.remove_listener("response", on_response)

            # 如果上面没抓到，请直接调用同源 mtop 接口拉店铺 body 数据
            if captured is None:
                try:
                    page.wait_for_timeout(500)
                    direct = page.evaluate(
                        """
                        async () => {
                            const links = Array.from(document.querySelectorAll('*'))
                              .map(n => (n.getAttribute && n.getAttribute('href')) || '')
                              .filter(Boolean);
                            const urlObj = new URL(location.href);
                            const shopId = urlObj.searchParams.get('shopId') || '';
                            const lng = urlObj.searchParams.get('__locLng') || urlObj.searchParams.get('longitude') || '121.4737';
                            const lat = urlObj.searchParams.get('__locLat') || urlObj.searchParams.get('latitude') || '31.2304';

                            const api = 'https://waimai-guide.ele.me/h5/mtop.alsc.waimai.store.miniapp.store.detail.body.query.v2/1.0/5.0/';
                            const data = {
                              longitude: Number(lng),
                              latitude: Number(lat),
                              storeId: shopId,
                              eleStoreId: shopId,
                              bizInfos: JSON.stringify({
                                businessComeFrom: 'mobile.default',
                              }),
                            };

                            const qs = new URLSearchParams({
                              jsv: '2.7.5',
                              appKey: '12574478',
                              api: 'mtop.alsc.waimai.store.miniapp.store.detail.body.query.v2',
                              v: '1.0',
                              type: 'originaljson',
                              dataType: 'json',
                              timeout: '10000',
                              mainDomain: 'ele.me',
                              subDomain: 'waimai-guide',
                              H5Request: 'true',
                              ttid: 'h5@chrome_pc',
                              SV: '5.0',
                              EtRequest: 'true',
                              syncCookieMode: 'true',
                              pageDomain: 'ele.me',
                              data: JSON.stringify(data),
                            });

                            const r = await fetch(`${api}?${qs.toString()}`, { credentials: 'include' });
                            const text = await r.text();
                            let payload = null;
                            try { payload = JSON.parse(text); } catch (_) {}
                            return { status: r.status, url: r.url, payload, text: text.slice(0, 500) };
                        }
                        """
                    )
                    if direct and direct.get("payload"):
                        captured = {"url": direct.get("url"), "payload": direct.get("payload")}
                except Exception:
                    pass

            if captured is None:
                debug.append({"shop_name": shop_name, "ok": False, "error": "未捕获到 body.query.v2"})
                print(f"  - [{idx}/{len(target_items)}] {shop_name} -> 未捕获菜单接口")
                continue

            categories, dishes = _menu_from_body_query(captured["payload"])
            dishes = _pick_top_dishes(dishes, args.max_dishes_per_shop)
            shop_lat, shop_lng, shop_addr = _extract_shop_geo_from_payload(captured["payload"])
            shop_id = None
            # 优先从 URL 解析 shopId
            if "shopId=" in page.url:
                try:
                    shop_id = page.url.split("shopId=")[1].split("&")[0]
                except Exception:
                    shop_id = None

            results.append(
                {
                    "shop_name": shop_name,
                    "shop_id": shop_id,
                    "shop_url": page.url,
                    "shop_address": shop_addr,
                    "shop_latitude": shop_lat,
                    "shop_longitude": shop_lng,
                    "shop_distance_km": target.get("distance_km"),
                    "category_summary": categories,
                    "menu": dishes,
                }
            )
            debug.append(
                {
                    "shop_name": shop_name,
                    "ok": True,
                    "shop_url": page.url,
                    "request_url": captured["url"],
                    "category_count": len(categories),
                    "dish_count": len(dishes),
                }
            )
            print(f"  - [{idx}/{len(target_items)}] {shop_name} -> 菜品 {len(dishes)}")
            page.wait_for_timeout(1200)

        print("[3/4] 保存登录态")
        _save_login_state(context, args.state_file)
        browser.close()

    print("[4/4] 写入结果文件")
    save_json(args.output_json, results)
    save_csv(args.output_csv, results)
    save_json(args.output_debug, debug)

    inferred_lat = args.latitude
    inferred_lng = args.longitude
    if inferred_lat is None or inferred_lng is None:
        lat2, lng2 = _infer_location_from_results(results)
        inferred_lat = inferred_lat if inferred_lat is not None else lat2
        inferred_lng = inferred_lng if inferred_lng is not None else lng2

    meta = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "eleme_h5",
        "limit": args.limit,
        "max_dishes_per_shop": args.max_dishes_per_shop,
        "used_manual_login": bool(args.manual_login),
        "city": None,
        "latitude": inferred_lat,
        "longitude": inferred_lng,
        "input_mode": "specified_location" if args.latitude is not None and args.longitude is not None else "current_location",
        "output_json": str(args.output_json),
        "output_csv": str(args.output_csv),
        "output_debug": str(args.output_debug),
    }
    save_json(args.output_meta, meta)

    with_menu = sum(1 for x in results if x.get("menu"))
    if len(results) < args.limit:
        print(f"提示：目标 {args.limit} 家，实际抓到 {len(results)} 家。可重跑或提高 limit。")
        if args.strict_limit:
            raise RuntimeError(f"严格模式失败：目标 {args.limit} 家，实际 {len(results)} 家")
    print(f"完成。商家总数: {len(results)}，含点餐菜品商家: {with_menu}")
    print(f"JSON: {args.output_json.resolve()}")
    print(f"CSV : {args.output_csv.resolve()}")
    print(f"DBG : {args.output_debug.resolve()}")
    print(f"META: {args.output_meta.resolve()}")


if __name__ == "__main__":
    main()
