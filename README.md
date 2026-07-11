# nfxx

AI Assistant Of The Non-Descending Gradient Team

## 设计文档
**[AI Office Assistant Demo Design Document](./.trae/documents/ai-office-assistant-demo.md)**
## 启动方式

### 开发模式 （前后端热更新）：

``` bash
# 终端1
cd backend && uvicorn app:app --reload --port 8000
# 终端2
cd frontend && npm run dev   # 打开 http://localhost:5173
```

### 部署模式 （前端内嵌后端）：

``` bash
# 终端1
cd frontend && npm run build
cd ../backend && uvicorn app:app --port 8000   # 打开 http://localhost:8000
```

使用前需 cp .env.example .env 并填入 OpenAI 兼容的 API Key、base_url 和 model。配置后 AI 助手即可通过工具调用读取聊天记录、替用户发消息、获取文件内容。
