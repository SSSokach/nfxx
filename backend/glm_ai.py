"""GLM AI 助手：对接智谱 GLM 模型，支持 function calling 工具调用。"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app import SessionLocal
from models import User, Contact, Message, UserContact, File, ChatTodoItem, EmailTodoItem, CandidateTodo
import skills as skill_registry

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

    # ===== 文本润色 / 邮件起草 / 信息抽取 工具 =====
    def polish_text_tool(args):
        """文本润色工具（封装 polish_text 函数）。"""
        text = args.get("text", "")
        style = args.get("style", None)
        if not text:
            return "请提供要润色的文本"
        result = polish_text(text, style)
        parts = [f"**默认推荐版本**：{result.get('default_version', '')}"]
        if result.get("variants"):
            for v in result["variants"]:
                parts.append(f"**{v.get('style', '')}版**：{v.get('content', '')}")
        if result.get("changes"):
            parts.append(f"修改要点：{result['changes']}")
        return "润色结果：\n" + "\n".join(parts)

    def draft_email_tool(args):
        """邮件起草工具（封装 draft_email 函数）。"""
        scene = args.get("scene", "new")
        recipient = args.get("recipient", "")
        topic = args.get("topic", "")
        points = args.get("points", [])
        original = args.get("original", None)
        language = args.get("language", "zh")
        result = draft_email(
            scene=scene, recipient=recipient, topic=topic,
            points=points, original=original, language=language,
        )
        parts = [f"**主题**：{result.get('subject', '')}", f"**正文**：\n{result.get('body', '')}"]
        if result.get("placeholders"):
            parts.append("**需补充信息**：" + "；".join(result["placeholders"]))
        return "邮件草稿：\n" + "\n".join(parts)

    def extract_information_tool(args):
        """信息抽取工具（封装 extract_information 函数）。"""
        text = args.get("text", "")
        types = args.get("types", None)
        if not text:
            return "请提供要抽取信息的文本"
        result = extract_information(text, types)
        if not result:
            return "未识别到可抽取的信息"
        parts = []
        for t, items in result.items():
            if items:
                parts.append(f"**{t}**：" + "；".join(str(i) for i in items))
        return "抽取结果：\n" + "\n".join(parts) if parts else "未识别到可抽取的信息"

    registry.register(
        name="polish_text",
        description="对文本进行润色改写，支持专业/简洁/礼貌/正式等多种风格。当用户要求润色、改写、优化措辞、调整语气时使用。",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要润色的原文",
                },
                "style": {
                    "type": "string",
                    "description": "期望风格，可选值：专业、简洁、礼貌、正式。不填则由AI自行推荐。",
                },
            },
            "required": ["text"],
        },
        handler=polish_text_tool,
    )

    registry.register(
        name="draft_email",
        description="起草邮件正文，支持新邮件/回复/转发场景。当用户要求写邮件、回复邮件、起草邮件时使用。",
        parameters={
            "type": "object",
            "properties": {
                "scene": {
                    "type": "string",
                    "description": "场景，可选值：new(新邮件)、reply(回复)、forward(转发)",
                    "default": "new",
                },
                "recipient": {
                    "type": "string",
                    "description": "收件人名称或称呼",
                },
                "topic": {
                    "type": "string",
                    "description": "邮件主题或核心要点",
                },
                "points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要表达的要点列表",
                },
                "original": {
                    "type": "string",
                    "description": "原邮件内容（回复/转发场景使用）",
                },
                "language": {
                    "type": "string",
                    "description": "语言，zh 或 en",
                    "default": "zh",
                },
            },
        },
        handler=draft_email_tool,
    )

    registry.register(
        name="extract_information",
        description="从文本中提取结构化信息（人名、时间、金额、地点、动作、组织）。当用户要求提取信息、找出关键信息、提炼要点时使用。",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "要抽取信息的文本",
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要抽取的信息类型，可选值：人名、时间、金额、地点、动作、组织。不填则抽取所有类型。",
                },
            },
            "required": ["text"],
        },
        handler=extract_information_tool,
    )

    # ===== 工作报告生成工具（获取所有时间段已完成+未完成待办） =====
    def generate_work_report_tool(args):
        """工作报告工具：查询所有已完成和未完成待办，生成 Markdown 报告。"""
        db = SessionLocal()
        try:
            # 所有未完成待办
            pending_chat = db.query(ChatTodoItem).filter(
                ChatTodoItem.user_id == user_id,
                ChatTodoItem.status == "pending",
            ).order_by(ChatTodoItem.created_at.desc()).all()
            pending_email = db.query(EmailTodoItem).filter(
                EmailTodoItem.user_id == user_id,
                EmailTodoItem.status == "pending",
            ).order_by(EmailTodoItem.created_at.desc()).all()

            # 所有已完成待办（不限时间）
            completed_chat = db.query(ChatTodoItem).filter(
                ChatTodoItem.user_id == user_id,
                ChatTodoItem.status == "completed",
            ).order_by(ChatTodoItem.completed_at.desc().nullslast()).all()
            completed_email = db.query(EmailTodoItem).filter(
                EmailTodoItem.user_id == user_id,
                EmailTodoItem.status == "completed",
            ).order_by(EmailTodoItem.completed_at.desc().nullslast()).all()
        finally:
            db.close()

        # 格式化未完成
        pending_tasks = []
        for t in pending_chat:
            dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
            src = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
            pending_tasks.append(f"{src} {t.content}{dl}")
        for t in pending_email:
            dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
            pending_tasks.append(f"[邮件:{t.subject}] {t.content}{dl}")

        # 格式化已完成
        completed_tasks = []
        for t in completed_chat:
            ts = t.completed_at.strftime("%Y-%m-%d %H:%M") if t.completed_at else "未知时间"
            src = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
            completed_tasks.append(f"{src} {t.content} (完成于:{ts})")
        for t in completed_email:
            ts = t.completed_at.strftime("%Y-%m-%d %H:%M") if t.completed_at else "未知时间"
            completed_tasks.append(f"[邮件:{t.subject}] {t.content} (完成于:{ts})")

        report = generate_work_report(completed_tasks, pending_tasks)
        return report

    registry.register(
        name="generate_work_report",
        description="生成工作报告（周报/月报/工作总结）。查询所有时间段内已完成和未完成的待办事项，生成 Markdown 格式的工作报告。当用户要求生成周报、月报、工作报告、工作总结时使用。",
        parameters={"type": "object", "properties": {}},
        handler=generate_work_report_tool,
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

    会先通过 skills 模块匹配用户意图，将专属 skill prompt 拼接到通用 system prompt 后。

    Returns:
        dict: { response: str, skill: str|None }
    """
    if not API_KEY:
        return {
            "response": "AI 助手未配置 API Key，请在 backend/.env 中设置 OPENAI_API_KEY。",
        }

    # 通过 skills 匹配用户意图，获取专属 prompt
    matched_skill = skill_registry.get_matched_skill(message)
    skill_prompt = matched_skill.get("system_prompt", "") if matched_skill else ""

    registry = build_registry(user_id, user_name)
    client = get_client()

    system_content = SYSTEM_PROMPT_TEMPLATE.format(user_name=user_name)
    if skill_prompt:
        system_content += "\n\n" + skill_prompt

    messages = [
        {"role": "system", "content": system_content},
    ]
    if history:
        for h in history:
            messages.append(h)
    messages.append({"role": "user", "content": message})

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
            return {
                "response": content,
                "skill": matched_skill["name"] if matched_skill else None,
            }

    return {
        "response": "工具调用次数过多，已终止。",
        "skill": matched_skill["name"] if matched_skill else None,
    }


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


def detect_email_candidate_todos(emails_batch, user_name):
    """邮件候选待办检测（批量）。

    批量分析邮件，找出需要用户处理的事项（候选待办）。
    需用户确认后才会转为正式邮件待办。

    优先使用 AI 检测；若 AI 未配置或调用失败，则使用规则匹配作为 fallback。

    Args:
        emails_batch: 邮件列表，每项为 dict { id, subject, sender, content }
        user_name: 当前用户名

    Returns:
        list[dict]: 候选待办列表，每项 { id, content, deadline }
    """
    if not emails_batch:
        return []

    # ---- 优先尝试 AI 检测 ----
    if API_KEY:
        lines = []
        for i, e in enumerate(emails_batch):
            content_snippet = (e["content"] or "")[:300]
            lines.append(f"{i+1}. [主题:{e['subject']}] [发件人:{e['sender']}]: {content_snippet}")
        emails_text = "\n".join(lines)

        prompt = f"""请分析以下邮件，找出所有需要用户「{user_name}」处理或跟进的事项。

邮件列表：
{emails_text}

判断标准：
- 邮件要求收件人执行的动作（如提交材料、参加会议、回复确认、填写表单等）
- 有明确截止时间的事项
- 需要用户回复或确认的事项
- 不包括：纯通知型邮件、闲聊、已回复的邮件

请以 JSON 格式返回，严格包含以下字段：
- candidates: 候选待办列表（对象数组，每项包含：
  - email_index: 对应邮件的序号（从1开始）
  - content: 待办事项描述（简洁明确，包含关键动作和时间节点）
  - deadline: 截止日期 YYYY-MM-DD 格式（如果有提到则提取，否则返回 null））

如果没有需要处理的事项，返回空数组。

只返回 JSON，不要任何额外文字。"""
        try:
            result = _ai_call(prompt, expect_json=True)
            candidates_raw = result.get("candidates", [])
            candidates = []
            for c in candidates_raw:
                idx = c.get("email_index", 0) - 1
                if 0 <= idx < len(emails_batch):
                    candidates.append({
                        "id": emails_batch[idx]["id"],
                        "content": c.get("content", ""),
                        "deadline": c.get("deadline"),
                    })
            if candidates:
                return candidates
        except Exception:
            pass  # AI 失败，降级到规则匹配

    # ---- 规则匹配 fallback ----
    candidates = []
    todo_keywords = ["请", "需要", "要求", "提交", "回复", "确认", "参加", "填写", "完成", "截止", "之前", "之前提交"]
    for e in emails_batch:
        content = (e.get("content") or "")
        if any(kw in content for kw in todo_keywords):
            snippet = content[:80] + ("..." if len(content) > 80 else "")
            candidates.append({
                "id": e["id"],
                "content": f"[{e.get('subject', '')}] {snippet}",
                "deadline": None,
            })
    return candidates


def generate_email_summary(email_content, attachments_text=""):
    """生成邮件摘要。

    对邮件正文（可带附件）生成结构化摘要，返回 Markdown 文本。

    Args:
        email_content: 邮件正文文本。
        attachments_text: 附件内容的拼接文本（可选），格式如 "[附件1: xxx.md]\n内容..."

    Returns:
        str: Markdown 格式的邮件摘要
    """
    attachment_section = ""
    if attachments_text and attachments_text.strip():
        attachment_section = f"""

【附件内容】
{attachments_text[:6000]}
"""

    prompt = f"""请阅读以下邮件（含附件内容，如有），生成结构化摘要。

【邮件正文】
{email_content}{attachment_section}

请以 Markdown 格式输出，严格包含以下小节（没有的内容写"无"，不要编造）：

## 邮件主题
（一句话概括邮件主旨）

## 发件人 / 部门
（若原文给出则提取，否则写"无"）

## 核心内容
（2-3 句话概括邮件正文要点）

## 关键时间节点
（用列表形式列出截止日期、会议时间等，格式 YYYY-MM-DD；无则写"无"）

## 涉及人员 / 部门
（列出邮件中提到的相关人或部门；无则写"无"）

## 需要执行的事项
（用列表形式列出需要收件人采取的行动项，按优先级排序；无则写"无"）

## 附件要点
（如有附件，简要概括附件核心内容；无附件则写"无"）

只输出 Markdown 摘要，不要附加任何解释性文字。"""
    return _ai_call(prompt, expect_json=False)


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

    # 在 db.close() 之前，预查询联系人信息
    contact_map = {}
    contact_ids_in_msgs = {m.contact_id for m in today_msgs[:30]}
    if contact_ids_in_msgs:
        contacts = db.query(Contact).filter(Contact.id.in_(contact_ids_in_msgs)).all()
        contact_map = {c.id: c for c in contacts}

    db.close()

    msg_lines = []
    for m in today_msgs[:30]:
        contact = contact_map.get(m.contact_id)
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


def detect_candidate_todos(messages_batch, user_name):
    """候选待办检测。

    批量分析消息，找出需要用户处理的事项（候选待办）。
    这些事项需要用户确认后才会转为正式待办。

    优先使用 AI 检测；若 AI 未配置或调用失败，则使用规则匹配作为 fallback。

    Args:
        messages_batch: 消息列表，每项为 dict { id, sender, source, content }
        user_name: 当前用户名

    Returns:
        list[dict]: 候选待办列表，每项 { message_id, content, deadline }
    """
    if not messages_batch:
        return []

    # ---- 优先尝试 AI 检测 ----
    if API_KEY:
        lines = []
        for i, m in enumerate(messages_batch):
            lines.append(f"{i+1}. [来源:{m['source']}] {m['sender']}: {m['content'][:200]}")
        messages_text = "\n".join(lines)

        prompt = f"""请分析以下聊天消息，找出所有需要用户「{user_name}」处理或跟进的事项。

消息列表：
{messages_text}

判断标准：
- 对方要求用户做的事（如提交文档、review代码、参加会议等）
- 有明确截止时间的任务
- 需要用户回复或确认的事项
- 不包括：纯通知、闲聊、用户自己发的消息中已回复的

请以 JSON 格式返回，严格包含以下字段：
- candidates: 候选待办列表（对象数组，每项包含：
  - message_index: 对应消息的序号（从1开始）
  - content: 待办事项描述（简洁明确）
  - deadline: 截止日期 YYYY-MM-DD 格式（如果有提到则提取，否则返回 null））

如果没有需要处理的事项，返回空数组。

只返回 JSON，不要任何额外文字。"""
        try:
            result = _ai_call(prompt, expect_json=True)
            candidates_raw = result.get("candidates", [])
            candidates = []
            for c in candidates_raw:
                idx = c.get("message_index", 0) - 1
                if 0 <= idx < len(messages_batch):
                    candidates.append({
                        "message_id": messages_batch[idx]["id"],
                        "content": c.get("content", ""),
                        "deadline": c.get("deadline"),
                    })
            if candidates:
                return candidates
        except Exception:
            pass  # AI 失败，降级到规则匹配

    # ---- 规则匹配 fallback ----
    import re
    from datetime import date, timedelta

    # 关键词模式：任务型
    task_patterns = [
        r'(?i)(?:帮忙|请|麻烦|需要你|你(?:来|去|帮忙)|@?张三)\s*(.{2,})',
        r'(?i)(review|审核|检查|提交|发送|准备|整理|更新|修改|完成|写|做|给)\s*(.{2,})',
        r'(?i)(?:什么时候|多久|能否|可以)\s*(.{2,})',
    ]

    # 截止时间模式
    deadline_patterns = [
        # 下周X / 本周X / 周X
        (r'(?:下|本)周[一二三四五六天日]\s*(?:前|之前)?', 7),
        # 明天/后天/今天
        (r'今天(?:之?前)?', 0),
        (r'明天(?:之?前)?', 1),
        (r'后天(?:之?前)?', 2),
        # X月X号前 / X月X日前
        (r'(\d{1,2})月(\d{1,2})号?(?:之?前)?', None),
        # X号前
        (r'(\d{1,2})号(?:之?前)?', None),
        # N天内
        (r'(\d+)\s*天[内以]', None),
    ]

    weekdays = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}

    def extract_deadline(text):
        today = date.today()
        # X月X号
        m = re.search(r'(\d{1,2})月(\d{1,2})号?(?:之?前)?', text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            try:
                return date(today.year, month, day).isoformat()
            except ValueError:
                pass
        # 今天/明天/后天
        if re.search(r'今天', text):
            return today.isoformat()
        if re.search(r'明天', text):
            return (today + timedelta(days=1)).isoformat()
        if re.search(r'后天', text):
            return (today + timedelta(days=2)).isoformat()
        # 下周X
        m = re.search(r'下周([一二三四五六天日])', text)
        if m:
            target_wd = weekdays[m.group(1)]
            delta = (target_wd - today.weekday() + 7) % 7
            if delta == 0:
                delta = 7
            return (today + timedelta(days=delta)).isoformat()
        # 本周X
        m = re.search(r'本周([一二三四五六天日])', text)
        if m:
            target_wd = weekdays[m.group(1)]
            delta = (target_wd - today.weekday() + 7) % 7
            return (today + timedelta(days=delta)).isoformat()
        # N天内
        m = re.search(r'(\d+)\s*天[内以]', text)
        if m:
            return (today + timedelta(days=int(m.group(1)))).isoformat()
        # X号前
        m = re.search(r'(\d{1,2})号(?:之?前)?', text)
        if m and not re.search(r'\d{1,2}月', text):
            day = int(m.group(1))
            if today.day <= day:
                return date(today.year, today.month, day).isoformat()
            else:
                nm = today.month + 1 if today.month < 12 else 1
                ny = today.year if today.month < 12 else today.year + 1
                try:
                    return date(ny, nm, day).isoformat()
                except ValueError:
                    pass
        return None

    # 排除模式：纯闲聊
    chat_keywords = ['天气', '吃饭', '下班', '周末', '休息', '早安', '晚安',
                     '谢谢', '不客气', '好的', '收到', '哈哈', '呵呵']

    # 任务关键词
    task_keywords = ['帮忙', '麻烦', '需要', '请', 'review', '审核', '提交',
                     '发送', '准备', '整理', '更新', '修改', '完成', '写',
                     '做', '给', '开个会', '什么时候', '能否', '讨论',
                     '带一下', '整理', '部署', '配置', '修复']

    candidates = []
    for msg in messages_batch:
        content = msg.get('content', '')
        if not content or len(content) < 5:
            continue

        # 排除纯闲聊
        if any(kw in content for kw in chat_keywords) and not any(kw in content for kw in task_keywords):
            continue

        # 检查是否包含任务关键词
        has_task = any(kw in content.lower() for kw in task_keywords)
        # 检查是否 @ 了用户
        mentions_user = f'@{user_name}' in content or '@张三' in content
        # 检查是否有截止时间
        has_deadline = bool(extract_deadline(content))

        if has_task or (mentions_user and has_deadline):
            # 清理内容，提取核心任务描述
            clean_content = content
            # 去掉 @张三/@所有人 等前缀
            clean_content = re.sub(r'@\S+\s*', '', clean_content).strip()
            # 如果太长，截取
            if len(clean_content) > 100:
                clean_content = clean_content[:100] + '...'

            deadline = extract_deadline(content)
            candidates.append({
                "message_id": msg['id'],
                "content": clean_content,
                "deadline": deadline,
            })

    return candidates


# ===== 文本润色 / 邮件起草 / 信息抽取（配合 skills.py 使用）=====


def polish_text(text, style=None):
    """文本润色与改写。

    Args:
        text: 待润色的原文。
        style: 期望风格，可选值：专业 / 简洁 / 礼貌 / 正式。为空时由 AI 自行推荐。

    Returns:
        dict: {
            default_version: 默认推荐版本,
            variants: [{style, content}, ...] 其他风格版本,
            changes: 修改要点说明
        }
    """
    style_hint = f"用户期望风格：{style}。" if style else "用户未指定风格，请自行选择最合适的风格作为默认版本。"

    prompt = f"""请对以下文本进行润色改写。

原文：
{text}

{style_hint}

请以 JSON 格式返回，严格包含以下字段：
- default_version: 默认推荐版本（根据原文语境选择最合适的风格）
- variants: 其他风格版本列表（对象数组，每项包含 style: 风格名（专业/简洁/礼貌/正式），content: 对应润色后的文本）
- changes: 修改要点说明（一句话，说明主要做了哪些调整）

要求：
1. 保留原意，不改变事实信息和核心立场
2. 修正明显的语法错误或病句
3. 不要过度改写避免失真
4. 各版本控制在 20-150 字

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    variants = result.get("variants", [])
    # 规范化 variants 结构
    clean_variants = []
    if isinstance(variants, list):
        for v in variants:
            if isinstance(v, dict) and "style" in v and "content" in v:
                clean_variants.append({"style": v["style"], "content": v["content"]})
    return {
        "default_version": result.get("default_version", text),
        "variants": clean_variants,
        "changes": result.get("changes", ""),
    }


def draft_email(scene="new", recipient="", topic="", points=None, original=None, language="zh"):
    """邮件起草。

    Args:
        scene: 场景，可选值：new(新邮件) / reply(回复) / forward(转发)。
        recipient: 收件人（名称或称呼）。
        topic: 邮件主题/要点。
        points: 用户要表达的要点列表（字符串列表）。
        original: 原邮件内容（回复/转发场景使用）。
        language: 语言，zh 或 en。

    Returns:
        dict: {
            subject: 邮件主题,
            body: 邮件正文（含称呼和署名）,
            placeholders: 需用户补充的信息列表
        }
    """
    points = points or []
    points_text = "\n".join(f"- {p}" for p in points) if points else "- （用户未提供具体要点，请根据主题自行起草）"
    original_text = f"\n原邮件内容：\n{original}\n" if original else ""
    lang_note = "请用英文撰写。" if language == "en" else "请用中文撰写。"

    prompt = f"""请起草一封邮件。

场景：{scene}（new=新邮件，reply=回复，forward=转发）
收件人：{recipient}
主题/要点：
{points_text}
{original_text}
{lang_note}

请以 JSON 格式返回，严格包含以下字段：
- subject: 邮件主题
- body: 邮件正文（含称呼、正文分段、结尾客套和署名）
- placeholders: 需要用户补充的信息列表（字符串数组，如具体日期、数据等，用 [待补充：xxx] 标记的位置也要在此列出；如无需补充返回空数组）

要求：
1. 信息完整但不啰嗦，正文控制在 200 字以内
2. 不要编造用户没提供的具体事实（数字、人名、日期），用 [待补充：xxx] 标记
3. 默认使用商务正式风格
4. 称呼和署名要符合{language}邮件习惯

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)
    return {
        "subject": result.get("subject", topic),
        "body": result.get("body", ""),
        "placeholders": result.get("placeholders", []),
    }


def extract_information(text, types=None):
    """信息抽取。

    从文本中提取结构化信息。

    Args:
        text: 待抽取的文本。
        types: 要抽取的信息类型列表，可选值：人名/时间/金额/地点/动作/组织。
               为空时抽取所有识别到的类型。

    Returns:
        dict: {
            人名: [...], 时间: [...], 金额: [...],
            地点: [...], 动作: [...], 组织: [...]
        }
    """
    if not text or not text.strip():
        return {}

    type_hint = f"只抽取以下类型：{', '.join(types)}。" if types else "抽取所有能识别到的类型。"

    prompt = f"""请从以下文本中提取结构化信息。

文本：
{text}

{type_hint}

请以 JSON 格式返回，包含以下字段（没有对应信息的字段返回空数组）：
- 人名: 涉及的人员名单（字符串数组）
- 时间: 日期、时间节点、截止日期（字符串数组，尽量统一为 YYYY-MM-DD 格式，无法解析的保留原文）
- 金额: 涉及的资金、预算、金额（字符串数组，保留原文表述）
- 地点: 场所、地址（字符串数组）
- 动作: 需要执行的事项（字符串数组）
- 组织: 涉及的团队、部门、机构（字符串数组）

要求：
1. 只抽取原文明确出现的信息，不推断、不补全
2. 每个抽取项尽量简短（一句话以内）
3. 如果文本太短或无信息可抽取，对应字段返回空数组

只返回 JSON，不要任何额外文字。"""
    result = _ai_call(prompt, expect_json=True)

    all_types = ["人名", "时间", "金额", "地点", "动作", "组织"]
    if types:
        # 只保留用户指定的类型
        return {t: result.get(t, []) for t in types if t in all_types}
    return {t: result.get(t, []) for t in all_types}
