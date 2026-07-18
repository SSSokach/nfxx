# AI办公助手 Demo

一个简洁的AI办公助手聊天Demo，支持消息收发、文件管理和AI助手功能。

## 技术栈

### 前端
- Vue 3 + Vite
- Axios（HTTP请求）
- Marked（Markdown渲染）

### 后端
- FastAPI
- SQLAlchemy（ORM）
- SQLite（数据库）

## 项目结构

```
nfxx/
├── README.md               # 项目说明文档
├── backend/                # 后端代码
│   ├── app.py              # FastAPI应用入口
│   ├── models.py           # SQLAlchemy数据库模型
│   ├── init_db.py          # 数据库初始化脚本
│   ├── requirements.txt    # Python依赖列表
│   └── routes/             # API路由模块
│       ├── users.py        # 用户管理API
│       ├── chats.py        # 聊天消息API
│       ├── files.py        # 文件管理API
│       └── ai.py           # AI助手API
└── frontend/               # 前端代码
    ├── index.html          # HTML入口
    ├── package.json        # Node.js依赖配置
    ├── vite.config.js      # Vite配置（含代理）
    └── src/
        ├── main.js         # Vue应用入口
        ├── App.vue         # 根组件
        ├── style.css       # 全局样式
        ├── api/
        │   └── index.js    # API接口封装
        └── components/
            ├── ContactList.vue   # 联系人列表组件
            ├── ChatArea.vue      # 聊天区域组件
            └── AIPanel.vue       # AI助手面板组件
```

## 功能特性

### 聊天功能
- ✅ 联系人/群组列表展示
- ✅ 消息收发（文本）
- ✅ Markdown文件上传、预览和编辑
- ✅ 用户切换（下拉框选择）

### AI助手功能
- ✅ 读取当前用户与联系人的聊天记录
- ✅ 替当前用户向联系人发送消息
- ✅ 获取在线文件内容
- ✅ 工具注册机制，支持后续复杂功能扩展

## 环境要求

- Python 3.10+
- Node.js 18+

## 安装步骤

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt --break-system-packages
```

### 2. 初始化数据库

```bash
cd backend
python3 init_db.py
```

数据库初始化后会自动创建以下测试数据：

- **用户**: 张三、李四、王五（可通过下拉框切换）
- **联系人**: 李四、王五（个人），项目组、技术讨论群（群组）
- **示例消息**: 各联系人/群组已有若干历史消息
- **示例文件**: 项目计划.md、技术文档.md（Markdown格式）

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

## 开发模式（前后端热更新）

### 启动后端服务

```bash
cd backend
python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 运行，支持代码热更新。

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端将在 `http://localhost:5173` 运行，通过Vite代理将API请求转发到后端。

访问地址：`http://localhost:5173/`

## 部署模式（前端内嵌后端）

### 1. 构建前端

```bash
cd frontend
npm run build
```

构建产物将输出到 `frontend/dist` 目录。

### 2. 启动后端服务

```bash
cd backend
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

后端将自动提供前端静态文件，直接访问 `http://localhost:8000` 即可。

### 3. 打包，部署到服务器

```bash
cd /home/longbook/nfxx/backend
mkdir packages
pip3 download -r requirements.txt -d packages

cd /home/longbook/nfxx
zip -r backend-deploy.zip backend/ frontend/dist/ README.md
```

### 4. 服务器上安装依赖

```bash
cd backend
pip3 install --no-index --find-links=packages -r requirements.txt
```

### 5. 启动后端服务

```bash
cd /home/longbook/nfxx/backend
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## API接口

### 用户管理
- `GET /api/users` - 获取所有用户
- `GET /api/users/{user_id}` - 获取单个用户

### 聊天管理
- `GET /api/chats/contacts/{user_id}` - 获取联系人列表
- `GET /api/chats/messages?user_id=&contact_id=` - 获取消息列表
- `POST /api/chats/send?user_id=&contact_id=&content=` - 发送消息

### 文件管理
- `GET /api/files/{user_id}` - 获取文件列表
- `GET /api/files/content/{file_id}` - 获取文件内容
- `POST /api/files/save` - 保存文件
- `PUT /api/files/update/{file_id}` - 更新文件

### AI助手
- `GET /api/ai/tools` - 获取可用工具列表
- `POST /api/ai/call_tool` - 调用工具
- `POST /api/ai/chat` - AI聊天接口

## AI助手使用示例

在AI助手面板中输入以下指令：

- `read_messages 李四` - 读取与李四的聊天记录
- `send_message 李四 你好` - 向李四发送消息"你好"
- `get_file_content 项目计划` - 获取"项目计划.md"文件内容
- `list_files` - 列出当前用户的所有文件
- `list_contacts` - 列出当前用户的所有联系人
