"""消息待办路由：@所有人摘要、@自己待办、私聊待办的管理。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from dependencies import get_db
from models import (
    ChatSummary, ChatTodoItem, Message, Contact, UserContact, User,
    CandidateTodo, ScannedMessage, ScannedEmail, Email, EmailTodoItem,
)
from datetime import datetime
from typing import Optional
import glm_ai

router = APIRouter()


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
    # 批量查询所有 source_id 对应的 contact_id（避免 N+1 查询）
    msg_ids = [t.source_id for t in todos if t.source_id]
    msg_contact_map = {}
    if msg_ids:
        msgs = db.query(Message).filter(Message.id.in_(msg_ids)).all()
        msg_contact_map = {m.id: m.contact_id for m in msgs}
    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "contact_id": msg_contact_map.get(t.source_id) if t.source_id else None,
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


# ------------------------------------------------------------------ #
#  候选待办 (Candidate Todos)
# ------------------------------------------------------------------ #

@router.post("/scan-candidates/{user_id}")
def scan_candidate_todos(user_id: int, db: Session = Depends(get_db)):
    """AI 扫描最近消息，自动检测候选待办（需用户确认）。

    去重逻辑：
    - 已有候选待办记录（pending/confirmed/dismissed）的消息不会重复扫描
    - 已有正式待办（ChatTodoItem）的消息不会重复扫描
    - 只扫描尚未处理过的新消息
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "用户不存在"}
    user_name = user.name

    user_contacts = db.query(UserContact).filter(
        UserContact.user_id == user_id
    ).all()
    contact_ids = [uc.contact_id for uc in user_contacts]
    if not contact_ids:
        return {"new_count": 0, "message": "没有联系人"}

    all_contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

    # === 收集已处理过的 message_id 集合 ===
    # 1. 已扫描过的消息（ScannedMessage 记录表，无论是否检测到候选）
    scanned_msg_ids = {
        sm.message_id for sm in db.query(ScannedMessage).filter(
            ScannedMessage.user_id == user_id,
        ).all()
    }
    # 2. 已有候选待办记录的消息（兼容旧数据，候选待办也记录了 source_message_id）
    candidate_msg_ids = {
        c.source_message_id for c in db.query(CandidateTodo).filter(
            CandidateTodo.user_id == user_id,
            CandidateTodo.source_message_id.isnot(None),
        ).all()
    }
    # 3. 已有正式待办的消息
    todo_msg_ids = {
        t.source_id for t in db.query(ChatTodoItem).filter(
            ChatTodoItem.user_id == user_id,
            ChatTodoItem.source_id.isnot(None),
        ).all()
    }
    processed_ids = scanned_msg_ids | candidate_msg_ids | todo_msg_ids

    # === 查询未处理的消息 ===
    # 优化策略：
    # - 群聊：只取 @所有人 或 @当前用户 的消息（群聊噪声大，@才有相关性）
    # - 私聊：全量取（私聊消息量少，都需要看）
    # - 时间范围：今日消息 与 最近100条 取较大者（保证至少能扫到今天全部 + 历史最近100条）
    from datetime import date as date_cls

    today_start = datetime.combine(date_cls.today(), datetime.min.time())

    # 区分群聊和私聊的 contact_id
    group_contact_ids = [c.id for c in all_contacts if c.is_group]
    private_contact_ids = [c.id for c in all_contacts if not c.is_group]

    # --- 群聊消息：只取 @所有人 或 @当前用户名 的 ---
    group_msgs_today = []
    group_msgs_recent = []
    if group_contact_ids:
        group_today_q = db.query(Message).filter(
            Message.contact_id.in_(group_contact_ids),
            Message.sender_id != user_id,
            Message.created_at >= today_start,
            Message.content.like(f"%@所有人%") | Message.content.like(f"%@{user_name}%"),
        ).all()
        group_msgs_today = group_today_q

        group_recent_q = db.query(Message).filter(
            Message.contact_id.in_(group_contact_ids),
            Message.sender_id != user_id,
            Message.content.like(f"%@所有人%") | Message.content.like(f"%@{user_name}%"),
        ).order_by(Message.created_at.desc()).limit(100).all()
        group_msgs_recent = group_recent_q

    # --- 私聊消息：全量取 ---
    private_msgs_today = []
    private_msgs_recent = []
    if private_contact_ids:
        private_msgs_today = db.query(Message).filter(
            Message.contact_id.in_(private_contact_ids),
            Message.sender_id != user_id,
            Message.created_at >= today_start,
        ).all()

        private_msgs_recent = db.query(Message).filter(
            Message.contact_id.in_(private_contact_ids),
            Message.sender_id != user_id,
        ).order_by(Message.created_at.desc()).limit(100).all()

    # 合并：今日消息 与 最近100条 取并集（去重），实现"较大者"
    # 用 dict 按 message.id 去重，保留 Message 对象
    merged_by_id = {}
    for m in group_msgs_today + group_msgs_recent + private_msgs_today + private_msgs_recent:
        merged_by_id[m.id] = m
    recent_msgs = list(merged_by_id.values())

    unprocessed = [m for m in recent_msgs if m.id not in processed_ids]
    # 注意：此处不再 early-return，即使没有新消息也要继续扫描邮件

    # 构建批量消息（按时间正序）
    unprocessed.sort(key=lambda m: m.created_at)
    messages_batch = []
    for m in unprocessed:
        contact = next((c for c in all_contacts if c.id == m.contact_id), None)
        source_name = contact.name if contact else ""
        source_type = "group" if (contact and contact.is_group) else "private"
        messages_batch.append({
            "id": m.id,
            "sender": m.sender.name if m.sender else "",
            "source": source_name,
            "content": m.content,
            "contact_id": m.contact_id,
            "source_type": source_type,
        })

    # 调用 AI / 规则检测候选待办（消息为空时跳过 AI 调用）
    if messages_batch:
        try:
            candidates = glm_ai.detect_candidate_todos(messages_batch, user_name)
        except Exception as e:
            candidates = []
            errors = f"消息候选检测失败: {e}"
    else:
        candidates = []

    # === 保存候选待办（二次去重，防止并发问题）===
    new_count = 0
    for c in candidates:
        msg_id = c.get("message_id")
        if not msg_id:
            continue
        # 二次检查：确保该消息没有已有的候选待办
        existing = db.query(CandidateTodo).filter(
            CandidateTodo.user_id == user_id,
            CandidateTodo.source_message_id == msg_id,
        ).first()
        if existing:
            continue

        msg_data = next((m for m in messages_batch if m["id"] == msg_id), None)
        if not msg_data:
            continue

        candidate = CandidateTodo(
            user_id=user_id,
            source_message_id=msg_id,
            source_type=msg_data["source_type"],
            source_name=msg_data["source"],
            content=c.get("content", ""),
            deadline=_parse_deadline(c.get("deadline")),
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(candidate)
        new_count += 1

    # === 将本次扫描的所有消息标记为已扫描（无论是否检测到候选）===
    for m in messages_batch:
        # 避免重复插入
        already = db.query(ScannedMessage).filter(
            ScannedMessage.user_id == user_id,
            ScannedMessage.message_id == m["id"],
        ).first()
        if not already:
            db.add(ScannedMessage(
                user_id=user_id,
                message_id=m["id"],
                scanned_at=datetime.utcnow(),
            ))

    msg_new_count = new_count
    msg_scanned_total = len(unprocessed) if 'unprocessed' in locals() else 0

    # === 扫描邮件 → 候选待办 ===
    # 已扫描过的邮件集合
    scanned_email_ids = {
        se.email_id for se in db.query(ScannedEmail).filter(
            ScannedEmail.user_id == user_id,
        ).all()
    }
    # 已有候选待办的邮件
    candidate_email_ids = {
        c.source_email_id for c in db.query(CandidateTodo).filter(
            CandidateTodo.user_id == user_id,
            CandidateTodo.source_email_id.isnot(None),
        ).all()
    }
    # 已有正式邮件待办（只排除未删除的，已删除的允许重新扫描）
    todo_email_ids = {
        int(t.source_id) for t in db.query(EmailTodoItem).filter(
            EmailTodoItem.user_id == user_id,
            EmailTodoItem.source_id.isnot(None),
            EmailTodoItem.status != "deleted",
        ).all()
        if (t.source_id or "").isdigit()
    }
    processed_email_ids = scanned_email_ids | candidate_email_ids | todo_email_ids

    # 只扫描收件箱里的原始邮件（非回复）
    all_emails = db.query(Email).filter(
        Email.user_id == user_id,
        Email.is_reply == False,
    ).order_by(Email.sent_at.desc()).limit(50).all()

    unprocessed_emails = [e for e in all_emails if e.id not in processed_email_ids]
    email_new_count = 0
    if unprocessed_emails:
        # 构建邮件批量数据
        emails_batch = []
        for e in unprocessed_emails:
            emails_batch.append({
                "id": e.id,
                "subject": e.subject or "",
                "sender": e.sender or "",
                "content": e.content or "",
            })
        try:
            email_candidates = glm_ai.detect_email_candidate_todos(emails_batch, user_name)
        except Exception as e:
            email_candidates = []
            errors_email = f"邮件候选检测失败: {e}"
        else:
            errors_email = None

        for c in email_candidates:
            email_id = c.get("id")
            if not email_id:
                continue
            # 二次去重
            existing = db.query(CandidateTodo).filter(
                CandidateTodo.user_id == user_id,
                CandidateTodo.source_email_id == email_id,
            ).first()
            if existing:
                continue
            email_data = next((x for x in emails_batch if x["id"] == email_id), None)
            if not email_data:
                continue
            candidate = CandidateTodo(
                user_id=user_id,
                source_message_id=None,
                source_email_id=email_id,
                source_type="email",
                source_name=email_data["subject"],
                content=c.get("content", ""),
                deadline=_parse_deadline(c.get("deadline")),
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(candidate)
            email_new_count += 1

        # 标记本次扫描的邮件
        for e in emails_batch:
            already = db.query(ScannedEmail).filter(
                ScannedEmail.user_id == user_id,
                ScannedEmail.email_id == e["id"],
            ).first()
            if not already:
                db.add(ScannedEmail(
                    user_id=user_id,
                    email_id=e["id"],
                    scanned_at=datetime.utcnow(),
                ))

    db.commit()

    total_new = msg_new_count + email_new_count
    email_scanned_total = len(unprocessed_emails)
    msg_str = f"检测 {msg_scanned_total} 条新消息，发现 {msg_new_count} 条消息候选待办"
    email_str = f"检测 {email_scanned_total} 封新邮件，发现 {email_new_count} 条邮件候选待办"
    return {
        "new_count": total_new,
        "message": f"扫描完成：{msg_str}；{email_str}",
        "scanned_total": msg_scanned_total + email_scanned_total,
        "message_candidates": msg_new_count,
        "email_candidates": email_new_count,
        "already_processed": (len(recent_msgs) - msg_scanned_total) if 'recent_msgs' in locals() else 0,
    }


@router.get("/candidates/{user_id}")
def get_candidate_todos(
    user_id: int,
    status: Optional[str] = Query(None, description="pending/confirmed/dismissed"),
    db: Session = Depends(get_db),
):
    """获取候选待办列表。"""
    query = db.query(CandidateTodo).filter(CandidateTodo.user_id == user_id)
    if status:
        query = query.filter(CandidateTodo.status == status)
    else:
        query = query.filter(CandidateTodo.status == "pending")
    candidates = query.order_by(CandidateTodo.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "source_message_id": c.source_message_id,
            "source_email_id": c.source_email_id,
            "source_type": c.source_type,
            "source_name": c.source_name,
            "content": c.content,
            "deadline": c.deadline.isoformat() if c.deadline else None,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in candidates
    ]


@router.post("/candidates/{candidate_id}/confirm")
def confirm_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """确认候选待办：转为正式待办。
    - source_type 为 email 时，创建 EmailTodoItem
    - 其他来源（group/private）创建 ChatTodoItem
    """
    candidate = db.query(CandidateTodo).filter(CandidateTodo.id == candidate_id).first()
    if not candidate:
        return {"error": "候选待办不存在"}
    if candidate.status != "pending":
        return {"error": f"该候选待办已处理（状态: {candidate.status}）"}

    now = datetime.utcnow()

    if candidate.source_type == "email":
        # 查找邮件以补全 subject/sender
        email = db.query(Email).filter(Email.id == candidate.source_email_id).first() if candidate.source_email_id else None
        todo = EmailTodoItem(
            user_id=candidate.user_id,
            source_id=str(candidate.source_email_id) if candidate.source_email_id else "",
            subject=email.subject if email else (candidate.source_name or ""),
            sender=email.sender if email else "",
            content=candidate.content,
            deadline=candidate.deadline,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        db.add(todo)
        candidate.status = "confirmed"
        candidate.updated_at = now
        db.commit()
        db.refresh(todo)
        return {
            "todo_id": todo.id,
            "candidate_id": candidate.id,
            "todo_type": "email",
            "content": todo.content,
            "status": "confirmed",
            "message": "候选待办已确认并转为邮件待办",
        }

    # 创建正式消息待办
    todo = ChatTodoItem(
        user_id=candidate.user_id,
        source_id=candidate.source_message_id,
        source_type=candidate.source_type,
        group_name=candidate.source_name if candidate.source_type == "group" else None,
        peer_name=candidate.source_name if candidate.source_type == "private" else None,
        content=candidate.content,
        deadline=candidate.deadline,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(todo)

    # 更新候选待办状态
    candidate.status = "confirmed"
    candidate.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(todo)

    return {
        "todo_id": todo.id,
        "candidate_id": candidate.id,
        "content": todo.content,
        "status": "confirmed",
        "message": "候选待办已确认并转为正式待办",
    }


@router.post("/candidates/{candidate_id}/dismiss")
def dismiss_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """忽略候选待办。"""
    candidate = db.query(CandidateTodo).filter(CandidateTodo.id == candidate_id).first()
    if not candidate:
        return {"error": "候选待办不存在"}
    if candidate.status != "pending":
        return {"error": f"该候选待办已处理（状态: {candidate.status}）"}

    candidate.status = "dismissed"
    candidate.updated_at = datetime.utcnow()
    db.commit()

    return {
        "candidate_id": candidate.id,
        "status": "dismissed",
        "message": "候选待办已忽略",
    }


@router.post("/rescan-emails/{user_id}")
def rescan_emails(user_id: int, db: Session = Depends(get_db)):
    """重置邮件扫描记录，使所有邮件可以在下次扫描时重新被检测。

    删除该用户的 ScannedEmail 记录，以及 pending/dismissed 状态的邮件候选待办。
    已确认（confirmed）的候选和正式邮件待办不受影响，但其关联的邮件仍会重新扫描。
    """
    # 删除已扫描邮件记录
    db.query(ScannedEmail).filter(ScannedEmail.user_id == user_id).delete()
    # 删除未确认和已忽略的邮件候选待办（保留 confirmed 的）
    db.query(CandidateTodo).filter(
        CandidateTodo.user_id == user_id,
        CandidateTodo.source_email_id.isnot(None),
        CandidateTodo.status.in_(["pending", "dismissed"]),
    ).delete()
    db.commit()

    return {
        "user_id": user_id,
        "message": "邮件扫描记录已重置，可重新扫描邮件",
    }
