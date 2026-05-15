# 今天吃什么 (Eat What)

## 项目简介
"今天吃什么" 是一个智能美食推荐系统，结合用户画像、问答权重、菜品向量等多维度信息，为用户提供个性化的美食推荐。系统包括：
- **后端服务**：基于 FastAPI 的 RESTful API。
- **小程序前端**：基于微信小程序的用户界面。
- **数据库**：使用 MySQL 存储用户、菜品、店铺等数据。

---

## 系统运行说明

### 1. 后端运行说明

#### 1.1 环境依赖
- **Python**：3.9+
- **数据库**：MySQL 8.0
- **依赖库安装**：
  ```bash
  cd backend && pip install -r requirements.txt
  ```

#### 1.2 数据库初始化
1. 确保 MySQL 数据库已安装并运行。
2. 创建数据库 `eat_what`：
   ```sql
   CREATE DATABASE eat_what CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. 修改 `d:\_Project_File\eat_what\backend\database.py` 中的 `DATABASE_URL`，配置为你的数据库连接信息：
   ```python
   DATABASE_URL = "mysql+pymysql://<username>:<password>@<host>:<port>/eat_what?charset=utf8mb4"
   ```
4. 自动建表：
   ```bash
   python -c "import models; from database import Base, engine; Base.metadata.create_all(bind=engine)"
   ```

若你是旧库结构，建议在测试环境重建空表（保留 users 表），再执行自动建表。

说明：

- 本项目使用 SQLAlchemy ORM 元数据自动建表。
- `Base.metadata.create_all(bind=engine)` 可重复执行，会创建缺失表，不会重复创建已存在表。
- 若你修改了模型字段，`create_all` 不会自动迁移历史表结构（只负责“创建不存在的表”）。

#### 1.3 启动后端服务
运行以下命令启动后端服务：
```bash
python d:\_Project_File\eat_what\backend\main.py
```
默认服务运行在 `http://localhost:8000`。

#### 1.4 测试后端接口
- 打开浏览器访问 `http://localhost:8000/docs` 查看 Swagger 文档。
- 使用 Postman 或其他工具测试接口。

---

### 2. 小程序端运行说明

#### 2.1 环境依赖
- **微信开发者工具**：最新版。
- **小程序 AppID**：需要在微信公众平台申请。

#### 2.2 配置小程序项目
1. 打开微信开发者工具，选择“导入项目”。
2. 选择 `d:\_Project_File\eat_what\frontend` 目录。
3. 在 `project.config.json` 中填写你的 AppID：
   ```json
   {
     "appid": "your-app-id"
   }
   ```

#### 2.3 配置后端地址
修改 `d:\_Project_File\eat_what\frontend\app.js` 中的 `baseUrl`，指向后端服务地址：
```javascript
globalData: {
  baseUrl: 'http://<your-backend-ip>:8000',
  ...
}
```

#### 2.4 运行小程序
1. 在微信开发者工具中点击“预览”或“真机调试”。
2. 使用微信扫码登录小程序。

---

## 功能验证流程

### 1. 用户注册与登录
1. 打开小程序，进入登录页面。
2. 点击“注册”，填写用户名和密码完成注册。
3. 注册成功后返回登录页面，输入用户名和密码登录。

### 2. 编辑个人画像
1. 登录后进入“我的”页面。
2. 点击“编辑个人画像”，填写基础信息、健康目标、饮食禁忌等，点击保存。

### 3. 添加店铺与菜品
1. 在“我的”页面点击“添加店铺”，填写店铺信息并保存。
2. 点击“提交菜品”，填写菜品信息并关联店铺，上传图片后保存。

### 4. 智能推荐
1. 在首页点击“看看今天吃什么”，进入问答页面。
2. 完成增强版问答后提交，系统会将答案转成用户即时向量并召回推荐。
3. 推荐排序综合向量匹配、距离惩罚、历史平滑。
4. 若问卷题目加载失败，页面会显示“重新加载”按钮；点击后可重试拉取题目（不再出现空白页）。
5. 在推荐结果页点击“就它了”后，系统记录选择并直接切回首页，避免深页面栈导致后续页面卡顿。

### 5. 查看历史记录
1. 在“我的”页面点击“我的历史记录”。
2. 查看历史选择记录，点击“再来一次”重新选择。

### 6. 增强版问答字段说明（已实现）

- 题型：单选、多选、滑条（0~5）。
- 核心字段：`meal_time`、`dining_scene`、`dining_goal`、`decision_style`、`dining_form`、`budget`、`cuisine_preference`。
- 强度字段（可选）：`spicy_level`、`numbing_level`、`sour_level`、`sweet_level`、`salty_level`、`oily_level`（均为 0~5 滑块，不选表示无特别偏好）。
- 向量化：后端将上述问答字段与用户画像信息拼接为结构化语义文本，并叠加衍生特征（饱腹度/浓郁度/社交属性）生成用户向量。

---

### 7. 向量化服务（本地实现）

后端已内置 `nlp-service` 风格接口，无需额外微服务。

- 接口地址：`POST http://localhost:8000/v1/vectorize`
- 请求体可直接传 `text`，也可传结构化字段（name/cuisine/taste_tags/taste_scores 等）
- 优先使用 `sentence-transformers` 模型（默认 `shibing624/text2vec-base-chinese`）
- 若模型不可用，服务返回 503，拒绝继续向量化与后续写库操作

可通过环境变量调整：

- `NLP_MODEL_NAME`：sentence-transformers 模型名
- `DISH_VECTOR_DIM`：向量维度（默认 768）
- `NLP_VECTOR_URL`：若你接入外部向量服务时可覆盖调用地址

#### 如何让本地模型可用

1. 安装依赖：

```bash
cd d:\_Project_File\eat_what\backend && pip install -r requirements.txt
```

2. 预下载模型文件（联网环境执行一次）：

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('shibing624/text2vec-base-chinese')"
```

3. 启动后端：

```bash
python d:\_Project_File\eat_what\backend\main.py
```

4. 访问接口验证模型状态（Swagger 或 curl/Postman）：

- `POST http://localhost:8000/v1/vectorize`
- 示例请求体：

```json
{
  "text": "菜名:麻婆豆腐\n菜系:川湘菜\n口味标签:辣,咸\n描述:香辣下饭",
  "vector_dim": 768
}
```

5. 判定标准：

- 返回 200 且 `model` 不是 `unavailable`，说明模型可用。
- 返回 503，说明模型未加载成功（依赖或模型下载问题），系统会拒绝向量化写库。

说明：后端默认使用 `local_files_only=True` 加载模型，不会在运行时自动联网下载，避免启动阻塞。
