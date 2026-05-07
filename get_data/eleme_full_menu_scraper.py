import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Response
from playwright.sync_api import sync_playwright


_SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(str(_SCRIPT_DIR))


# =============================================================================
# 风控模拟工具：所有操作都通过这里，模拟真人的行为特征
# =============================================================================
class AntiDetect:
    """
    模拟真人操作行为，避免被风控系统识别为脚本。
    核心原理：让每次操作的时间、距离、节奏都有自然随机波动。
    """

    @staticmethod
    def sleep(page, base_ms: int) -> None:
        """
        随机等待：基础时间上叠加 ±25% 的随机波动，最小不低于 300ms。
        模拟真人操作之间不规律的停顿。
        """
        if base_ms <= 0:
            return
        jitter = base_ms * random.uniform(0.25, 0.45)
        delay = int(base_ms + random.uniform(-jitter, jitter))
        delay = max(300, delay)
        page.wait_for_timeout(delay)

    @staticmethod
    def scroll(page) -> None:
        """
        模拟真人滚动：随机距离 + 随机等待 + 偶尔停顿"看内容"。
        每次滚动后等待时间根据滚动距离动态变化（滚得多等得久）。
        """
        # 滚动距离：800-2800 像素，正态分布偏向中间值
        distance = int(random.gauss(1600, 500))
        distance = max(800, min(2800, distance))

        # 随机选择滚动方向（99%向下，1%向上，模拟回拉）
        if random.random() < 0.01:
            distance = -int(abs(distance) * random.uniform(0.3, 0.6))

        page.mouse.wheel(0, distance)

        # 滚动后等待时间：与滚动距离成正比 + 随机波动
        # 滚得多需要等更久让内容加载，也更像真人
        base_wait = abs(distance) * random.uniform(0.6, 1.2)

        # 15% 概率额外停顿 2-5 秒（模拟"在看内容"）
        if random.random() < 0.15:
            base_wait += random.uniform(2000, 5000)

        page.wait_for_timeout(int(base_wait))

    @staticmethod
    def move_mouse_to_scroll_area(page) -> None:
        """
        将鼠标移动到页面中央偏下位置（滚动区域），
        模拟真人把手指放在内容区域准备滑动。
        """
        try:
            viewport = page.viewport_size or {"width": 430, "height": 932}
            x = viewport["width"] * random.uniform(0.3, 0.7)
            y = viewport["height"] * random.uniform(0.4, 0.7)
            page.mouse.move(x, y)
            page.wait_for_timeout(int(random.uniform(200, 500)))
        except Exception:
            pass

    @staticmethod
    def random_long_pause(page) -> None:
        """
        随机长停顿：3-8 秒，模拟真人停下来看推荐内容。
        在回到首页后、抓取新商家前调用，降低操作频率。
        """
        pause = random.uniform(3000, 8000)
        page.wait_for_timeout(int(pause))


# =============================================================================
# 参数解析
# =============================================================================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="饿了么商家菜单抓取")
    p.add_argument("--state-file", type=Path, default=Path(".playwright/eleme_state.json"), help="登录态存储路径")
    p.add_argument("--limit", type=int, default=1, help="目标抓取商家数量（默认 1）")
    p.add_argument("--latitude", type=float, default=None, help="可选：指定纬度")
    p.add_argument("--longitude", type=float, default=None, help="可选：指定经度")
    p.add_argument("--timeout-ms", type=int, default=30000, help="页面导航超时（毫秒）")
    p.add_argument("--interval-ms", type=int, default=5000, help="操作间隔（毫秒），默认 5000ms")
    p.add_argument("--output-json", type=Path, default=Path(".generated/menus_around.json"), help="输出 JSON 路径")
    return p.parse_args()


def error_exit(msg: str, results: list[dict[str, Any]] | None = None, args: argparse.Namespace | None = None) -> None:
    """
    输出错误，保存已抓取的数据（如果有），然后等待用户确认后退出。
    避免已抓取的数据因异常而丢失。
    """
    print(f"\n[ERROR] {msg}")

    # 保存已抓取的数据（如果有）
    if results and args and len(results) > 0:
        try:
            save_json(args.output_json, results)
            print(f"\n  [已保存] 已抓取 {len(results)} 家商家的数据: {args.output_json.resolve()}")
        except Exception as e:
            print(f"\n  [保存失败] 无法保存已抓取的数据: {e}")

    print("\n脚本已暂停。按回车键退出...")
    input()
    sys.exit(1)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except Exception:
        return None


def _month_sales_score(raw: Any) -> int:
    text = str(raw or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else -1


def _image_hash_to_url(image_hash: str) -> str:
    lower = image_hash.lower()
    exts = ["jpeg", "jpg", "png", "webp", "gif"]
    ext = next((e for e in exts if lower.endswith(e)), None)

    if len(image_hash) < 4:
        return ""

    dir1, dir2, stem = image_hash[0], image_hash[1:3], image_hash[3:]
    filename = stem if "." in stem or not ext else f"{stem}.{ext}"

    return (
        f"https://cube.elemecdn.com/{dir1}/{dir2}/{filename}"
        "?x-oss-process=image/resize,m_mfit,w_192,h_192/format,webp/quality,q_90"
    )


def _extract_taste_hint(item: dict[str, Any]) -> str:
    hints: list[str] = []
    for k, v in item.items():
        if isinstance(v, str) and (("口味" in k) or ("味道" in k) or ("flavor" in k.lower()) or ("taste" in k.lower())):
            if v and v not in hints:
                hints.append(v)

    desc = str(item.get("description") or "")
    m = re.search(r"口味[:：]\s*([^，。；\n]+)", desc)
    if m:
        val = m.group(1).strip()
        if val and val not in hints:
            hints.append(val)

    return " / ".join(hints[:3])


def _has_solo_no_delivery(item: dict[str, Any]) -> bool:
    for key in ["description", "tips", "tagText", "labelText", "activityText", "promotionText"]:
        val = item.get(key)
        if isinstance(val, str) and "单点不送" in val:
            return True

    def _scan(node: Any) -> bool:
        if isinstance(node, str) and "单点不送" in node:
            return True
        if isinstance(node, dict):
            return any(_scan(v) for v in node.values())
        if isinstance(node, list):
            return any(_scan(x) for x in node)
        return False

    return _scan(item)


# ---------------------------------------------------------------------------
# 页面状态检测
# ---------------------------------------------------------------------------
def _is_login_or_verify_page(page) -> bool:
    try:
        url = page.url or ""
    except Exception:
        url = ""
    if any(k in url for k in ["ebridge.login", "zebra-ele-login", "passport", "login"]):
        return True
    try:
        return any(k in page.inner_text("body") for k in ["验证码", "请验证", "安全验证", "滑块", "登录"])
    except Exception:
        return False


def _is_home_ready(page) -> bool:
    try:
        if page.locator(".card-takeaway-big").count() > 0:
            return True
    except Exception:
        pass
    try:
        return "为你推荐附近的商家" in page.inner_text("body")
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 登录态
# ---------------------------------------------------------------------------
def _save_login_state(context, state_file: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(state_file))
    print(f"  已保存登录态: {state_file}")


def _wait_for_manual_login(page, timeout_ms: int, context, state_file: Path, results: list[dict[str, Any]] | None = None, args: argparse.Namespace | None = None) -> None:
    """
    无限等待用户在浏览器中完成登录。
    用户按回车后，先等待浏览器完成登录重定向，再导航到首页。
    成功进入首页后立即保存登录态（不依赖后续代码）。
    """
    print("\n检测到需要登录/验证。请在浏览器中完成登录。")
    print("完成后按回车继续...")
    while True:
        input()

        # 等待浏览器完成登录后的重定向（常见：登录页 → minisite → 首页）
        print("  等待登录重定向完成...")
        page.wait_for_timeout(3000)

        # 如果当前页面正在导航中，等它完成
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        # 尝试导航到首页（如果已经在首页则跳过）
        try:
            if _is_home_ready(page):
                print("  当前已在首页")
                _save_login_state(context, state_file)
                break

            page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2000)
        except Exception as e:
            err_msg = str(e)
            if "interrupted by another navigation" in err_msg or "Navigation" in err_msg:
                print(f"  登录重定向中，等待 3 秒后重试...")
                page.wait_for_timeout(3000)
                try:
                    if _is_home_ready(page):
                        print("  当前已在首页")
                        _save_login_state(context, state_file)
                        break
                    page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(2000)
                except Exception as e2:
                    error_exit(f"登录后导航失败（重试后）: {e2}", results, args)
            else:
                error_exit(f"登录后导航失败: {e}", results, args)

        if _is_login_or_verify_page(page):
            print("  仍在登录/验证页，请先完成验证后再回车...")
            continue
        if _is_home_ready(page):
            _save_login_state(context, state_file)
            break
        print("  页面未就绪，请确认登录成功后再回车...")


# ---------------------------------------------------------------------------
# 首页商家采集
# ---------------------------------------------------------------------------
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


def _collect_visible_cards(page) -> list[dict[str, Any]]:
    rows = page.evaluate(
        """
        () => Array.from(document.querySelectorAll('.card-takeaway-big')).map(card => ({
            title: (card.querySelector('.card-takeaway__title')?.textContent || '').trim(),
            distance: (card.querySelector('.card-takeaway__store-distance')?.textContent || '').trim(),
        })).filter(x => x.title)
        """
    )
    if not isinstance(rows, list):
        rows = []

    out: list[dict[str, Any]] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        out.append({
            "title": title,
            "distance_text": str(row.get("distance") or "").strip(),
            "distance_km": _parse_distance_km(str(row.get("distance") or "")),
        })
    return out


def _click_visible_card(page, shop_name: str, ad: AntiDetect) -> bool:
    cards = page.locator(".card-takeaway-big")
    for i in range(cards.count()):
        card = cards.nth(i)
        try:
            title = card.locator(".card-takeaway__title").first.inner_text(timeout=1500).strip()
        except Exception:
            continue
        if title == shop_name:
            try:
                card.scroll_into_view_if_needed(timeout=3000)
                ad.sleep(page, 800)  # 看到卡片后短暂停顿（模拟阅读）
                card.click(timeout=6000)
                ad.sleep(page, 1500)  # 点击后等待页面跳转
                return True
            except Exception:
                return False
    return False


# ---------------------------------------------------------------------------
# 滚动状态检测
# ---------------------------------------------------------------------------
def _get_scroll_state(page) -> dict:
    result = page.evaluate(
        """
        () => {
            const all = Array.from(document.querySelectorAll('div, section, main'));
            let best = null, bestScroll = 0;
            for (const el of all) {
                const sh = el.scrollHeight, ch = el.clientHeight;
                if (sh > ch + 50 && sh > bestScroll) { best = el; bestScroll = sh; }
            }
            return best ? { scrollTop: best.scrollTop } : { scrollTop: window.scrollY };
        }
        """
    )
    return result if isinstance(result, dict) else {"scrollTop": 0}


# ---------------------------------------------------------------------------
# 菜品解析
# ---------------------------------------------------------------------------
def _extract_dishes(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_dishes: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for payload in payloads:
        result_map = payload.get("data", {}).get("resultMap", {})
        menu = result_map.get("menu", {}) if isinstance(result_map, dict) else {}
        groups = menu.get("itemGroups", []) if isinstance(menu, dict) else []

        for group in groups:
            if not isinstance(group, dict):
                continue
            gname = group.get("name") or ""
            for item in group.get("items") or []:
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
                if price is None:
                    continue

                price_f = _safe_float(price)
                if price_f is None or price_f < 1.0:
                    continue

                if _has_solo_no_delivery(item):
                    continue

                key = (name.strip(), str(price), gname)
                if key in seen:
                    continue
                seen.add(key)

                image_hash = item.get("imageHash") or ""
                image_url = item.get("imageUrl") or item.get("image") or ""
                if not image_url and isinstance(image_hash, str) and image_hash:
                    image_url = _image_hash_to_url(image_hash)

                month_sales = None
                tip_list = item.get("tipTextList")
                if isinstance(tip_list, list) and tip_list:
                    month_sales = tip_list[0]
                if month_sales is None:
                    month_sales = item.get("month_sales") or item.get("sales") or item.get("monthSale")

                all_dishes.append({
                    "category": gname,
                    "name": name.strip(),
                    "price": price_f,
                    "description": item.get("description") or "",
                    "month_sales": month_sales,
                    "image_url": image_url,
                    "image_hash": image_hash,
                    "taste_hint": _extract_taste_hint(item),
                })

    return all_dishes


# ---------------------------------------------------------------------------
# 商家信息解析
# ---------------------------------------------------------------------------
def _extract_shop_info(payload: dict[str, Any]) -> dict[str, Any]:
    info = {"shop_id": "", "name": "", "address": "", "latitude": None, "longitude": None, "image_url": ""}

    if not isinstance(payload, dict):
        return info

    data = payload.get("data", {})
    if not isinstance(data, dict):
        data = payload

    restaurant = None
    if isinstance(data, dict):
        cart = data.get("cart")
        if isinstance(cart, dict):
            restaurant = cart.get("restaurant")
        if not isinstance(restaurant, dict):
            restaurant = data.get("restaurant")
    if not isinstance(restaurant, dict) and isinstance(payload, dict):
        restaurant = payload.get("restaurant")

    if not isinstance(restaurant, dict):
        return info

    info["name"] = str(restaurant.get("name") or "").strip()
    info["address"] = str(restaurant.get("address") or "").strip()
    info["latitude"] = _safe_float(restaurant.get("latitude"))
    info["longitude"] = _safe_float(restaurant.get("longitude"))
    info["shop_id"] = str(
        restaurant.get("encrypted_id") or restaurant.get("id") or restaurant.get("restaurant_id") or ""
    ).strip()

    image_path = restaurant.get("image_path")
    if isinstance(image_path, str) and image_path:
        info["image_url"] = image_path

    return info


# ---------------------------------------------------------------------------
# 抓取单个商家
# ---------------------------------------------------------------------------
def _scrape_one_shop(page, shop_name: str, args, ad: AntiDetect) -> dict[str, Any] | None:
    """
    抓取单个商家的菜品和商家信息。
    shop_name 非空时：从首页点击该商家卡片进入。
    shop_name 为空时：假设已在菜品页面，直接监听+滚动+解析。
    """
    if shop_name:
        print(f"\n  [{shop_name}]")
    else:
        print(f"\n  [手动模式] 抓取当前页面商家")

    menu_payloads: list[dict[str, Any]] = []
    shop_payloads: list[dict[str, Any]] = []

    def on_response(resp: Response) -> None:
        if "store.detail.body.query.v2" in resp.url:
            try:
                menu_payloads.append(resp.json())
            except Exception:
                pass
        if "carts.shop.operate" in resp.url or "waimai.carts.shop" in resp.url:
            try:
                shop_payloads.append(resp.json())
            except Exception:
                pass

    page.on("response", on_response)

    # 批量模式：需要点击商家卡片进入
    if shop_name:
        if not _click_visible_card(page, shop_name, ad):
            page.remove_listener("response", on_response)
            print(f"    [跳过] 未找到可点击的卡片")
            return None

        if _is_login_or_verify_page(page):
            page.remove_listener("response", on_response)
            print(f"    [跳过] 命中登录/验证页")
            return None

    # 确保在"点餐"标签
    try:
        page.get_by_text("点餐", exact=True).click(timeout=3000)
        ad.sleep(page, 1200)
    except Exception:
        pass

    # 滚动加载菜品（使用 AntiDetect 模拟真人滚动）
    print("    滚动加载...")
    ad.move_mouse_to_scroll_area(page)
    no_move = 0
    last_top = -1
    for _ in range(30):
        ad.scroll(page)

        state = _get_scroll_state(page)
        top = state.get("scrollTop", 0)
        if top == last_top:
            no_move += 1
            if no_move >= 2 and menu_payloads:
                break
        else:
            no_move = 0
            last_top = top

        if menu_payloads and _ >= 5:
            break

    page.remove_listener("response", on_response)

    # 刷新重试
    if not menu_payloads:
        print("    未捕获数据，刷新重试...")
        try:
            page.reload(wait_until="domcontentloaded", timeout=args.timeout_ms)
            ad.sleep(page, args.interval_ms)
        except Exception:
            print(f"    [跳过] 刷新失败")
            return None
        if _is_login_or_verify_page(page):
            print(f"    [跳过] 刷新后命中登录/验证页")
            return None

        menu_payloads = []
        shop_payloads = []
        page.on("response", on_response)

        try:
            page.get_by_text("点餐", exact=True).click(timeout=3000)
            ad.sleep(page, 1200)
        except Exception:
            pass

        ad.move_mouse_to_scroll_area(page)
        for _ in range(15):
            ad.scroll(page)
            if menu_payloads:
                break
        page.remove_listener("response", on_response)

        if not menu_payloads:
            print(f"    [跳过] 刷新后仍未获取到数据")
            return None

    # 解析菜品
    dishes = _extract_dishes(menu_payloads)
    if not dishes:
        print(f"    [跳过] 未获取到有效菜品")
        return None
    print(f"    菜品: {len(dishes)} 道")

    # 解析商家信息
    shop_info: dict[str, Any] = {"shop_id": "", "name": "", "address": "", "latitude": None, "longitude": None, "image_url": ""}
    for sp in shop_payloads:
        extracted = _extract_shop_info(sp)
        if extracted["name"] or extracted["address"]:
            shop_info = extracted
            break

    # 兜底商家名称
    if not shop_info["name"]:
        if shop_name:
            shop_info["name"] = shop_name
        else:
            inferred = _extract_current_shop_title(page)
            if inferred:
                shop_info["name"] = inferred

    # 兜底商家图片
    if not shop_info["image_url"] and dishes:
        best = sorted(dishes, key=lambda d: (_month_sales_score(d.get("month_sales")), d.get("price", 0)), reverse=True)
        shop_info["image_url"] = best[0].get("image_url", "")

    return {
        "shop_name": shop_info["name"],
        "shop_id": shop_info["shop_id"],
        "shop_image_url": shop_info["image_url"],
        "shop_address": shop_info["address"],
        "shop_latitude": shop_info["latitude"],
        "shop_longitude": shop_info["longitude"],
        "menus": dishes,
    }


# ---------------------------------------------------------------------------
# 核心流程
# ---------------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    results: list[dict[str, Any]] = []

    if (args.latitude is None) ^ (args.longitude is None):
        error_exit("--latitude 与 --longitude 需要同时提供，或都不提供", results, args)

    ad = AntiDetect()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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

        # Step 1: 首页 + 登录态
        print("[Step 1/4] 打开首页...")
        try:
            page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
            ad.sleep(page, args.interval_ms)
        except Exception as e:
            error_exit(f"首页导航失败: {e}", results, args)

        if _is_login_or_verify_page(page):
            print("当前页面处于登录/验证状态。")
            _wait_for_manual_login(page, args.timeout_ms, context, args.state_file, results, args)
            ad.sleep(page, args.interval_ms)

        if not _is_home_ready(page):
            error_exit("首页未就绪，无法继续", results, args)

        print("首页就绪")
        ad.sleep(page, args.interval_ms)

        # Step 2+3: 在首页边滚动边抓取
        print(f"[Step 2/4] 滚动首页并抓取商家（目标 {args.limit} 家）...")
        visited: set[str] = set()
        all_seen: set[str] = set()
        no_new_count = 0
        max_scrolls = 80
        scroll_round = 0
        refreshed_once = False

        while len(visited) < args.limit and scroll_round < max_scrolls:
            # 1. 获取当前可见的商家卡片
            cards = _collect_visible_cards(page)

            # 2. 找出一个未访问的商家
            target = None
            for card in cards:
                title = card["title"]
                all_seen.add(title)
                if title not in visited:
                    target = title
                    break

            # 3. 找到未访问商家，点击并抓取
            if target:
                entry = _scrape_one_shop(page, target, args, ad)

                if entry:
                    results.append(entry)
                    visited.add(target)
                    print(f"  已抓取 {len(visited)}/{args.limit} 家")
                else:
                    visited.add(target)
                    print(f"  抓取失败，跳过。已处理 {len(visited)}/{args.limit} 家")

                # 回到首页继续
                try:
                    page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
                    ad.random_long_pause(page)  # 回到首页后随机长停顿（模拟看推荐）
                except Exception:
                    error_exit("回首页失败", results, args)

                if _is_login_or_verify_page(page):
                    error_exit("回首页后命中登录/验证页", results, args)
                if not _is_home_ready(page):
                    error_exit("回首页后页面未就绪", results, args)

                no_new_count = 0
                scroll_round = 0
                continue

            # 4. 当前视口没有未访问商家，向下滚动
            ad.move_mouse_to_scroll_area(page)
            ad.scroll(page)
            scroll_round += 1

            # 5. 检查本轮滚动后是否有新商家出现
            cards_after = _collect_visible_cards(page)
            new_titles = {c["title"] for c in cards_after} - all_seen
            if new_titles:
                no_new_count = 0
                for t in new_titles:
                    all_seen.add(t)
                print(f"    本轮滚动发现 {len(new_titles)} 家新商家（累计 {len(all_seen)} 家）")
            else:
                no_new_count += 1
                print(f"    本轮滚动无新商家（连续 {no_new_count} 次，累计 {len(all_seen)} 家）")

                # 连续 5 次无新商家，尝试刷新首页一次
                if no_new_count >= 5 and not refreshed_once:
                    print("    首页似乎到底，尝试刷新...")
                    try:
                        page.goto("https://h5.ele.me/", wait_until="domcontentloaded", timeout=args.timeout_ms)
                        ad.sleep(page, args.interval_ms * 2)
                    except Exception:
                        break

                    if _is_login_or_verify_page(page):
                        break
                    if not _is_home_ready(page):
                        break

                    refreshed_once = True
                    no_new_count = 0
                    scroll_round = 0
                    all_seen = set()
                    cards_refreshed = _collect_visible_cards(page)
                    for c in cards_refreshed:
                        all_seen.add(c["title"])
                    print(f"    刷新后首页有 {len(all_seen)} 家可见商家")
                    continue

                # 已经刷新过一次，连续 5 次仍无新商家，真正到底
                if no_new_count >= 5 and refreshed_once:
                    print(f"    首页已彻底到底，共处理 {len(visited)} 家商家")
                    break

        # Step 4: 手动选择商家模式（可选）
        print(f"\n[Step 3/4] 首页推荐模式完成，共抓取 {len(results)} 家商家")
        _scrape_manual_shops(page, results, args, ad, context)

        # Step 5: 保存
        print(f"\n[Step 4/4] 保存最终结果...")
        save_json(args.output_json, results)
        _save_login_state(context, args.state_file)
        browser.close()

    print(f"\n完成！共抓取 {len(results)} 家商家")
    print(f"数据: {args.output_json.resolve()}")
    print("\n按回车键退出...")
    input()


# ---------------------------------------------------------------------------
# 手动选择商家模式
# ---------------------------------------------------------------------------
def _scrape_manual_shops(page, results: list[dict[str, Any]], args, ad: AntiDetect, context) -> None:
    """
    手动模式：用户自行进入商家菜品页面，脚本直接抓取当前页面。
    """
    while True:
        print("\n" + "=" * 50)
        print("是否需要手动选择商家页面来拉取数据？")
        print("  输入 1 并回车：需要（请先手动进入商家菜品页面）")
        print("  直接回车：不需要，结束程序")
        print("=" * 50)
        choice = input().strip()

        if choice != "1":
            break

        # 直接抓取当前页面（shop_name 为空，跳过点击卡片）
        entry = _scrape_one_shop(page, "", args, ad)

        if entry:
            # 去重
            existing_ids = {r["shop_id"] for r in results if r.get("shop_id")}
            existing_names = {r["shop_name"] for r in results}
            if entry.get("shop_id") and entry["shop_id"] in existing_ids:
                print(f"  商家「{entry['shop_name']}」已采集过，跳过")
                continue
            if entry["shop_name"] in existing_names:
                print(f"  商家「{entry['shop_name']}」已采集过，跳过")
                continue

            results.append(entry)
            print(f"  成功抓取「{entry['shop_name']}」，累计 {len(results)} 家")
            try:
                save_json(args.output_json, results)
            except Exception:
                pass
        else:
            print("  未获取到数据，跳过")


def _extract_current_shop_title(page) -> str | None:
    """
    从当前页面提取商家名称，用于去重。
    尝试多种选择器，取第一个非空结果。
    """
    selectors = [
        # 商家详情页常见标题选择器
        (".shop-header .title",),
        ("[class*='shop-name']",),
        ("[class*='restaurant-name']",),
        ("h1",),
        ("h2",),
    ]
    try:
        body_text = page.inner_text("body")
        for sel_tuple in selectors:
            try:
                el = page.locator(sel_tuple[0]).first
                if el.count() > 0:
                    text = el.inner_text(timeout=1000).strip()
                    if text:
                        return text
            except Exception:
                continue
        # 兜底：从 body 文本中尝试提取第一行有意义的文本
        lines = [l.strip() for l in body_text.split("\n") if l.strip()]
        for line in lines[:5]:
            if len(line) > 2 and len(line) < 30:
                return line
    except Exception:
        pass
    return None


if __name__ == "__main__":
    main()