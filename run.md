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
- **数据库**：MySQL 5.7+ 或 MariaDB
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
2. 完成问答后查看推荐结果，选择心仪的菜品。

### 5. 查看历史记录
1. 在“我的”页面点击“我的历史记录”。
2. 查看历史选择记录，点击“再来一次”重新选择。

---

## 注意事项
1. **后端服务需公网可访问**：
   - 如果后端部署在本地，需配置内网穿透工具（如 ngrok）或云服务器。
2. **小程序合法域名配置**：
   - 在微信公众平台配置后端服务地址为合法域名。
3. **NLP 模型服务**：
   - 菜品向量生成依赖 NLP 模型服务，需确保 `http://nlp-service/v1/vectorize` 可用。

---

## 常见问题
1. **后端无法连接数据库**：
   - 检查 `DATABASE_URL` 配置是否正确。
   - 确保数据库服务已启动，用户权限正确。
2. **小程序无法访问后端**：
   - 检查后端服务是否运行，确保合法域名已配置。
3. **推荐结果为空**：
   - 确保数据库中有足够的菜品数据，且菜品信息完整（如向量字段）。

---

至此，系统已完整实现并可正常运行。