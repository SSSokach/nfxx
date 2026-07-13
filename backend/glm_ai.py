"""GLM AI 助手：对接智谱 GLM 模型，支持 function calling 工具调用。"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app import SessionLocal
from models import User, Contact, Message, UserContact, File, ChatTodoItem, EmailTodoItem

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
MODEL = os.getenv("OPENAI_MODEL", "glm-4-flash")

_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, description, parameters, handler):
        self._tools[name] = {
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    def get_schemas(self):
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
        tool = self._tools.get(name)
        if not tool:
            return f"工具 {name} 不存在"
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            return tool["handler"](args)
        except Exception as e:
            return f"工具执行出错: {e}"


def build_registry(user_id, user_name):
    registry = ToolRegistry()

    def read_chat_history(args):
        peer_name = args.get("peer_name", "")
        limit = min(args.get("limit", 20), 50)

        db = SessionLocal()
        # Find contact by peer name
        from models import User as UserModel
        # Search users by name
        peer_user = db.query(UserModel).filter(UserModel.name.like(f"%{peer_name}%")).first()
        if not peer_user:
            db.close()
            return f"未找到用户：{peer_name}"

        # Find shared contact (1-on-1)
        user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
        contact_ids = [uc.contact_id for uc in user_contacts]
        peer_contacts = db.query(UserContact).filter(
            UserContact.user_id == peer_user.id
        ).all()
        peer_contact_ids = [uc.contact_id for uc in peer_contacts]
        shared_ids = set(contact_ids) & set(peer_contact_ids)

        if not shared_ids:
            db.close()
            return f"没有与{peer_name}的聊天记录"

        contact_id = list(shared_ids)[0]
        msgs = db.query(Message).filter(
            Message.contact_id == contact_id
        ).order_by(Message.created_at.asc()).limit(limit).all()

        db.close()
        if not msgs:
            return f"没有与{peer_name}的聊天记录"

        lines = []
        for m in msgs:
            lines.append(f"{m.sender.name}: {m.content}")
        return f"与{peer_name}的最近{len(msgs)}条消息：\n" + "\n".join(lines)

    def send_message(args):
        peer_name = args.get("peer_name", "")
        content = args.get("content", "")

        if not content:
            return "发送内容不能为空"

        db = SessionLocal()
        peer_user = db.query(User).filter(User.name.like(f"%{peer_name}%")).first()
        if not peer_user:
            db.close()
            return f"未找到用户：{peer_name}"

        # Find shared contact
        user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
        contact_ids = [uc.contact_id for uc in user_contacts]
        peer_contacts = db.query(UserContact).filter(
            UserContact.user_id == peer_user.id
        ).all()
        peer_contact_ids = [uc.contact_id for uc in peer_contacts]
        shared_ids = set(contact_ids) & set(peer_contact_ids)

        if not shared_ids:
            db.close()
            return f"没有与{peer_name}的对话窗口"

        contact_id = list(shared_ids)[0]
        from datetime import datetime
        msg = Message(
            sender_id=user_id,
            contact_id=contact_id,
            content=content,
            message_type="text",
            created_at=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.close()
        return f"已成功替你向{peer_name}发送消息：{content}"

    def get_contacts_list(args):
        db = SessionLocal()
        user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
        contact_ids = [uc.contact_id for uc in user_contacts]
        contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

        lines = []
        for c in contacts:
            display_name = c.name
            if not c.is_group:
                other_uc = db.query(UserContact).filter(
                    UserContact.contact_id == c.id,
                    UserContact.user_id != user_id
                ).first()
                if other_uc:
                    other_user = db.query(User).filter(User.id == other_uc.user_id).first()
                    if other_user:
                        display_name = other_user.name
            tag = "(群)" if c.is_group else ""
            lines.append(f"- {display_name}{tag}")
        db.close()
        return "联系人列表：\n" + "\n".join(lines) if lines else "没有联系人"

    def get_files_list(args):
        db = SessionLocal()
        files = db.query(File).filter(File.owner_id == user_id).all()
        db.close()
        if not files:
            return "没有文件"
        lines = []
        for f in files:
            size = len(f.content) if f.content else 0
            size_str = f"{size}字符" if size < 10000 else f"{size//1000}k字符"
            lines.append(f"- ID:{f.id} | {f.name} | 类型:{f.file_type} | {size_str}")
        return "文件列表：\n" + "\n".join(lines)

    def get_file_content(args):
        file_name = args.get("file_name", "")
        file_id = args.get("file_id", None)
        db = SessionLocal()
        if file_id:
            f = db.query(File).filter(File.id == file_id, File.owner_id == user_id).first()
        elif file_name:
            f = db.query(File).filter(
                File.owner_id == user_id,
                File.name.like(f"%{file_name}%")
            ).first()
        else:
            f = db.query(File).filter(File.owner_id == user_id).first()
        db.close()
        if not f:
            return "未找到匹配的文件"
        content = f.content or ""
        # Truncate very large files to avoid token overflow
        if len(content) > 8000:
            content = content[:8000] + f"\n\n[文件已截断，共{len(f.content)}字符，仅显示前8000字符]"
        return f"文件名：{f.name}\n类型：{f.file_type}\n内容：\n{content}"

    def summarize_file(args):
        """读取文件内容并调用AI生成摘要。"""
        file_name = args.get("file_name", "")
        file_id = args.get("file_id", None)
        db = SessionLocal()
        if file_id:
            f = db.query(File).filter(File.id == file_id, File.owner_id == user_id).first()
        elif file_name:
            f = db.query(File).filter(
                File.owner_id == user_id,
                File.name.like(f"%{file_name}%")
            ).first()
        else:
            f = db.query(File).filter(File.owner_id == user_id).first()
        db.close()
        if not f:
            return "未找到匹配的文件"

        content = f.content or ""
        if not content.strip() or content.startswith("[二进制文件"):
            return f"文件 {f.name} 是二进制文件，无法读取文本内容。"

        # Truncate for AI processing
        truncate_content = content[:6000] if len(content) > 6000 else content
        try:
            summary = generate_file_summary(truncate_content)
            if isinstance(summary, dict):
                parts = []
                for k, v in summary.items():
                    label_map = {
                        "title": "文档主题",
                        "topic": "文档主题",
                        "summary": "摘要",
                        "amounts": "涉及金额",
                        "rules": "关键规则",
                        "standards": "考核标准",
                        "departments": "考核部门",
                        "key_points": "关键要点",
                        "action_items": "行动项",
                        "topics": "主题标签",
                    }
                    label = label_map.get(k, k)
                    if isinstance(v, list):
                        v = "；".join(str(i) for i in v)
                    parts.append(f"**{label}**：{v}")
                return f"文件 {f.name} 的摘要：\n" + "\n".join(parts)
            return f"文件 {f.name} 的摘要：\n{summary}"
        except Exception as e:
            return f"生成摘要失败：{e}\n\n文件原文（前2000字符）：\n{content[:2000]}"

    def search_files(args):
        """搜索文件内容中包含指定关键词的文件。"""
        keyword = args.get("keyword", "")
        if not keyword:
            return "请提供搜索关键词"
        db = SessionLocal()
        files = db.query(File).filter(
            File.owner_id == user_id,
            File.content.like(f"%{keyword}%")
        ).all()
        db.close()
        if not files:
            return f"没有找到内容包含「{keyword}」的文件"
        lines = []
        for f in files:
            # Find context around keyword
            idx = f.content.find(keyword) if f.content else -1
            if idx >= 0:
                start = max(0, idx - 30)
                end = min(len(f.content), idx + len(keyword) + 50)
                context = f.content[start:end].replace("\n", " ")
                lines.append(f"- ID:{f.id} | {f.name} | ...{context}...")
            else:
                lines.append(f"- ID:{f.id} | {f.name}")
        return f"找到 {len(files)} 个包含「{keyword}」的文件：\n" + "\n".join(lines)

    def get_recent_messages(args):
        """获取当前用户最近的所有消息（跨联系人）。"""
        limit = min(args.get("limit", 20), 50)
        db = SessionLocal()
        user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
        contact_ids = [uc.contact_id for uc in user_contacts]
        msgs = db.query(Message).filter(
            Message.contact_id.in_(contact_ids)
        ).order_by(Message.created_at.desc()).limit(limit).all()
        db.close()
        if not msgs:
            return "没有最近消息"
        lines = []
        for m in reversed(msgs):
            lines.append(f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.sender.name}: {m.content[:100]}")
        return f"最近{len(msgs)}条消息：\n" + "\n".join(lines)

    registry.register(
        name="read_chat_history",
        description="读取当前用户与指定联系人的聊天记录。可用于了解沟通上下文。",
        parameters={
            "type": "object",
            "properties": {
                "peer_name": {
                    "type": "string",
                    "description": "对方用户名（支持模糊匹配）",
                },
                "limit": {
                    "type": "integer",
                    "description": "读取的最大消息条数，默认20",
                    "default": 20,
                },
            },
            "required": ["peer_name"],
        },
        handler=read_chat_history,
    )

    registry.register(
        name="send_message",
        description="替当前用户向联系人发送一条文本消息。",
        parameters={
            "type": "object",
            "properties": {
                "peer_name": {
                    "type": "string",
                    "description": "对方用户名（支持模糊匹配）",
                },
                "content": {
                    "type": "string",
                    "description": "要发送的消息内容",
                },
            },
            "required": ["peer_name", "content"],
        },
        handler=send_message,
    )

    registry.register(
        name="get_contacts_list",
        description="获取当前用户的联系人列表。",
        parameters={"type": "object", "properties": {}},
        handler=get_contacts_list,
    )

    registry.register(
        name="get_files_list",
        description="获取当前用户的文件列表，返回文件ID、名称、类型和大小。",
        parameters={"type": "object", "properties": {}},
        handler=get_files_list,
    )

    registry.register(
        name="get_file_content",
        description="读取指定文件的完整内容。支持通过文件名（模糊匹配）或文件ID查找。当用户提到某个文件或文档时，应主动调用此工具读取内容后再回答。",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "文件名（支持模糊匹配），如不填则需提供file_id",
                },
                "file_id": {
                    "type": "integer",
                    "description": "文件ID，如已知则优先使用",
                },
            },
        },
        handler=get_file_content,
    )

    registry.register(
        name="summarize_file",
        description="读取文件内容并自动生成结构化摘要（主题、金额、规则、考核标准等）。当用户要求总结、概述文档时使用。",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "文件名（支持模糊匹配）",
                },
                "file_id": {
                    "type": "integer",
                    "description": "文件ID",
                },
            },
        },
        handler=summarize_file,
    )

    registry.register(
        name="search_files",
        description="搜索文件内容中包含指定关键词的文件。当用户想查找包含某些内容的文件时使用。",
        parameters={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词",
                },
            },
            "required": ["keyword"],
        },
        handler=search_files,
    )

    registry.register(
        name="get_recent_messages",
        description="获取当前用户最近的聊天消息（跨所有联系人）。用于了解最近的沟通动态。",
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "获取的消息条数，默认20",
                    "default": 20,
                },
            },
        },
        handler=get_recent_messages,
    )

    def smart_reply(args):
        """根据对方消息和上下文，AI 生成智能回复建议。"""
        message = args.get("message", "")
        contact_id = args.get("contact_id", None)
        if not message:
            return "请提供要回复的消息内容"

        context = ""
        if contact_id:
            db = SessionLocal()
            msgs = db.query(Message).filter(
                Message.contact_id == contact_id
            ).order_by(Message.created_at.desc()).limit(6).all()
            db.close()
            if len(msgs) > 1:
                lines = []
                for m in reversed(msgs[:-1]):
                    lines.append(f"{m.sender.name}: {m.content[:100]}")
                context = "\n".join(lines)

        result = generate_smart_reply(message, context)
        if not result.get("replies"):
            return "无法生成回复建议"
        reply_lines = [f"{i+1}. {r}" for i, r in enumerate(result["replies"])]
        tone_info = f"\n建议语气：{result.get('tone', '')}" if result.get("tone") else ""
        return f"智能回复建议：\n" + "\n".join(reply_lines) + tone_info

    def classify_msg(args):
        """使用 AI 分析消息的意图类别。"""
        message = args.get("message", "")
        if not message:
            return "请提供要分类的消息"
        result = classify_message(message)
        return f"分类结果：{result.get('category', '其他')}（置信度：{result.get('confidence', '中')}）\n意图概括：{result.get('summary', '')}"

    def prioritize_my_todos(args):
        """对用户当前的待办事项按优先级排序。"""
        db = SessionLocal()
        chat_todos = db.query(ChatTodoItem).filter(
            ChatTodoItem.user_id == user_id,
            ChatTodoItem.status == "pending",
        ).all()
        email_todos = db.query(EmailTodoItem).filter(
            EmailTodoItem.user_id == user_id,
            EmailTodoItem.status == "pending",
        ).all()
        db.close()

        all_todos = []
        for t in chat_todos:
            dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
            src = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
            all_todos.append(f"{src} {t.content}{dl}")
        for t in email_todos:
            dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
            all_todos.append(f"[邮件:{t.subject}] {t.content}{dl}")

        if not all_todos:
            return "当前没有待办事项"

        result = prioritize_todos(all_todos)
        if not result:
            return "排序失败"
        lines = []
        for item in result:
            lines.append(f"[{item.get('priority', '中')}] {item.get('original', '')} — {item.get('reason', '')}")
        return f"待办优先级排序（共{len(result)}项）：\n" + "\n".join(lines)

    def meeting_minutes(args):
        """从群聊消息中提取会议纪要。"""
        contact_name = args.get("contact_name", "")
        limit = min(args.get("limit", 50), 100)
        if not contact_name:
            return "请提供群聊名称"

        db = SessionLocal()
        contact = db.query(Contact).filter(
            Contact.name.like(f"%{contact_name}%"),
            Contact.is_group == True,
        ).first()
        if not contact:
            db.close()
            return f"未找到群聊：{contact_name}"

        msgs = db.query(Message).filter(
            Message.contact_id == contact.id
        ).order_by(Message.created_at.asc()).limit(limit).all()
        db.close()

        if not msgs:
            return f"该群聊没有消息记录"

        lines = []
        for m in msgs:
            lines.append(f"[{m.created_at.strftime('%H:%M')}] {m.sender.name}: {m.content}")
        messages_text = "\n".join(lines)

        result = extract_meeting_minutes(messages_text)
        parts = []
        parts.append(f"**会议主题**：{result.get('topic', '未知')}")
        if result.get('attendees'):
            parts.append(f"**参会人员**：{'、'.join(result['attendees'])}")
        parts.append(f"**会议摘要**：{result.get('summary', '')}")
        if result.get('key_decisions'):
            parts.append(f"**关键决议**：\n" + "\n".join(f"- {d}" for d in result['key_decisions']))
        if result.get('action_items'):
            parts.append(f"**行动项**：\n" + "\n".join(f"- {a}" for a in result['action_items']))
        return f"群「{contact_name}」的会议纪要：\n" + "\n\n".join(parts)

    registry.register(
        name="smart_reply",
        description="根据对方消息和聊天上下文，AI 生成多个不同风格的回复建议。当用户需要回复消息但不知道怎么回时使用。",
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "对方发来的消息内容",
                },
                "contact_id": {
                    "type": "integer",
                    "description": "联系人/对话ID，用于获取上下文",
                },
            },
            "required": ["message"],
        },
        handler=smart_reply,
    )

    registry.register(
        name="classify_message",
        description="使用 AI 分析消息的意图类别（任务分配、信息通知、会议邀请等），帮助用户快速理解消息性质。",
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "要分类的消息内容",
                },
            },
            "required": ["message"],
        },
        handler=classify_msg,
    )

    registry.register(
        name="prioritize_todos",
        description="对当前用户的所有待办事项按紧急程度和重要性进行 AI 智能排序，帮助用户确定工作优先级。",
        parameters={"type": "object", "properties": {}},
        handler=prioritize_my_todos,
    )

    registry.register(
        name="meeting_minutes",
        description="从群聊消息记录中提取会议纪要，包括会议主题、参会人员、关键决议和行动项。",
        parameters={
            "type": "object",
            "properties": {
                "contact_name": {
                    "type": "string",
                    "description": "群聊名称（支持模糊匹配）",
                },
                "limit": {
                    "type": "integer",
                    "description": "读取的最大消息条数，默认50",
                    "default": 50,
                },
            },
            "required": ["contact_name"],
        },
        handler=meeting_minutes,
    )

    return registry


SYSTEM_PROMPT_TEMPLATE = """你是一个智能办公助手，当前正在为用户「{user_name}」服务。

你可以通过调用工具来帮助用户：
1. 读取聊天记录：了解用户与同事的沟通上下文
2. 发送消息：替用户向联系人发送消息
3. 查看联系人列表：列出用户的联系人
4. 查看文件列表：列出用户的所有文件（返回文件ID、名称、类型、大小）
5. 获取文件内容：读取文件完整内容
6. 生成文件摘要：自动读取文件并生成结构化摘要
7. 搜索文件：按关键词搜索文件内容
8. 获取最近消息：查看最近的聊天动态

工作原则：
- **主动读取文件**：当用户提到某个文件、文档或询问文件内容时，必须先调用 get_file_content 或 summarize_file 读取文件内容，然后再基于实际内容回答。绝不要在没有读取文件的情况下凭空回答。
- **先查再答**：当用户询问联系人、消息等内容时，先调用对应工具获取数据再回答
- 用户提到的联系人姓名可能是简称，调用工具时用 peer_name 模糊匹配即可
- 发送消息前确认内容，如果是用户明确要求的指令可以直接发送
- 回答简洁，不要过度解释
- 处理文件时，如果文件较大，优先使用 summarize_file 生成摘要
"""


def chat_with_ai(user_id, user_name, message, history=None):
    """与 AI 对话，支持 function calling 工具调用。

    Returns:
        dict: { response: str, result: list }
    """
    if not API_KEY:
        return {
            "response": "AI 助手未配置 API Key，请在 backend/.env 中设置 OPENAI_API_KEY。",
            "result": None
        }

    registry = build_registry(user_id, user_name)
    client = get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name)},
    ]
    if history:
        for h in history:
            messages.append(h)
    messages.append({"role": "user", "content": message})

    tool_calls_log = []
    tools = registry.get_schemas()

    for _ in range(5):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools if tools else None,
            extra_body={"enable_thinking": False},
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
            # Handle both content and reasoning_content
            content = msg.content or ""
            if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
                content = msg.reasoning_content
            return {"response": content, "result": tool_calls_log if tool_calls_log else None}

    return {"response": "工具调用次数过多，已终止。", "result": tool_calls_log}


# ===== 场景化 AI 调用函数 =====


def _parse_json_response(content):
    """从模型返回中解析 JSON，兼容代码块包裹的情况。"""
    if not content:
        return {}
    text = content.strip()
    # 去除 ```json ... ``` 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # 去掉首行 ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # 去掉末尾 ```
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception:
        return {}


def _ai_call(prompt, expect_json=True):
    """统一的 AI 调用封装，返回文本或解析后的 JSON。"""
    if not API_KEY:
        if expect_json:
            return {}
        return ""
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"enable_thinking": False},
    )
    msg = resp.choices[0].message
    content = msg.content or ""
    if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
        content = msg.reasoning_content
    if expect_json:
        return _parse_json_response(content)
    return content


def summarize_message(message_content):
    """@所有人 消息摘要。

    Args:
        message_content: 包含 "@所有人" 的群聊消息文本。

    Returns:
        dict: { summary: str, deadline: str|null }
    """
    prompt = f"""请分析以下包含"@所有人"的群聊消息，提取关键信息并生成简洁摘要。

消息内容：
{message_content}

请以 JSON 格式返回，严格包含以下字段：
- summary: 消息摘要（一句话概括核心内容和要求）
- deadline: 截止日期，格式 YYYY-MM-DD（如果消息中提到了明确截止时间则提取，否则返回 null）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "summary": result.get("summary", message_content[:100]),
        "deadline": result.get("deadline"),
    }


def extract_todo(message_content):
    """@自己 消息待办提取。

    Args:
        message_content: 包含 "@用户名" 的群聊消息文本。

    Returns:
        dict: { content: str, deadline: str|null }
    """
    prompt = f"""请分析以下群聊消息（其中 @某人 表示对方在@你），提取需要你执行的待办事项。

消息内容：
{message_content}

请以 JSON 格式返回，严格包含以下字段：
- content: 待办事项内容（清晰描述你需要做什么）
- deadline: 截止日期，格式 YYYY-MM-DD（如果有明确截止时间则提取，否则返回 null）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "content": result.get("content", message_content[:100]),
        "deadline": result.get("deadline"),
    }


def extract_private_todo(peer_message, user_reply):
    """私聊待办提取。

    分析对方发给你的消息以及你的回复，判断是否产生了需要跟进的待办。

    Args:
        peer_message: 对方发送的消息文本。
        user_reply: 你的回复消息文本。

    Returns:
        dict: { should_create_todo: bool, content: str, deadline: str|null, peer_name: str }
    """
    prompt = f"""请分析以下私聊对话，判断是否产生了需要当前用户跟进的待办事项。

对方消息：
{peer_message}

用户回复：
{user_reply}

请以 JSON 格式返回，严格包含以下字段：
- should_create_todo: 布尔值，true 表示需要创建待办，false 表示不需要
- content: 待办事项内容（如果需要创建则描述具体待办，否则返回空字符串）
- deadline: 截止日期，格式 YYYY-MM-DD（如果有明确截止时间则提取，否则返回 null）
- peer_name: 对方称呼或部门名称（如果能从消息中识别）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "should_create_todo": bool(result.get("should_create_todo", False)),
        "content": result.get("content", ""),
        "deadline": result.get("deadline"),
        "peer_name": result.get("peer_name", ""),
    }


def extract_email_todo(email_content):
    """邮件待办提取。

    分析邮件内容，判断是否需要当前用户采取行动。

    Args:
        email_content: 邮件正文文本。

    Returns:
        dict: { action_required: bool, content: str, deadline: str|null }
    """
    prompt = f"""请分析以下邮件内容，判断是否需要收件人采取行动或处理。

邮件内容：
{email_content}

请以 JSON 格式返回，严格包含以下字段：
- action_required: 布尔值，true 表示需要处理，false 表示仅通知无需处理
- content: 待办事项内容（如果需要处理则描述具体待办，否则返回空字符串）
- deadline: 截止日期，格式 YYYY-MM-DD（如果有明确截止时间则提取，否则返回 null）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "action_required": bool(result.get("action_required", False)),
        "content": result.get("content", ""),
        "deadline": result.get("deadline"),
    }


def generate_file_summary(file_content):
    """文件摘要生成。

    读取文件内容，生成结构化摘要。

    Args:
        file_content: 文件文本内容。

    Returns:
        dict: 结构化摘要 JSON
    """
    prompt = f"""请阅读以下文件内容，生成结构化摘要。

文件内容：
{file_content}

请以 JSON 格式返回，严格包含以下字段：
- title: 文件标题或主题
- summary: 整体摘要（2-3句话概括文件核心内容）
- key_points: 关键要点列表（字符串数组，每项一个要点）
- action_items: 待办行动项列表（字符串数组，如果文件中提到需要做的事情）
- topics: 涉及主题列表（字符串数组，如"项目管理"、"技术方案"等）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "title": result.get("title", ""),
        "summary": result.get("summary", ""),
        "key_points": result.get("key_points", []),
        "action_items": result.get("action_items", []),
        "topics": result.get("topics", []),
    }


def generate_work_report(completed_tasks, pending_tasks):
    """工作报告生成。

    根据已完成和未完成的待办事项，生成 Markdown 格式的工作报告。

    Args:
        completed_tasks: 已完成任务列表（字符串列表）。
        pending_tasks: 未完成任务列表（字符串列表）。

    Returns:
        str: Markdown 格式的工作报告文本。
    """
    completed_text = "\n".join(f"- {t}" for t in completed_tasks) if completed_tasks else "- 暂无"
    pending_text = "\n".join(f"- {t}" for t in pending_tasks) if pending_tasks else "- 暂无"

    prompt = f"""请根据以下待办事项数据，生成一份结构清晰的 Markdown 格式工作报告。

已完成任务：
{completed_text}

未完成任务：
{pending_text}

要求：
1. 报告以 "# 工作报告" 为标题
2. 包含"本期工作总结"部分，概述已完成的工作
3. 包含"待办事项"部分，列出未完成的任务并标注优先级
4. 包含"下周计划"部分，基于待办事项给出建议
5. 语言简洁专业，直接输出 Markdown 内容，不要加代码块标记"""

    return _ai_call(prompt, expect_json=False)


def generate_smart_reply(peer_message, context_messages=""):
    """智能回复生成。

    根据对方发来的消息和上下文，生成合适的回复建议。

    Args:
        peer_message: 对方发送的最新消息文本。
        context_messages: 之前的上下文消息（可选）。

    Returns:
        dict: { replies: list[str], tone: str }
    """
    context_text = ""
    if context_messages:
        context_text = f"\n\n之前的对话上下文：\n{context_messages}\n"

    prompt = f"""请根据以下对话，生成3个不同风格的回复建议。

对方最新消息：
{peer_message}
{context_text}
请以 JSON 格式返回，严格包含以下字段：
- replies: 回复建议列表（字符串数组，3个不同风格的回复，每个20-80字）
- tone: 建议的回复语气（如"正式"、"友好"、"简洁"等）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "replies": result.get("replies", []),
        "tone": result.get("tone", ""),
    }


def generate_daily_digest(user_id):
    """AI 日报生成。

    汇总用户当天的消息、待办、邮件动态，生成工作日报。
    """
    db = SessionLocal()
    from models import User, Contact, UserContact, Message, ChatTodoItem, EmailTodoItem
    from datetime import date, datetime

    user = db.query(User).filter(User.id == user_id).first()
    user_name = user.name if user else "用户"

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
    contact_ids = [uc.contact_id for uc in user_contacts]

    today_msgs = db.query(Message).filter(
        Message.contact_id.in_(contact_ids),
        Message.created_at >= today_start,
        Message.created_at <= today_end,
    ).order_by(Message.created_at.asc()).all()

    pending_todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.status == "pending",
    ).all()

    pending_email_todos = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.status == "pending",
    ).all()

    completed_chat = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.status == "completed",
        ChatTodoItem.completed_at >= today_start,
        ChatTodoItem.completed_at <= today_end,
    ).all()

    completed_email = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.status == "completed",
        EmailTodoItem.completed_at >= today_start,
        EmailTodoItem.completed_at <= today_end,
    ).all()

    db.close()

    msg_lines = []
    for m in today_msgs[:30]:
        contact = db.query(Contact).filter(Contact.id == m.contact_id).first()
        contact_name = contact.name if contact else ""
        msg_lines.append(f"[{m.created_at.strftime('%H:%M')}] {contact_name} - {m.sender.name}: {m.content[:80]}")
    messages_text = "\n".join(msg_lines) if msg_lines else "今日无消息"

    todo_lines = []
    for t in pending_todos + pending_email_todos:
        dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
        todo_lines.append(f"- {t.content}{dl}")
    todos_text = "\n".join(todo_lines) if todo_lines else "无待办"

    completed_lines = []
    for t in completed_chat + completed_email:
        completed_lines.append(f"- {t.content}")
    completed_text = "\n".join(completed_lines) if completed_lines else "今日无已完成项"

    prompt = f"""请根据以下数据，为用户「{user_name}」生成今日工作日报（Markdown格式）。

## 今日消息动态（共{len(today_msgs)}条）
{messages_text}

## 今日已完成（共{len(completed_chat) + len(completed_email)}项）
{completed_text}

## 待办事项（共{len(pending_todos) + len(pending_email_todos)}项）
{todos_text}

要求：
1. 报告以 "# 工作日报 - {today.isoformat()}" 为标题
2. 包含"今日沟通动态"部分，概括重要的聊天和邮件
3. 包含"今日完成"部分，列出已完成的工作
4. 包含"待办提醒"部分，标注紧急程度
5. 语言简洁专业，直接输出 Markdown 内容，不要加代码块标记"""

    return _ai_call(prompt, expect_json=False)


def prioritize_todos(todo_items):
    """待办优先级排序。

    使用 AI 对待办事项按紧急程度和重要性进行排序。
    """
    todos_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(todo_items))

    prompt = f"""请根据紧急程度和重要性，对以下待办事项进行优先级排序。

待办事项：
{todos_text}

请以 JSON 格式返回，严格包含以下字段：
- sorted_items: 排序后的待办列表（对象数组，每项包含：
  - original: 原始待办文本
  - priority: 优先级（"紧急"/"高"/"中"/"低"）
  - reason: 排序理由（一句话））

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return result.get("sorted_items", [])


def classify_message(message_content):
    """消息分类。

    分析消息内容，判断其意图类别。
    """
    prompt = f"""请分析以下消息的意图类别。

消息内容：
{message_content}

请以 JSON 格式返回，严格包含以下字段：
- category: 消息类别，从以下选择：任务分配、信息通知、会议邀请、文件分享、问题咨询、日常闲聊、审批流程、其他
- confidence: 置信度（"高"/"中"/"低"）
- summary: 一句话概括消息核心意图

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "category": result.get("category", "其他"),
        "confidence": result.get("confidence", "中"),
        "summary": result.get("summary", ""),
    }


def extract_meeting_minutes(messages_text):
    """会议纪要提取。

    从群聊消息中提取会议纪要。
    """
    prompt = f"""请从以下群聊记录中提取会议纪要。

群聊记录：
{messages_text}

请以 JSON 格式返回，严格包含以下字段：
- topic: 会议主题
- attendees: 参会人员列表（字符串数组）
- key_decisions: 关键决议列表（字符串数组）
- action_items: 行动项列表（字符串数组，每项包含负责人和任务）
- summary: 会议摘要（2-3句话）

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "topic": result.get("topic", ""),
        "attendees": result.get("attendees", []),
        "key_decisions": result.get("key_decisions", []),
        "action_items": result.get("action_items", []),
        "summary": result.get("summary", ""),
    }
