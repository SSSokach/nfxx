# AI办公助手 Demo

一个简洁的AI办公助手聊天Demo，支持消息收发、邮件管理、文件管理和AI助手功能。

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
├── ai-assistant-tech-spec.md # 智能助手功能技术规范
├── start.sh / restart.sh    # 后端启动/重启脚本
├── backend/                # 后端代码
│   ├── app.py              # FastAPI应用入口（含轻量级 DB 迁移）
│   ├── models.py           # SQLAlchemy数据库模型
│   ├── init_db.py          # 数据库初始化脚本
│   ├── glm_ai.py           # GLM 大模型调用层（含 skills）
│   ├── skills.py           # AI skill 注册表（含邮件摘要 skill）
│   ├── requirements.txt    # Python依赖列表
│   └── routes/             # API路由模块
│       ├── users.py        # 用户管理API
│       ├── chats.py        # 聊天消息API
│       ├── files.py        # 文件管理API
│       ├── emails.py       # 邮件 API（列表/详情/发送/加入待办）
│       ├── todos.py        # 待办与候选待办 API（消息+邮件合并扫描）
│       ├── ai.py           # AI助手API
│       └── ...
└── frontend/               # 前端代码
    ├── index.html          # HTML入口
    ├── package.json        # Node.js依赖配置
    ├── vite.config.js      # Vite配置（含代理）
    └── src/
        ├── main.js         # Vue应用入口
        ├── App.vue         # 根组件（含 viewMode 切换：消息/邮箱）
        ├── style.css       # 全局样式
        ├── api/
        │   └── index.js    # API接口封装
        └── components/
            ├── ContactList.vue  # 联系人列表（含视图切换按钮）
            ├── ChatArea.vue     # 聊天区域组件
            ├── EmailList.vue    # 邮件列表组件（左栏）
            ├── EmailDetail.vue  # 邮件详情/写邮件组件（中栏）
            └── AIPanel.vue      # AI助手面板组件（含消息+邮件待办合并）
```

## 功能特性

### 聊天功能
- ✅ 联系人/群组列表展示
- ✅ 消息收发（文本）
- ✅ Markdown文件上传、预览和编辑
- ✅ 用户切换（下拉框选择）
- ✅ 右键菜单：复制/回复/转发/收藏/AI对话/多选

### 邮箱功能（新增）
- ✅ 左上角视图切换按钮（💬 消息 / ✉️ 邮箱）
- ✅ 收件箱 / 已发送 / 写邮件 三个模块
- ✅ 邮件内容支持 Markdown 与纯文本两种格式
- ✅ 邮件附件支持（引用已有文件作为附件）
- ✅ 写邮件实时 Markdown 预览
- ✅ 邮件列表右键菜单：🤖 AI对话 / 📋 加入待办
- ✅ AI对话引用邮件正文与附件内容一同发送给大模型
- ✅ 加入待办直接进入正式待办列表（不经过候选阶段）

### AI助手功能
- ✅ 读取当前用户与联系人的聊天记录
- ✅ 替当前用户向联系人发送消息
- ✅ 获取在线文件内容
- ✅ 文件摘要 / 工作报告生成（通过自然语言对话）
- ✅ 邮件摘要 skill（新增）：引用邮件后输入"总结这封邮件"等触发
- ✅ 工具注册机制，支持后续复杂功能扩展

### 待办功能（消息+邮件合并）
- ✅ 候选待办（顶部）+ 正式待办（底部）双栏布局
- ✅ AI 扫描：同时扫描消息与邮件，将新增内容加入候选待办
- ✅ 候选待办确认：邮件候选确认 → 创建 EmailTodoItem；消息候选确认 → 创建 ChatTodoItem
- ✅ 待办 tag 区分消息来源（✉️ 邮件 / 💬 私聊 / 👥 群聊）
- ✅ 完成 / 删除 / 超期标红

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
- **示例邮件**: 收件箱 6 封（含 1 封带 Markdown 附件的周报），已发送 2 封

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

或使用启动脚本：

```bash
./start.sh      # 后台启动，PID 写入 nohup.pid，日志输出到 backend.log
./restart.sh    # 重启服务
```

后端服务将在 `http://localhost:8000` 运行，支持代码热更新。
首次启动时会自动执行轻量级 DB 迁移（为已有表添加 folder / body_type / attachment_file_ids / source_email_id 等列）。

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
## 下载依赖（x86架构）
pip3 download -r requirements.txt  -d packages_x86
## 下载依赖（ARM架构）
pip3 download -r requirements.txt  --platform manylinux2014_aarch64  --only-binary=:all:   -d ./packages_arm

cd /home/longbook/nfxx
zip -r backend-deploy.zip backend/ frontend/dist/ README.md start.sh restart.sh
```

### 4. 服务器上安装依赖

```bash
cd backend
## 安装 x86 架构依赖
pip3 install --no-index --find-links=packages_x86 -r requirements.txt
## 安装 ARM 架构依赖
pip3 install --no-index --find-links=packages_arm -r requirements.txt
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

### 邮件管理（新增）
- `GET /api/emails/list/{user_id}?folder=inbox|sent|draft` - 获取邮件列表（支持按文件夹过滤）
- `GET /api/emails/detail/{email_id}` - 获取邮件详情（含附件内容）
- `POST /api/emails/send/{user_id}` - 发送新邮件（body: `{to, subject, content, body_type, attachment_file_ids}`）
- `POST /api/emails/add-to-todo/{user_id}/{email_id}` - 将邮件直接加入待办列表
- `POST /api/emails/scan/{user_id}` - 扫描邮件生成邮件待办
- `GET /api/emails/todos/{user_id}` - 获取邮件待办列表
- `PUT /api/emails/todos/{todo_id}?action=complete|delete|restore|extend` - 更新邮件待办状态

### 待办管理
- `POST /api/todos/scan-messages/{user_id}` - 扫描消息生成摘要/待办
- `GET /api/todos/chat-todos/{user_id}?status=pending|completed|deleted` - 获取消息待办
- `PUT /api/todos/chat-todos/{todo_id}?action=complete|delete|restore|extend` - 更新消息待办
- `POST /api/todos/create-from-message/{user_id}/{message_id}` - 从消息直接创建待办
- `POST /api/todos/scan-candidates/{user_id}` - AI 扫描消息+邮件，生成候选待办
- `GET /api/todos/candidates/{user_id}` - 获取候选待办列表
- `POST /api/todos/candidates/{candidate_id}/confirm` - 确认候选（邮件→EmailTodoItem，消息→ChatTodoItem）
- `POST /api/todos/candidates/{candidate_id}/dismiss` - 忽略候选

### AI助手
- `GET /api/ai/tools` - 获取可用工具列表
- `POST /api/ai/call_tool` - 调用工具
- `POST /api/ai/chat` - AI聊天接口（支持 skill 路由，含邮件摘要 skill）

## AI助手使用示例

在AI助手面板中输入以下指令：

- `read_messages 李四` - 读取与李四的聊天记录
- `send_message 李四 你好` - 向李四发送消息"你好"
- `get_file_content 项目计划` - 获取"项目计划.md"文件内容
- `list_files` - 列出当前用户的所有文件
- `list_contacts` - 列出当前用户的所有联系人
- 邮件右键 → AI对话 → 在输入框输入"总结这封邮件" - 触发邮件摘要 skill
