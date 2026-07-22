"""邮件路由：邮件列表、邮件详情、发送邮件、邮件待办、邮件回复追踪。"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dependencies import get_db
from models import Email, EmailTodoItem, EmailTracker, File, User
import re
from datetime import datetime
from typing import Optional, List
import glm_ai


def _check_single_tracker(tracker, db):
    """检查单个邮件追踪器的回复状态（兼容部门级和人名级追踪）。"""
    email_id_int = int(tracker.email_id) if str(tracker.email_id).isdigit() else None
    if email_id_int is None:
        return

    # 所有待追踪对象（可能是部门名或人名）
    all_targets = list(set(
        [d.strip() for d in (tracker.unreplied_depts or "").split("|") if d.strip()]
        + [d.strip() for d in (tracker.replied_depts or "").split("|") if d.strip()]
    ))

    # 查找回复邮件：
    # 1. 直接回复：is_reply=True 且 reply_to_email_id 指向原邮件
    # 2. 兜底匹配：主题以 "Re: 原主题" 开头，且发件人是被追踪人（兼容未标记 is_reply 的情况）
    reply_emails = db.query(Email).filter(
        Email.is_reply == True,
        Email.reply_to_email_id == email_id_int,
    ).all()

    # 兜底：按主题匹配未标记为回复的邮件
    original = db.query(Email).filter(Email.id == email_id_int).first()
    if original:
        base_subject = re.sub(r'^Re:\s*', '', original.subject)
        fallback_replies = db.query(Email).filter(
            Email.subject.like(f"Re: {base_subject}%"),
            Email.is_reply == False,
            Email.folder.in_(["inbox", "sent"]),
        ).all()
        # 去重：避免与已查到的重复
        existing_ids = {r.id for r in reply_emails}
        for fr in fallback_replies:
            if fr.id not in existing_ids and fr.id != email_id_int:
                reply_emails.append(fr)
                existing_ids.add(fr.id)

    # 收集已回复对象
    replied_set = set()
    for d in (tracker.replied_depts or "").split("|"):
        d = d.strip()
        if d:
            replied_set.add(d)

    for reply in reply_emails:
        # 按发件人姓名匹配
        sender_names = _extract_recipient_names(reply.sender or "")
        for name in sender_names:
            if name in all_targets:
                replied_set.add(name)
        # 按部门匹配（兼容旧数据）
        if reply.sender_dept:
            dept = reply.sender_dept.strip()
            if dept in all_targets:
                replied_set.add(dept)

    unreplied_set = set(all_targets) - replied_set
    tracker.replied_depts = "|".join(sorted(replied_set))
    tracker.unreplied_depts = "|".join(sorted(unreplied_set))
    tracker.last_checked_at = datetime.utcnow()

    if all_targets and not unreplied_set:
        tracker.status = "completed"

    db.commit()

router = APIRouter()


def _extract_recipient_names(to_str):
    """从收件人字符串中提取姓名列表，支持 '姓名 <email>' 或纯姓名，多个收件人用逗号/分号分隔。"""
    if not to_str:
        return []
    names = []
    for part in re.split(r'[,;]', to_str):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(.+?)\s*<.+@.+>$', part)
        if m:
            names.append(m.group(1).strip())
        elif '@' not in part:
            names.append(part)
    return names


def _parse_deadline(deadline_str):
    """将 YYYY-MM-DD 字符串解析为 date 对象，失败返回 None。"""
    if not deadline_str:
        return None
    try:
        return datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_attachment_ids(attachment_file_ids):
    """将逗号分隔的 file_id 字符串解析为 List[int]。"""
    if not attachment_file_ids:
        return []
    ids = []
    for part in str(attachment_file_ids).split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def _email_summary_dict(e):
    """邮件列表项（不含附件内容，体积小）。"""
    return {
        "id": e.id,
        "subject": e.subject,
        "sender": e.sender,
        "sender_dept": e.sender_dept,
        "recipients": e.recipients,
        "content": e.content,
        "is_reply": e.is_reply,
        "reply_to_email_id": e.reply_to_email_id,
        "sent_at": e.sent_at.isoformat() if e.sent_at else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "folder": e.folder or "inbox",
        "body_type": e.body_type or "text",
        "has_attachments": len(_parse_attachment_ids(e.attachment_file_ids)) > 0,
    }


def _email_detail_dict(e, db):
    """邮件详情（含附件文件名与内容）。"""
    attachment_ids = _parse_attachment_ids(e.attachment_file_ids)
    attachments = []
    if attachment_ids:
        files = db.query(File).filter(File.id.in_(attachment_ids)).all()
        files_map = {f.id: f for f in files}
        # 保持用户填写的顺序
        for fid in attachment_ids:
            f = files_map.get(fid)
            if f:
                attachments.append({
                    "id": f.id,
                    "name": f.name,
                    "file_type": f.file_type,
                    "content": f.content or "",
                    "size": len(f.content) if f.content else 0,
                })
    return {
        **_email_summary_dict(e),
        "attachment_file_ids": attachment_ids,
        "attachments": attachments,
    }


# ------------------------------------------------------------------ #
#  邮件列表
# ------------------------------------------------------------------ #

@router.get("/list/{user_id}")
def get_email_list(
    user_id: int,
    folder: Optional[str] = Query(None, description="inbox / sent / draft，不填则返回全部"),
    db: Session = Depends(get_db),
):
    """获取用户邮件列表，支持按 folder 过滤。"""
    query = db.query(Email).filter(Email.user_id == user_id)
    if folder:
        query = query.filter(Email.folder == folder)
    emails = query.order_by(Email.sent_at.desc()).all()
    return [_email_summary_dict(e) for e in emails]


# ------------------------------------------------------------------ #
#  邮件详情
# ------------------------------------------------------------------ #

@router.get("/detail/{email_id}")
def get_email_detail(email_id: int, db: Session = Depends(get_db)):
    """获取单封邮件详情，包含附件文件名与内容。"""
    e = db.query(Email).filter(Email.id == email_id).first()
    if not e:
        return {"error": "邮件不存在"}
    return _email_detail_dict(e, db)


# ------------------------------------------------------------------ #
#  发送邮件
# ------------------------------------------------------------------ #

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    content: str
    body_type: str = "markdown"
    attachment_file_ids: List[int] = []
    reply_to_email_id: Optional[int] = None  # 回复的原始邮件ID


@router.post("/send/{user_id}")
def send_email(user_id: int, req: SendEmailRequest, db: Session = Depends(get_db)):
    """发送新邮件（写入已发送箱）。支持回复邮件：传入 reply_to_email_id 即标记为回复。"""
    user = db.query(User).filter(User.id == user_id).first()
    sender_str = f"{user.name} <{user.name.lower()}@company.com>" if user else "me@company.com"
    sender_dept = user.name if user else ""

    attachment_ids_str = ",".join(str(i) for i in req.attachment_file_ids) if req.attachment_file_ids else ""

    # 是否为回复邮件
    is_reply = req.reply_to_email_id is not None

    email = Email(
        user_id=user_id,
        subject=req.subject or "(无主题)",
        sender=sender_str,
        sender_dept=sender_dept,
        recipients=req.to,
        content=req.content,
        is_reply=is_reply,
        reply_to_email_id=req.reply_to_email_id,
        sent_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        folder="sent",
        body_type=req.body_type or "markdown",
        attachment_file_ids=attachment_ids_str,
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    # 为收件人创建收件箱副本，使收件人能在收件箱中看到该邮件
    recipient_names = _extract_recipient_names(req.to)
    if recipient_names:
        recipients = db.query(User).filter(User.name.in_(recipient_names)).all()
        for r in recipients:
            if r.id == user_id:
                continue  # 跳过发件人自己

            # 回复邮件：为每个收件人找到他们本地的原始邮件 ID
            reply_to_id = None
            if is_reply:
                # 找到收件人收件箱/已发送中与原始邮件同主题的邮件
                original = db.query(Email).filter(Email.id == req.reply_to_email_id).first()
                if original:
                    base_subject = re.sub(r'^Re:\s*', '', original.subject)
                    their_original = db.query(Email).filter(
                        Email.user_id == r.id,
                        Email.subject == base_subject,
                        Email.is_reply == False,
                        Email.folder.in_(["inbox", "sent"]),
                    ).first()
                    reply_to_id = their_original.id if their_original else req.reply_to_email_id
                else:
                    reply_to_id = req.reply_to_email_id

            inbox_email = Email(
                user_id=r.id,
                subject=email.subject,
                sender=sender_str,
                sender_dept=sender_dept,
                recipients=req.to,
                content=email.content,
                is_reply=is_reply,
                reply_to_email_id=reply_to_id,
                sent_at=email.sent_at,
                created_at=email.created_at,
                folder="inbox",
                body_type=email.body_type,
                attachment_file_ids=attachment_ids_str,
            )
            db.add(inbox_email)
        db.commit()

    return {
        "id": email.id,
        "folder": email.folder,
        "message": "邮件已发送",
        "email": _email_detail_dict(email, db),
    }


# ------------------------------------------------------------------ #
#  从邮件直接加入待办（用户手动添加，不经过候选）
# ------------------------------------------------------------------ #

@router.post("/add-to-todo/{user_id}/{email_id}")
def add_email_to_todo(user_id: int, email_id: int, db: Session = Depends(get_db)):
    """将一封邮件直接加入待办列表（EmailTodoItem，status=pending）。"""
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == user_id).first()
    if not email:
        return {"error": "邮件不存在"}

    # 去重：同 source_id 已存在则返回已有待办
    existing = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.source_id == str(email_id),
    ).first()
    if existing:
        return {"message": "该邮件已加入待办", "todo_id": existing.id}

    todo = EmailTodoItem(
        user_id=user_id,
        source_id=str(email_id),
        subject=email.subject,
        sender=email.sender,
        content=email.content[:500] if email.content else "",
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
        "subject": todo.subject,
        "status": todo.status,
        "message": "已加入待办列表",
    }


# ------------------------------------------------------------------ #
#  扫描邮件 -> 生成邮件待办
# ------------------------------------------------------------------ #

@router.post("/scan/{user_id}")
def scan_emails(user_id: int, db: Session = Depends(get_db)):
    """扫描用户收件箱邮件，调用 AI 判断是否需要处理，生成邮件待办。"""
    emails = db.query(Email).filter(
        Email.user_id == user_id,
        Email.is_reply == False,   # 只扫描原始邮件，不扫描回复邮件
        Email.folder == "inbox",   # 只扫收件箱，不扫已发送
    ).order_by(Email.sent_at.desc()).all()

    # 已处理的邮件 source_id 集合
    existing_ids = {
        t.source_id for t in db.query(EmailTodoItem).filter(
            EmailTodoItem.user_id == user_id
        ).all()
    }

    todo_count = 0
    skipped_count = 0
    errors = []

    for email in emails:
        source_id = str(email.id)
        if source_id in existing_ids:
            skipped_count += 1
            continue

        try:
            result = glm_ai.extract_email_todo(email.content)
            if result.get("action_required"):
                todo = EmailTodoItem(
                    user_id=user_id,
                    source_id=source_id,
                    subject=email.subject,
                    sender=email.sender,
                    content=result.get("content", ""),
                    deadline=_parse_deadline(result.get("deadline")),
                    status="pending",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(todo)
                existing_ids.add(source_id)
                todo_count += 1
            else:
                # 不需要处理的邮件也标记为已扫描（创建一条 status=no_action 的记录）
                todo = EmailTodoItem(
                    user_id=user_id,
                    source_id=source_id,
                    subject=email.subject,
                    sender=email.sender,
                    content="无需处理",
                    deadline=None,
                    status="no_action",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(todo)
                existing_ids.add(source_id)
                skipped_count += 1
        except Exception as e:
            errors.append(f"邮件扫描失败(email={email.id}): {e}")

    db.commit()

    return {
        "todo_count": todo_count,
        "skipped_count": skipped_count,
        "total": len(emails),
        "message": f"扫描完成：{todo_count} 封邮件需要处理，{skipped_count} 封无需处理",
        "errors": errors if errors else None,
    }


# ------------------------------------------------------------------ #
#  邮件待办列表
# ------------------------------------------------------------------ #

@router.get("/todos/{user_id}")
def get_email_todos(
    user_id: int,
    status: Optional[str] = Query(None, description="pending/completed/deleted"),
    db: Session = Depends(get_db),
):
    """获取邮件待办列表，支持 status 参数过滤。"""
    query = db.query(EmailTodoItem).filter(EmailTodoItem.user_id == user_id)
    if status:
        query = query.filter(EmailTodoItem.status == status)
    else:
        # 默认只显示 pending 和 completed，不显示 no_action
        query = query.filter(EmailTodoItem.status != "no_action")
    todos = query.order_by(EmailTodoItem.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "source_id": t.source_id,
            "subject": t.subject,
            "sender": t.sender,
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
#  更新邮件待办状态
# ------------------------------------------------------------------ #

@router.put("/todos/{todo_id}")
def update_email_todo(
    todo_id: int,
    action: str = Query(..., description="complete/delete/restore/extend"),
    deadline: Optional[str] = Query(None, description="新截止日期 YYYY-MM-DD（extend 时使用）"),
    db: Session = Depends(get_db),
):
    """更新邮件待办状态。"""
    todo = db.query(EmailTodoItem).filter(EmailTodoItem.id == todo_id).first()
    if not todo:
        return {"error": "邮件待办不存在"}

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
        "message": f"邮件待办已{action}",
    }


# ------------------------------------------------------------------ #
#  邮件回复追踪
# ------------------------------------------------------------------ #

@router.get("/trackers/{user_id}")
def get_email_trackers(user_id: int, db: Session = Depends(get_db)):
    """获取邮件回复追踪列表。"""
    trackers = db.query(EmailTracker).filter(
        EmailTracker.user_id == user_id
    ).order_by(EmailTracker.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "email_id": t.email_id,
            "subject": t.subject,
            "sent_at": t.sent_at.isoformat() if t.sent_at else None,
            "replied_depts": t.replied_depts,
            "unreplied_depts": t.unreplied_depts,
            "status": t.status,
            "check_interval_hours": t.check_interval_hours,
            "last_checked_at": t.last_checked_at.isoformat() if t.last_checked_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trackers
    ]


@router.post("/track/{email_id}")
def track_email(email_id: int, db: Session = Depends(get_db)):
    """开始追踪某封邮件的回复。"""
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        return {"error": "邮件不存在"}

    # 检查是否已在追踪
    existing = db.query(EmailTracker).filter(
        EmailTracker.email_id == str(email_id)
    ).first()
    if existing:
        return {"message": "该邮件已在追踪中", "tracker_id": existing.id}

    tracker = EmailTracker(
        user_id=email.user_id,
        email_id=str(email_id),
        subject=email.subject,
        sent_at=email.sent_at,
        replied_depts="",
        unreplied_depts=email.recipients or "",
        status="tracking",
        check_interval_hours=12,
        last_checked_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)

    return {
        "tracker_id": tracker.id,
        "email_id": tracker.email_id,
        "subject": tracker.subject,
        "unreplied_depts": tracker.unreplied_depts,
        "status": tracker.status,
        "message": "已开始追踪邮件回复",
    }


@router.post("/trackers/check/{user_id}")
def check_email_trackers(user_id: int, db: Session = Depends(get_db)):
    """检查邮件回复状态，更新追踪记录。"""
    trackers = db.query(EmailTracker).filter(
        EmailTracker.user_id == user_id,
        EmailTracker.status == "tracking",
    ).all()

    checked_count = 0
    updated_count = 0
    completed_count = 0

    for tracker in trackers:
        checked_count += 1
        old_replied = set(d.strip() for d in (tracker.replied_depts or "").split("|") if d.strip())
        _check_single_tracker(tracker, db)
        new_replied = set(d.strip() for d in (tracker.replied_depts or "").split("|") if d.strip())
        if new_replied != old_replied:
            updated_count += 1
        if tracker.status == "completed":
            completed_count += 1

    return {
        "checked_count": checked_count,
        "updated_count": updated_count,
        "completed_count": completed_count,
        "message": (
            f"检查完成：检查了 {checked_count} 封追踪邮件，"
            f"{updated_count} 封有新回复，{completed_count} 封已全部回复"
        ),
    }


# ============ 邮件事项追踪（人名级） ============

@router.post("/track-sent/{user_id}/{email_id}")
def track_sent_email(user_id: int, email_id: int, db: Session = Depends(get_db)):
    """将已发送的邮件设为事项跟踪项，追踪各收件人的回复情况。"""
    email = db.query(Email).filter(
        Email.id == email_id,
        Email.user_id == user_id,
    ).first()
    if not email:
        raise HTTPException(404, "邮件不存在")

    # 检查是否已在追踪
    existing = db.query(EmailTracker).filter(
        EmailTracker.email_id == str(email_id)
    ).first()
    if existing:
        return {"message": "该邮件已在追踪中", "tracker_id": existing.id}

    # 从收件人字段提取姓名
    recipient_names = _extract_recipient_names(email.recipients or "")
    if not recipient_names:
        # 兼容竖线分隔的部门格式
        recipient_names = [r.strip() for r in (email.recipients or "").split("|") if r.strip()]
    if not recipient_names:
        raise HTTPException(400, "无法解析收件人列表")

    tracker = EmailTracker(
        user_id=user_id,
        email_id=str(email_id),
        subject=email.subject,
        sent_at=email.sent_at,
        replied_depts="",
        unreplied_depts="|".join(recipient_names),
        status="tracking",
        check_interval_hours=12,
        last_checked_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(tracker)
    db.commit()
    db.refresh(tracker)

    # 立即检查一次现有回复
    _check_single_tracker(tracker, db)
    db.refresh(tracker)

    return {
        "tracker_id": tracker.id,
        "email_id": tracker.email_id,
        "subject": tracker.subject,
        "unreplied_depts": tracker.unreplied_depts,
        "replied_depts": tracker.replied_depts,
        "status": tracker.status,
        "message": f"已开始追踪 {len(recipient_names)} 位收件人的回复情况",
    }


@router.delete("/trackers/{tracker_id}")
def delete_email_tracker(tracker_id: int, db: Session = Depends(get_db)):
    """删除邮件追踪记录。"""
    tracker = db.query(EmailTracker).filter(EmailTracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(404, "追踪记录不存在")
    db.delete(tracker)
    db.commit()
    return {"ok": True, "message": "已删除邮件追踪记录"}


@router.post("/trackers/{tracker_id}/ai-summary")
def ai_summary_email_tracker(tracker_id: int, db: Session = Depends(get_db)):
    """AI 总结邮件回复追踪情况。"""
    tracker = db.query(EmailTracker).filter(EmailTracker.id == tracker_id).first()
    if not tracker:
        raise HTTPException(404, "追踪记录不存在")

    # 先检查最新回复状态
    _check_single_tracker(tracker, db)
    db.refresh(tracker)

    replied = [d.strip() for d in (tracker.replied_depts or "").split("|") if d.strip()]
    unreplied = [d.strip() for d in (tracker.unreplied_depts or "").split("|") if d.strip()]
    total = len(replied) + len(unreplied)
    percent = round(len(replied) / total * 100, 1) if total else 0

    detail_lines = []
    for name in replied:
        detail_lines.append(f"- {name}：✅ 已回复")
    for name in unreplied:
        detail_lines.append(f"- {name}：❌ 尚未回复")

    sent_at_str = tracker.sent_at.isoformat() if tracker.sent_at else "时间未知"

    prompt = f"""你是办公助手的AI分析模块。请根据以下邮件回复追踪数据，生成一份简洁的总结报告。

邮件主题：{tracker.subject}
发送时间：{sent_at_str}
应回复人数：{total} 人
已回复人数：{len(replied)} 人
未回复人数：{len(unreplied)} 人
回复率：{percent}%

各人回复详情：
{chr(10).join(detail_lines)}

请生成总结报告：
1. 概括整体回复进度
2. 列出未回复的人员
3. 给出 1-2 条跟进建议（如提醒未回复人员、关注截止时间等）
4. 语气专业、简洁，用中文，总字数控制在 150 字以内
"""

    try:
        summary = glm_ai._ai_call(prompt, expect_json=False)
    except Exception as e:
        summary = (
            f"邮件《{tracker.subject}》回复情况：\n"
            f"回复率 {percent}%（{len(replied)}/{total}）\n"
            f"未回复：{', '.join(unreplied) or '无'}"
        )

    return {
        "ok": True,
        "tracker_id": tracker_id,
        "title": tracker.subject,
        "summary": summary,
        "stats": {
            "total": total,
            "filled": len(replied),
            "unfilled": len(unreplied),
            "percent": percent,
            "deadline": None,
        },
        "details": detail_lines,
    }
