import argparse
import csv
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import Response
from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="自动打开饿了么商家并抓取点餐页完整菜品")
    p.add_argument("--state-file", type=Path, default=Path(".playwright/eleme_state.json"))
    p.add_argument("--limit", type=int, default=10, help="目标商家数")
    p.add_argument("--latitude", type=float, default=None, help="可选：指定纬度；不传则使用页面当前位置")
    p.add_argument("--longitude", type=float, default=None, help="可选：指定经度；不传则使用页面当前位置")
    p.add_argument("--strict-limit", action="store_true", help="若最终商家数小于 limit，则报错退出")
    p.add_argument("--output-json", type=Path, default=Path("menus_around.json"))
    p.add_argument("--output-csv", type=Path, default=Path("menus_around.csv"))
    p.add_argument("--output-debug", type=Path, default=Path("menus_debug.json"))
    p.add_argument("--headless", action="store_true")
    p.add_argument("--timeout-ms", type=int, default=30000)
    return p.parse_args()


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except Exception:
        return None


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

            dishes.append(
                {
                    "category": gname,
                    "name": name.strip(),
                    "price": _safe_float(price) if _safe_float(price) is not None else price,
                    "description": item.get("description") or "",
                    "month_sales": (item.get("tipTextList") or [None])[0],
                    "image_url": image_url,
                    "image_hash": image_hash,
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
                    }
                )


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
              return { title, distance };
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
            }
        )
    return out


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


def main() -> None:
    args = parse_args()
    if not args.state_file.exists():
        raise RuntimeError(f"缺少登录态文件: {args.state_file}")
    if (args.latitude is None) ^ (args.longitude is None):
        raise RuntimeError("--latitude 与 --longitude 需要同时提供，或都不提供")

    results: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context_kwargs: dict[str, Any] = {
            "storage_state": str(args.state_file),
            "locale": "zh-CN",
            "viewport": {"width": 430, "height": 932},
        }
        if args.latitude is not None and args.longitude is not None:
            context_kwargs["geolocation"] = {"latitude": args.latitude, "longitude": args.longitude}
            context_kwargs["permissions"] = ["geolocation"]

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        print("[1/4] 打开首页并等待商家卡片")
        page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
        page.wait_for_timeout(5000)
        _best_effort_prepare_home(page)

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
            page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.wait_for_timeout(5000)
            _best_effort_prepare_home(page)
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
            page.screenshot(path="full_menu_home_fail.png", full_page=True)
            raise RuntimeError("未获取到商家标题，请确认登录与定位是否正常")

        target_cards = target_cards[: args.limit]
        target_titles = [c["title"] for c in target_cards]
        print(f"[2/4] 准备抓取商家: {len(target_titles)} 家")

        for idx, shop_name in enumerate(target_titles, start=1):
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

            # 回到首页并找到目标店铺
            page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.wait_for_timeout(3500)
            _best_effort_prepare_home(page)

            found = False
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
                print(f"  - [{idx}/{len(target_titles)}] {shop_name} -> 未找到")
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
                print(f"  - [{idx}/{len(target_titles)}] {shop_name} -> 未捕获菜单接口")
                continue

            categories, dishes = _menu_from_body_query(captured["payload"])
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
            print(f"  - [{idx}/{len(target_titles)}] {shop_name} -> 菜品 {len(dishes)}")

        print("[3/4] 保存登录态")
        context.storage_state(path=str(args.state_file))
        browser.close()

    print("[4/4] 写入结果文件")
    save_json(args.output_json, results)
    save_csv(args.output_csv, results)
    save_json(args.output_debug, debug)

    with_menu = sum(1 for x in results if x.get("menu"))
    if len(results) < args.limit:
        print(f"提示：目标 {args.limit} 家，实际抓到 {len(results)} 家。可重跑或提高 limit。")
        if args.strict_limit:
            raise RuntimeError(f"严格模式失败：目标 {args.limit} 家，实际 {len(results)} 家")
    print(f"完成。商家总数: {len(results)}，含点餐菜品商家: {with_menu}")
    print(f"JSON: {args.output_json.resolve()}")
    print(f"CSV : {args.output_csv.resolve()}")
    print(f"DBG : {args.output_debug.resolve()}")


if __name__ == "__main__":
    main()
