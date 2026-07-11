# AI 办公助手 Demo 实现计划

## Context

用户需要一个简洁的 AI 办公助手 Demo，展示 AI 与即时通讯结合的场景。前端三栏布局（联系人/聊天/AI助手），后端提供消息收发、文件管理、AI 工具编排能力。项目当前为空仓库（仅有 README 和 .gitignore），需从零搭建。

**核心目标**：轻量、可运行、可扩展的 Demo，验证 AI 助手通过工具调用融入办公通讯的工作流。

**用户确认的决策**：

* AI 接入：OpenAI 兼容接口（通过环境变量配置 base\_url / api\_key / model）

* 工具编排：可扩展工具注册框架（新增工具只需注册描述+处理函数）

* 数据模式：预置初始数据 + 模拟实时（轮询刷新，不用 WebSocket）

* Markdown：轻量方案（marked.js 解析渲染 + textarea 编辑）

***

## 技术栈

| 层        | 技术                       | 说明                                   |
| -------- | ------------------------ | ------------------------------------ |
| 前端       | Vue3 + Vite              | 三栏布局，Pinia 管理共享状态                    |
| 后端       | Python FastAPI + uvicorn | 支持 --reload 热更新，自带静态文件服务             |
| 数据库      | SQLite                   | 通过 Python 标准库 sqlite3 操作             |
| LLM      | OpenAI 兼容接口              | 通过 openai SDK 调用，支持 function calling |
| Markdown | marked.js + textarea     | 轻量编辑/预览切换                            |

***

## 项目结构

```
nfxx/
├── backend/
│   ├── app.py              # FastAPI 应用、所有 API 路由、静态文件服务
│   ├── database.py         # 数据库初始化、表结构、预置数据
│   ├── ai.py               # LLM 客户端 + 工具注册框架 + 内置工具
│   ├── requirements.txt    # Python 依赖
│   └── static/             # 部署时前端构建产物（开发时为空）
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js
│       ├── App.vue         # 三栏布局容器 + 用户切换
│       ├── stores/
│       │   └── app.js      # Pinia store（当前用户、当前聊天、消息列表）
│       ├── api/
│       │   └── index.js    # axios 封装的 API 客户端
│       └── components/
│           ├── ContactList.vue    # 左栏：联系人/群列表
│           ├── ChatArea.vue       # 中栏：聊天主区
│           ├── MessageItem.vue    # 单条消息（文本/文件）
│           ├── MarkdownEditor.vue # Markdown 编辑/预览组件
│           ├── AIAssistant.vue    # 右栏：AI 对话
│           └── UserSwitcher.vue   # 顶部用户切换下拉框
├── .env.example            # 环境变量示例
├── README.md
└── .gitignore
```

***

## 数据库设计

使用 SQLite，4 张表：

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    avatar TEXT DEFAULT ''  -- 头像 URL 或首字母
);

-- 群组表
CREATE TABLE groups (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    avatar TEXT DEFAULT ''
);

-- 群成员表
CREATE TABLE group_members (
    group_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (group_id, user_id)
);

-- 消息表（文本和文件统一存储）
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,         -- 发送者用户 ID
    receiver_type TEXT NOT NULL,        -- 'user' | 'group'
    receiver_id INTEGER NOT NULL,       -- 接收者 ID
    content TEXT NOT NULL,              -- 文本内容 或 markdown 文件内容
    msg_type TEXT NOT NULL,             -- 'text' | 'file'
    file_name TEXT DEFAULT '',          -- 文件类型时的文件名
    created_at TEXT NOT NULL            -- ISO 时间戳
);
```

**预置数据**：

* 用户：张三、李四、王五、赵六

* 群组：技术讨论组（全员）、项目协作组（张三、李四、王五）

* 初始消息：用户间和群组中各预置若干条对话，含一个 markdown 文件消息

***

## API 设计

所有 API 以 `/api` 为前缀。

### 用户与联系人

| 方法  | 路径                              | 说明                       |
| --- | ------------------------------- | ------------------------ |
| GET | `/api/users`                    | 获取所有用户（用于切换用户下拉框）        |
| GET | `/api/users/{user_id}/contacts` | 获取该用户的联系人列表（其他用户 + 所属群组） |

### 消息

| 方法   | 路径                                                                | 说明                                                                                   |
| ---- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| GET  | `/api/messages?user_id={id}&peer_type={user\|group}&peer_id={id}` | 获取与某联系人/群组的聊天记录                                                                      |
| POST | `/api/messages`                                                   | 发送消息（body: sender\_id, receiver\_type, receiver\_id, content, msg\_type, file\_name） |
| GET  | `/api/files/{message_id}`                                         | 获取文件消息的 markdown 内容                                                                  |
| PUT  | `/api/files/{message_id}`                                         | 编辑文件消息的 markdown 内容                                                                  |

### AI 助手

| 方法   | 路径             | 说明                                                        |
| ---- | -------------- | --------------------------------------------------------- |
| POST | `/api/ai/chat` | 与 AI 对话（body: user\_id, message）。AI 可调用工具，返回最终回复 + 工具调用记录 |

***

## AI 工具注册框架（核心）

设计在 `backend/ai.py` 中，基于 OpenAI function calling 格式：

```python
class ToolRegistry:
    """工具注册中心：注册描述 schema + 处理函数，供 LLM 调用"""
    def register(self, name, description, parameters, handler): ...
    def get_schemas(self) -> list: ...  # 返回 OpenAI tools 格式
    def execute(self, name, arguments) -> str: ...  # 执行工具，返回结果字符串

# 内置工具（注册时绑定当前 user_id 上下文）
registry.register(
    name="read_chat_history",
    description="读取当前用户与指定联系人/群组的聊天记录",
    parameters={...},
    handler=lambda args: read_chat(user_id, args)
)
registry.register(
    name="send_message",
    description="替当前用户向联系人或群组发送消息",
    parameters={...},
    handler=lambda args: send_message(user_id, args)
)
registry.register(
    name="get_file_content",
    description="获取指定文件消息的 markdown 内容",
    parameters={...},
    handler=lambda args: get_file(args)
)
```

**AI 对话流程**（`POST /api/ai/chat`）：

1. 接收 user\_id + message，为该用户创建 ToolRegistry 实例（绑定 user\_id 上下文）
2. 构造 system prompt（当前用户身份 + 可用工具说明）
3. 调用 LLM，若返回 tool\_calls 则执行对应工具，将结果喂回 LLM
4. 循环直到 LLM 返回文本回复（最多 5 轮，防止死循环）
5. 返回 `{ reply, tool_calls: [...] }` 给前端展示

**扩展方式**：新增工具只需调用 `registry.register(name, desc, params, handler)`，无需改动其他代码。

***

## 前端关键设计

### 状态管理（Pinia store）

```js
// stores/app.js
- currentUser: 当前登录用户（默认张三）
- currentChat: 当前激活的聊天对象 { type, id, name }
- messages: 当前聊天的消息列表
```

### 三栏布局（App.vue）

```
┌─────────────────────────────────────────────┐
│  顶部栏：AI 办公助手 Demo    [UserSwitcher]  │
├──────────┬──────────────────┬───────────────┤
│          │                  │               │
│ Contact  │   ChatArea       │  AIAssistant  │
│ List     │   (消息列表+      │  (AI 对话+    │
│ (联系人  │    输入框)        │   工具调用     │
│  /群)    │                  │   展示)       │
│          │                  │               │
└──────────┴──────────────────┴───────────────┘
```

### 组件职责

* **ContactList.vue**：展示联系人/群列表，点击切换 currentChat，触发消息加载

* **ChatArea.vue**：消息列表 + 输入框，支持发送文本和 markdown 文件；点击文件消息弹出 MarkdownEditor

* **MessageItem.vue**：区分文本/文件消息样式，文件消息显示文件名+预览按钮

* **MarkdownEditor.vue**：弹窗形式，左侧 textarea 编辑、右侧 marked.js 渲染预览，支持保存

* **AIAssistant.vue**：AI 对话界面，展示 AI 回复和工具调用过程（折叠展示）

* **UserSwitcher.vue**：下拉框切换当前用户，切换后刷新联系人列表和消息

### 消息刷新策略

* 发送消息后立即刷新消息列表

* 切换聊天对象时加载对应消息

* 可选：5 秒轮询当前聊天消息（模拟实时）

***

## 开发与部署

### 开发模式（前后端独立热更新）

```bash
# 终端1 - 后端
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# 终端2 - 前端
cd frontend
npm install
npm run dev   # Vite dev server，代理 /api 到 localhost:8000
```

`vite.config.js` 配置代理：

```js
server: {
  proxy: { '/api': 'http://localhost:8000' }
}
```

### 部署模式（前端内嵌后端）

```bash
cd frontend && npm run build   # 产物输出到 ../backend/static
cd ../backend && uvicorn app:app --port 8000  # 单服务启动
```

`app.py` 中静态文件路径用绝对路径（基于 `__file__`）：

```python
StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"))
```

### 环境变量（.env.example）

```
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

***

## 依赖清单

### 后端（requirements.txt）

```
fastapi
uvicorn[standard]
openai
python-dotenv
```

### 前端（package.json）

```
vue@3
pinia
axios
marked
vite
@vitejs/plugin-vue
```

***

## 实现步骤

1. **后端骨架**：创建 `backend/app.py`、`database.py`、`ai.py`，初始化 FastAPI + SQLite + 预置数据
2. **后端 API**：实现用户、联系人、消息、文件的 CRUD 路由
3. **AI 工具框架**：实现 ToolRegistry + 3 个内置工具 + LLM 对话接口
4. **前端骨架**：创建 Vite + Vue3 项目，配置代理，搭建三栏布局
5. **前端组件**：实现 ContactList、ChatArea、MessageItem、UserSwitcher
6. **Markdown 组件**：实现 MarkdownEditor 编辑/预览
7. **AI 助手组件**：实现 AIAssistant 对话 + 工具调用展示
8. **联调测试**：前后端联调，验证所有功能
9. **README 更新**：补充启动说明

***

## 验证方式

1. **启动后端**：`cd backend && uvicorn app:app --reload`，访问 `http://localhost:8000/api/users` 返回用户列表
2. **启动前端**：`cd frontend && npm run dev`，浏览器打开 Vite 提示的地址
3. **功能验证**：

   * 左栏显示联系人和群组，点击切换聊天

   * 中栏发送文本消息和 markdown 文件，文件可点击预览编辑

   * 顶部下拉框切换用户，联系人列表和消息刷新

   * 右栏 AI 对话：问"帮我看看和张三的聊天记录"，AI 调用 read\_chat\_history 工具并总结

   * 问"帮我给技术讨论组发一条消息：会议改到下午3点"，AI 调用 send\_message 工具
4. **部署验证**：`npm run build` 后 `uvicorn app:app`，单端口访问完整应用

