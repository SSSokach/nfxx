from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from dependencies import get_db
from models import User, Message, Contact, UserContact
from typing import Optional
import glm_ai
from token_limiter import check_rate_limit, apply_slowdown, record_usage, estimate_tokens

router = APIRouter()

@router.get("/tools")
def get_tools():
    """返回可用工具列表（兼容旧接口）。"""
    return {"tools": [
        {"name": "read_chat_history", "description": "读取与指定联系人的聊天记录"},
        {"name": "send_message", "description": "替用户向联系人发送消息"},
        {"name": "get_contacts_list", "description": "获取联系人列表"},
        {"name": "get_files_list", "description": "获取文件列表"},
        {"name": "get_file_content", "description": "获取文件内容"},
        {"name": "smart_reply", "description": "AI 生成智能回复建议"},
        {"name": "classify_message", "description": "AI 分析消息意图类别"},
        {"name": "prioritize_todos", "description": "AI 待办优先级排序"},
        {"name": "meeting_minutes", "description": "从群聊提取会议纪要"},
        {"name": "summarize_file", "description": "生成文件结构化摘要"},
        {"name": "search_files", "description": "按关键词搜索文件内容"},
        {"name": "get_recent_messages", "description": "获取最近跨联系人消息"},
    ]}

@router.post("/chat")
def ai_chat(user_id: int, message: str, db: Session = Depends(get_db)):
    """与 GLM AI 对话，支持 function calling 工具调用。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"response": "用户不存在"}

    # 检查用量限制
    limit_check = check_rate_limit(user_id)
    if not limit_check["allowed"]:
        return {
            "response": f"⚠️ {limit_check['reason']}\n\n今日已使用：{limit_check['usage']['request_count']}次请求 / {limit_check['usage']['token_count']} tokens\n每日限额：{limit_check['limits']['request_count']}次请求 / {limit_check['limits']['token_count']} tokens",
            "usage": limit_check["usage"],
            "limits": limit_check["limits"],
        }

    # 根据用量施加延迟（控制响应速度）
    delay = apply_slowdown(user_id)

    result = glm_ai.chat_with_ai(user_id, user.name, message)

    # 记录用量
    input_tokens = estimate_tokens(message)
    output_tokens = estimate_tokens(result.get("response", ""))
    record_usage(user_id, input_tokens + output_tokens)

    return {**result, "usage": limit_check["usage"], "limits": limit_check["limits"], "delay": delay}


@router.get("/usage/{user_id}")
def get_usage(user_id: int):
    """获取用户今日AI用量"""
    from token_limiter import check_rate_limit
    return check_rate_limit(user_id)


# ===== 新增 AI 功能端点 =====

@router.post("/smart-reply")
def smart_reply(
    user_id: int = Query(...),
    message: str = Query(...),
    contact_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """AI 智能回复建议：根据对方消息和上下文生成多个回复选项。"""
    context = ""
    if contact_id:
        msgs = db.query(Message).filter(
            Message.contact_id == contact_id
        ).order_by(Message.created_at.desc()).limit(6).all()
        if len(msgs) > 1:
            lines = []
            for m in reversed(msgs[:-1]):
                lines.append(f"{m.sender.name}: {m.content[:100]}")
            context = "\n".join(lines)

    try:
        result = glm_ai.generate_smart_reply(message, context)
        return {
            "replies": result.get("replies", []),
            "tone": result.get("tone", ""),
        }
    except Exception as e:
        return {"error": f"生成回复失败: {e}", "replies": []}


@router.post("/classify-message")
def classify_message(
    message: str = Query(...),
):
    """AI 消息分类：分析消息的意图类别。"""
    try:
        result = glm_ai.classify_message(message)
        return result
    except Exception as e:
        return {"error": f"分类失败: {e}"}


@router.post("/daily-digest/{user_id}")
def daily_digest(user_id: int):
    """AI 日报：汇总当天消息、待办、邮件动态，生成工作日报。"""
    try:
        report = glm_ai.generate_daily_digest(user_id)
        return {"report": report}
    except Exception as e:
        return {"error": f"日报生成失败: {e}"}


@router.post("/prioritize-todos/{user_id}")
def prioritize_todos(user_id: int, db: Session = Depends(get_db)):
    """AI 待办优先级排序：对所有待办按紧急程度排序。"""
    from models import ChatTodoItem, EmailTodoItem

    chat_todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.status == "pending",
    ).all()
    email_todos = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.status == "pending",
    ).all()

    all_todos = []
    for t in chat_todos:
        dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
        src = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
        all_todos.append(f"{src} {t.content}{dl}")
    for t in email_todos:
        dl = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
        all_todos.append(f"[邮件:{t.subject}] {t.content}{dl}")

    if not all_todos:
        return {"sorted_items": [], "message": "当前没有待办事项"}

    try:
        result = glm_ai.prioritize_todos(all_todos)
        return {"sorted_items": result}
    except Exception as e:
        return {"error": f"排序失败: {e}"}


@router.post("/meeting-minutes")
def meeting_minutes(
    user_id: int = Query(...),
    contact_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """AI 会议纪要：从群聊消息中提取会议纪要。"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"error": "联系人不存在"}

    msgs = db.query(Message).filter(
        Message.contact_id == contact_id
    ).order_by(Message.created_at.asc()).limit(100).all()

    if not msgs:
        return {"error": "该对话没有消息记录"}

    lines = []
    for m in msgs:
        lines.append(f"[{m.created_at.strftime('%H:%M')}] {m.sender.name}: {m.content}")
    messages_text = "\n".join(lines)

    try:
        result = glm_ai.extract_meeting_minutes(messages_text)
        return {
            "contact_name": contact.name,
            **result,
        }
    except Exception as e:
        return {"error": f"提取会议纪要失败: {e}"}