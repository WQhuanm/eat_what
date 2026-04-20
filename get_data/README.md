# 饿了么菜单抓取工具说明

## 1. 工具目标

`eleme_full_menu_scraper.py` 用于自动抓取饿了么 H5 的周边商家点餐菜单数据，输出为 JSON/CSV，核心可用字段包括：

- 商家：`shop_name`、`shop_id`、`shop_url`
- 菜品：`name`、`description`、`image_url`、`image_hash`、`price`、`month_sales`、`category`


## 2. 关键文件

- `eleme_full_menu_scraper.py`：主脚本（唯一建议运行脚本）
- `.generated/menus_around.json`：主结果（结构化）
- `.generated/menus_around.csv`：扁平化结果（Excel/BI 友好）
- `.generated/menus_debug.json`：调试摘要（成功失败明细、命中接口、菜品计数）
- `.generated/menus_meta.json`：本批次来源元数据（抓取位置与参数）
- `.playwright/eleme_state.json`：登录态缓存
- `temp_artifacts/`：历史调试脚本与中间文件归档


## 3. `menus_around.json` 与 `menus_debug.json` 区别

### `menus_around.json`（业务数据）

这是后续直接消费的数据源，每条商家记录都带 `menu` 菜品数组，里面是你需要的实际字段（名字、描述、图片等）。

### `menus_debug.json`（调试数据）

这是执行过程日志，不用于业务入库。主要用于排查：

- 某商家是否抓取成功（`ok`）
- 命中的接口 URL（`request_url`）
- 分类数与菜品数（`category_count`、`dish_count`）
- 失败原因（`error`）


## 4. 定位策略（已调整）

### 4.1 不传定位参数

- 不传 `--latitude/--longitude` 时，脚本按页面当前位置抓取。
- 前提：系统与浏览器的定位权限开启。

### 4.2 传定位参数

- 传入 `--latitude/--longitude` 时，脚本显式设置定位中心。
- 在权限不稳定或系统定位关闭时，建议显式传参。

示例：

```bash
python eleme_full_menu_scraper.py --limit 10 --latitude 31.2304 --longitude 121.4737 --timeout-ms 20000
```


## 5. 商家数量与 `--limit` 逻辑

`--limit` 是目标抓取数量，不是绝对保证值。当前逻辑：

1. 首页滚动收集商家标题（最多多轮滚动）
2. 逐个点击并抓取菜单
3. 若个别商家点击失败或菜单接口未命中，实际结果可能少于 `limit`

当实际不足时：

- 控制台会输出提示：`目标 X 家，实际抓到 Y 家`
- 默认继续输出已有结果
- 若传 `--strict-limit`，则会报错退出（适合自动化流程判失败重试）


## 6. 图片链接说明

- `image_url` 已按页面实际可访问规则生成到 `cube.elemecdn.com`
- 当前格式与页面中 `menuItem--image-img` 背景图一致
- `image_hash` 保留原始值，便于后续追溯或二次处理


## 7. 运行方法

### 7.1 常用运行（推荐）

```bash
python eleme_full_menu_scraper.py --limit 10 --timeout-ms 20000
```

### 7.2 指定经纬度运行

```bash
python eleme_full_menu_scraper.py --limit 10 --latitude 31.2304 --longitude 121.4737 --timeout-ms 20000
```

### 7.3 严格数量模式

```bash
python eleme_full_menu_scraper.py --limit 10 --strict-limit
```

### 7.4 登录态失效时手动登录

```bash
python eleme_full_menu_scraper.py --manual-login --limit 10 --timeout-ms 20000
```

脚本会先打开页面并暂停，等你手动登录后在终端按回车继续抓取。

### 7.5 每家仅保留热门菜品

```bash
python eleme_full_menu_scraper.py --limit 10 --max-dishes-per-shop 30
```

会按月售优先截断每家菜品，便于控制数据规模。


## 8. 环境要求

1. Python 3.10+
2. 已安装 `playwright`
3. 已安装 Chromium：

```bash
python -m playwright install chromium
```


## 9. 常见问题

### Q1：报“未获取到商家标题”

通常是定位权限或页面状态问题，建议：

1. 打开系统/浏览器定位权限
2. 先手动确认可在页面看到附近商家
3. 再运行脚本，必要时加显式经纬度

### Q2：图片链接偶发不可访问

平台资源可能有时效与风控，建议后处理阶段做一次 URL 探活并缓存可用链接。

### Q3：频繁跳验证页/登录页

新版脚本已优先使用商家卡片 `href` 直达，减少无效页面访问和滚动误触。  
若仍被风控：

1. 降低 `--limit`（先 5-10 家）
2. 增加抓取间隔（脚本内已加入基础等待）
3. 使用 `--manual-login` 完成验证后继续


## 10. 当前版本变更

- 删除了“距离范围筛选”功能（按你的要求移除）
- 保留并优化了“自动定位 / 显式定位”双模式
- 保留 `--strict-limit` 作为数量保障开关
- 新增 `--manual-login`，支持登录态失效后人工登录再继续
- 新增 `--max-dishes-per-shop`，支持按月售优先保留每家热门菜品
- 抓取结果默认写入 `get_data/.generated/`（Git 忽略目录）
- 新增 `--output-meta`，输出抓取元数据，供后续转换脚本复用
