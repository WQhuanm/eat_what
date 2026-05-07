# 运行指南

## 环境准备

```bash
pip install playwright
python -m playwright install chromium
```

## 参数说明

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--limit` | `1` | 抓取商家数量 |
| `--latitude` | 系统定位 | 纬度（需与 longitude 同时提供）|
| `--longitude` | 系统定位 | 经度（需与 latitude 同时提供）|
| `--interval-ms` | `5000` | 操作间隔（毫秒），防风控 |
| `--timeout-ms` | `30000` | 页面导航超时（毫秒）|
| `--state-file` | `.playwright/eleme_state.json` | 登录态文件路径 |
| `--output-json` | `.generated/menus_around.json` | 输出 JSON 路径 |

## 命令示例

### 首次运行（需要手动登录）

```bash
python eleme_full_menu_scraper.py
```

### 强制指定坐标

```bash
python eleme_full_menu_scraper.py --latitude 30.318882 --longitude 120.347132
```


### 提取获取数据中的商家名称

```bash
python extract_shop_names.py
```