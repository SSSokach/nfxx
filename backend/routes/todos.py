"""消息待办路由：@所有人摘要、@自己待办、私聊待办的管理。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import SessionLocal
from models import (
    ChatSummary, ChatTodoItem, Message, Contact, UserContact, User,
)
from datetime import datetime
from typing import Optional
import glm_ai

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_deadline(deadline_str):
    """将 YYYY-MM-DD 字符串解析为 date 对象，失败返回 None。"""
    if not deadline_str:
        return None
    try:
        return datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  @所有人 消息摘要
# ------------------------------------------------------------------ #

@router.get("/chat-summary/{user_id}")
def get_chat_summary(user_id: int, db: Session = Depends(get_db)):
    """获取 @所有人 消息摘要列表。"""
    summaries = db.query(ChatSummary).filter(
        ChatSummary.user_id == user_id
    ).order_by(ChatSummary.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "source_id": s.source_id,
            "group_name": s.group_name,
            "content": s.content,
            "original_message": s.original_message,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in summaries
    ]


# ------------------------------------------------------------------ #
#  扫描消息
# ------------------------------------------------------------------ #

@router.post("/scan-messages/{user_id}")
def scan_messages(user_id: int, db: Session = Depends(get_db)):
    """扫描用户所有群聊消息，检测 @所有人 和 @自己 的消息，
    调用 AI 生成摘要 / 待办；同时扫描私聊消息提取待办。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "用户不存在"}

    user_name = user.name  # 当前用户名（如"张三"）

    # 获取该用户的所有联系人（群聊 + 私聊）
    user_contacts = db.query(UserContact).filter(
        UserContact.user_id == user_id
    ).all()
    contact_ids = [uc.contact_id for uc in user_contacts]
    all_contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

    group_contacts = [c for c in all_contacts if c.is_group]
    private_contacts = [c for c in all_contacts if not c.is_group]

    # 已处理的 source_id 集合，避免重复
    existing_summary_ids = {
        s.source_id for s in db.query(ChatSummary).filter(
            ChatSummary.user_id == user_id
        ).all()
    }
    existing_todo_ids = {
        t.source_id for t in db.query(ChatTodoItem).filter(
            ChatTodoItem.user_id == user_id
        ).all()
    }

    summary_count = 0
    group_todo_count = 0
    private_todo_count = 0
    errors = []

    # ---- 1. 群聊消息扫描 ----
    group_contact_ids = [c.id for c in group_contacts]
    group_messages = db.query(Message).filter(
        Message.contact_id.in_(group_contact_ids),
        Message.sender_id != user_id,   # 只看别人发的消息
    ).order_by(Message.created_at.asc()).all()

    for msg in group_messages:
        contact = next((c for c in group_contacts if c.id == msg.contact_id), None)
        group_name = contact.name if contact else ""

        # @所有人 -> 摘要
        if "@所有人" in msg.content and msg.id not in existing_summary_ids:
            try:
                result = glm_ai.summarize_message(msg.content)
                summary = ChatSummary(
                    user_id=user_id,
                    source_id=msg.id,
                    group_name=group_name,
                    content=result.get("summary", msg.content[:100]),
                    original_message=msg.content,
                    created_at=datetime.utcnow(),
                )
                db.add(summary)
                existing_summary_ids.add(msg.id)
                summary_count += 1
            except Exception as e:
                errors.append(f"摘要生成失败(msg={msg.id}): {e}")

        # @自己 -> 待办
        if f"@{user_name}" in msg.content and msg.id not in existing_todo_ids:
            try:
                result = glm_ai.extract_todo(msg.content)
                todo = ChatTodoItem(
                    user_id=user_id,
                    source_id=msg.id,
                    source_type="group",
                    group_name=group_name,
                    content=result.get("content", msg.content[:100]),
                    deadline=_parse_deadline(result.get("deadline")),
                    status="pending",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(todo)
                existing_todo_ids.add(msg.id)
                group_todo_count += 1
            except Exception as e:
                errors.append(f"待办提取失败(msg={msg.id}): {e}")

    # ---- 2. 私聊消息扫描 ----
    for contact in private_contacts:
        # 找到对方用户名
        other_uc = db.query(UserContact).filter(
            UserContact.contact_id == contact.id,
            UserContact.user_id != user_id,
        ).first()
        peer_name = ""
        if other_uc:
            peer_user = db.query(User).filter(User.id == other_uc.user_id).first()
            if peer_user:
                peer_name = peer_user.name

        private_msgs = db.query(Message).filter(
            Message.contact_id == contact.id
        ).order_by(Message.created_at.asc()).all()

        # 逐条检查对方消息，寻找用户回复
        for i, msg in enumerate(private_msgs):
            if msg.sender_id == user_id:
                continue  # 跳过自己发的消息

            # 找到紧接着的用户回复
            user_reply = None
            for j in range(i + 1, len(private_msgs)):
                if private_msgs[j].sender_id == user_id:
                    user_reply = private_msgs[j].content
                    break
                break  # 只看紧接的下一条

            if not user_reply:
                continue

            if msg.id in existing_todo_ids:
                continue

            try:
                result = glm_ai.extract_private_todo(msg.content, user_reply)
                if result.get("should_create_todo"):
                    todo = ChatTodoItem(
                        user_id=user_id,
                        source_id=msg.id,
                        source_type="private",
                        peer_name=result.get("peer_name") or peer_name,
                        content=result.get("content", ""),
                        deadline=_parse_deadline(result.get("deadline")),
                        status="pending",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    db.add(todo)
                    existing_todo_ids.add(msg.id)
                    private_todo_count += 1
            except Exception as e:
                errors.append(f"私聊待办提取失败(msg={msg.id}): {e}")

    db.commit()

    return {
        "summary_count": summary_count,
        "group_todo_count": group_todo_count,
        "private_todo_count": private_todo_count,
        "total": summary_count + group_todo_count + private_todo_count,
        "message": (
            f"扫描完成：生成 {summary_count} 条摘要，"
            f"{group_todo_count} 条群聊待办，"
            f"{private_todo_count} 条私聊待办"
        ),
        "errors": errors if errors else None,
    }


# ------------------------------------------------------------------ #
#  待办列表
# ------------------------------------------------------------------ #

@router.get("/chat-todos/{user_id}")
def get_chat_todos(
    user_id: int,
    status: Optional[str] = Query(None, description="pending/completed/deleted"),
    db: Session = Depends(get_db),
):
    """获取待办列表，支持 status 参数过滤。"""
    query = db.query(ChatTodoItem).filter(ChatTodoItem.user_id == user_id)
    if status:
        query = query.filter(ChatTodoItem.status == status)
    todos = query.order_by(ChatTodoItem.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "source_type": t.source_type,
            "group_name": t.group_name,
            "peer_name": t.peer_name,
            "content": t.content,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in todos
    ]


# ------------------------------------------------------------------ #
#  更新待办状态
# ------------------------------------------------------------------ #

@router.put("/chat-todos/{todo_id}")
def update_chat_todo(
    todo_id: int,
    action: str = Query(..., description="complete/delete/restore/extend"),
    deadline: Optional[str] = Query(None, description="新截止日期 YYYY-MM-DD（extend 时使用）"),
    db: Session = Depends(get_db),
):
    """更新待办状态。

    action 取值：
    - complete: 标记为已完成
    - delete:   标记为已删除
    - restore:  恢复为待处理
    - extend:   延长截止日期（需传 deadline 参数）
    """
    todo = db.query(ChatTodoItem).filter(ChatTodoItem.id == todo_id).first()
    if not todo:
        return {"error": "待办不存在"}

    now = datetime.utcnow()

    if action == "complete":
        todo.status = "completed"
        todo.completed_at = now
    elif action == "delete":
        todo.status = "deleted"
    elif action == "restore":
        todo.status = "pending"
        todo.completed_at = None
    elif action == "extend":
        new_deadline = _parse_deadline(deadline)
        if new_deadline:
            todo.deadline = new_deadline
        else:
            return {"error": "extend 操作需要有效的 deadline 参数 (YYYY-MM-DD)"}
    else:
        return {"error": f"不支持的操作: {action}"}

    todo.updated_at = now
    db.commit()
    db.refresh(todo)

    return {
        "id": todo.id,
        "status": todo.status,
        "deadline": todo.deadline.isoformat() if todo.deadline else None,
        "completed_at": todo.completed_at.isoformat() if todo.completed_at else None,
        "updated_at": todo.updated_at.isoformat() if todo.updated_at else None,
        "message": f"待办已{action}",
    }


# ------------------------------------------------------------------ #
#  从消息直接创建待办
# ------------------------------------------------------------------ #

@router.post("/create-from-message/{user_id}/{message_id}")
def create_todo_from_message(user_id: int, message_id: int, db: Session = Depends(get_db)):
    """从一条消息直接创建待办事项（用户点击"创建待办"气泡时调用）。"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        return {"error": "消息不存在"}

    # 检查是否已存在同 source_id 的待办
    existing = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.source_id == message_id,
    ).first()
    if existing:
        return {"message": "该消息已创建过待办", "todo_id": existing.id}

    # 获取联系人信息
    contact = db.query(Contact).filter(Contact.id == msg.contact_id).first()
    source_type = "group" if (contact and contact.is_group) else "private"
    group_name = contact.name if (contact and contact.is_group) else None
    peer_name = None
    if source_type == "private":
        # 找到对方用户名
        other_uc = db.query(UserContact).filter(
            UserContact.contact_id == msg.contact_id,
            UserContact.user_id != user_id,
        ).first()
        if other_uc:
            peer_user = db.query(User).filter(User.id == other_uc.user_id).first()
            if peer_user:
                peer_name = peer_user.name

    todo = ChatTodoItem(
        user_id=user_id,
        source_id=message_id,
        source_type=source_type,
        group_name=group_name,
        peer_name=peer_name,
        content=msg.content[:200],
        deadline=None,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)

    return {
        "todo_id": todo.id,
        "content": todo.content,
        "source_type": todo.source_type,
        "group_name": todo.group_name,
        "peer_name": todo.peer_name,
        "status": todo.status,
        "message": "待办已创建",
    }


# ------------------------------------------------------------------ #
#  摘要转待办
# ------------------------------------------------------------------ #

@router.post("/chat-todos/{todo_id}/convert")
def convert_summary_to_todo(todo_id: int, db: Session = Depends(get_db)):
    """将 @所有人 消息摘要转为待办事项。

    参数 todo_id 实际为 ChatSummary 的 id。
    """
    summary = db.query(ChatSummary).filter(ChatSummary.id == todo_id).first()
    if not summary:
        return {"error": "摘要不存在"}

    # 检查是否已转换过
    existing = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == summary.user_id,
        ChatTodoItem.source_id == summary.source_id,
        ChatTodoItem.source_type == "group",
    ).first()
    if existing:
        return {"message": "该摘要已转换为待办", "todo_id": existing.id}

    todo = ChatTodoItem(
        user_id=summary.user_id,
        source_id=summary.source_id,
        source_type="group",
        group_name=summary.group_name,
        content=summary.content,
        deadline=None,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)

    return {
        "todo_id": todo.id,
        "content": todo.content,
        "group_name": todo.group_name,
        "status": todo.status,
        "message": "摘要已转换为待办",
    }
