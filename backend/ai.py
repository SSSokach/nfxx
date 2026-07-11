"""AI 助手：LLM 客户端 + 可扩展工具注册框架。"""

import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


class ToolRegistry:
    """工具注册中心：注册描述 schema + 处理函数，供 LLM function calling 调用。"""

    def __init__(self):
        self._tools = {}

    def register(self, name, description, parameters, handler):
        """注册一个工具。

        Args:
            name: 工具名称（唯一）
            description: 工具描述（给 LLM 看的）
            parameters: JSON Schema 格式的参数描述
            handler: 处理函数，接收 dict 参数，返回 str 结果
        """
        self._tools[name] = {
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    def get_schemas(self):
        """返回 OpenAI tools 格式的工具列表。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for name, t in self._tools.items()
        ]

    def execute(self, name, arguments):
        """执行工具，返回结果字符串。"""
        tool = self._tools.get(name)
        if not tool:
            return f"工具 {name} 不存在"
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            return tool["handler"](args)
        except Exception as e:
            return f"工具执行出错: {e}"


def build_registry(user_id, user_name):
    """为指定用户构建工具注册实例，绑定用户上下文。"""
    import database

    registry = ToolRegistry()

    def read_chat_history(args):
        peer_type = args.get("peer_type", "user")
        peer_name = args.get("peer_name", "")
        limit = min(args.get("limit", 20), 50)

        conn = database.get_conn()
        c = conn.cursor()

        # 通过名字查找 peer
        if peer_type == "user":
            row = c.execute("SELECT id, name FROM users WHERE name LIKE ?", (f"%{peer_name}%",)).fetchone()
            if not row:
                return f"未找到用户：{peer_name}"
            peer_id = row["id"]
        else:
            row = c.execute("SELECT id, name FROM groups WHERE name LIKE ?", (f"%{peer_name}%",)).fetchone()
            if not row:
                return f"未找到群组：{peer_name}"
            peer_id = row["id"]

        # 查询双向消息
        if peer_type == "user":
            msgs = c.execute(
                "SELECT m.*, u.name as sender_name FROM messages m "
                "JOIN users u ON m.sender_id = u.id "
                "WHERE (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?) "
                "OR (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?) "
                "ORDER BY m.created_at ASC LIMIT ?",
                (user_id, peer_id, peer_id, user_id, limit),
            ).fetchall()
        else:
            msgs = c.execute(
                "SELECT m.*, u.name as sender_name FROM messages m "
                "JOIN users u ON m.sender_id = u.id "
                "WHERE m.receiver_type = 'group' AND m.receiver_id = ? "
                "ORDER BY m.created_at ASC LIMIT ?",
                (peer_id, limit),
            ).fetchall()

        conn.close()
        if not msgs:
            return f"没有与{peer_name}的聊天记录"

        lines = []
        for m in msgs:
            tag = f"[{m['msg_type']}]" if m["msg_type"] == "file" else ""
            fname = f" ({m['file_name']})" if m["file_name"] else ""
            lines.append(f"{m['sender_name']}: {m['content']}{fname}{tag}")
        return f"与{peer_name}的最近{len(msgs)}条消息：\n" + "\n".join(lines)

    def send_message(args):
        peer_type = args.get("peer_type", "user")
        peer_name = args.get("peer_name", "")
        content = args.get("content", "")

        if not content:
            return "发送内容不能为空"

        conn = database.get_conn()
        c = conn.cursor()

        if peer_type == "user":
            row = c.execute("SELECT id, name FROM users WHERE name LIKE ?", (f"%{peer_name}%",)).fetchone()
            if not row:
                conn.close()
                return f"未找到用户：{peer_name}"
            peer_id = row["id"]
            peer_display = row["name"]
        else:
            row = c.execute("SELECT id, name FROM groups WHERE name LIKE ?", (f"%{peer_name}%",)).fetchone()
            if not row:
                conn.close()
                return f"未找到群组：{peer_name}"
            peer_id = row["id"]
            peer_display = row["name"]

        c.execute(
            "INSERT INTO messages (sender_id, receiver_type, receiver_id, content, msg_type, file_name, created_at) "
            "VALUES (?, ?, ?, ?, 'text', '', ?)",
            (user_id, peer_type, peer_id, content, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return f"已成功替你向{peer_display}发送消息：{content}"

    def get_file_content(args):
        file_name = args.get("file_name", "")
        peer_name = args.get("peer_name", "")

        conn = database.get_conn()
        c = conn.cursor()

        msg = None
        # 先尝试按联系人 + 文件名查找
        if file_name and peer_name:
            peer = c.execute(
                "SELECT id FROM users WHERE name LIKE ?", (f"%{peer_name}%",)
            ).fetchone()
            if peer:
                peer_id = peer["id"]
                msg = c.execute(
                    "SELECT * FROM messages WHERE msg_type = 'file' AND file_name LIKE ? "
                    "AND ((sender_id = ? AND receiver_type = 'user' AND receiver_id = ?) "
                    "OR (sender_id = ? AND receiver_type = 'user' AND receiver_id = ?)) "
                    "ORDER BY created_at DESC LIMIT 1",
                    (f"%{file_name}%", user_id, peer_id, peer_id, user_id),
                ).fetchone()
            if not msg:
                group = c.execute(
                    "SELECT id FROM groups WHERE name LIKE ?", (f"%{peer_name}%",)
                ).fetchone()
                if group:
                    msg = c.execute(
                        "SELECT * FROM messages WHERE msg_type = 'file' AND file_name LIKE ? "
                        "AND receiver_type = 'group' AND receiver_id = ? "
                        "ORDER BY created_at DESC LIMIT 1",
                        (f"%{file_name}%", group["id"]),
                    ).fetchone()

        # 仅按文件名查找
        if not msg and file_name:
            msg = c.execute(
                "SELECT * FROM messages WHERE msg_type = 'file' AND file_name LIKE ? "
                "ORDER BY created_at DESC LIMIT 1",
                (f"%{file_name}%",),
            ).fetchone()

        # 获取最近的文件
        if not msg and not file_name:
            msg = c.execute(
                "SELECT * FROM messages WHERE msg_type = 'file' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()

        conn.close()
        if not msg:
            return "未找到匹配的文件"

        return f"文件名：{msg['file_name']}\n内容：\n{msg['content']}"

    registry.register(
        name="read_chat_history",
        description="读取当前用户与指定联系人或群组的聊天记录。可用于了解沟通上下文。",
        parameters={
            "type": "object",
            "properties": {
                "peer_type": {
                    "type": "string",
                    "enum": ["user", "group"],
                    "description": "对方类型：user 为私聊，group 为群聊",
                },
                "peer_name": {
                    "type": "string",
                    "description": "对方用户名或群组名（支持模糊匹配）",
                },
                "limit": {
                    "type": "integer",
                    "description": "读取的最大消息条数，默认20",
                    "default": 20,
                },
            },
            "required": ["peer_type", "peer_name"],
        },
        handler=read_chat_history,
    )

    registry.register(
        name="send_message",
        description="替当前用户向联系人或群组发送一条文本消息。",
        parameters={
            "type": "object",
            "properties": {
                "peer_type": {
                    "type": "string",
                    "enum": ["user", "group"],
                    "description": "对方类型：user 为私聊，group 为群聊",
                },
                "peer_name": {
                    "type": "string",
                    "description": "对方用户名或群组名（支持模糊匹配）",
                },
                "content": {
                    "type": "string",
                    "description": "要发送的消息内容",
                },
            },
            "required": ["peer_type", "peer_name", "content"],
        },
        handler=send_message,
    )

    registry.register(
        name="get_file_content",
        description="获取聊天中分享的 markdown 文件内容。",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "文件名（支持模糊匹配），不填则获取最近的文件",
                },
                "peer_name": {
                    "type": "string",
                    "description": "对方用户名或群组名，用于缩小查找范围（可选）",
                },
            },
        },
        handler=get_file_content,
    )

    return registry


SYSTEM_PROMPT_TEMPLATE = """你是一个智能办公助手，当前正在为用户「{user_name}」服务。

你可以通过调用工具来帮助用户：
1. 读取聊天记录：了解用户与同事的沟通上下文
2. 发送消息：替用户向联系人或群组发送消息
3. 获取文件内容：查看聊天中分享的 markdown 文件

原则：
- 用户提到的联系人姓名可能是简称，调用工具时用 peer_name 模糊匹配即可
- 发送消息前确认内容，如果是用户明确要求的指令可以直接发送
- 回答简洁，不要过度解释
"""


def chat_with_ai(user_id, user_name, message, history=None):
    """与 AI 对话，支持多轮工具调用。

    Returns:
        dict: { reply: str, tool_calls: list }
    """
    if not API_KEY:
        return {
            "reply": "AI 助手未配置 API Key，请在 .env 中设置 OPENAI_API_KEY。",
            "tool_calls": [],
        }

    registry = build_registry(user_id, user_name)
    client = get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name)},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    tool_calls_log = []
    tools = registry.get_schemas()

    for _ in range(5):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools if tools else None,
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                result = registry.execute(tc.function.name, tc.function.arguments)
                tool_calls_log.append({
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                    "result": result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return {"reply": msg.content or "", "tool_calls": tool_calls_log}

    return {"reply": "工具调用次数过多，已终止。", "tool_calls": tool_calls_log}
