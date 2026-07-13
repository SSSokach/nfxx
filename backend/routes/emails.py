"""邮件路由：邮件列表、邮件待办、邮件回复追踪。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import SessionLocal
from models import Email, EmailTodoItem, EmailTracker
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
#  邮件列表
# ------------------------------------------------------------------ #

@router.get("/list/{user_id}")
def get_email_list(user_id: int, db: Session = Depends(get_db)):
    """获取用户邮件列表。"""
    emails = db.query(Email).filter(
        Email.user_id == user_id
    ).order_by(Email.sent_at.desc()).all()
    return [
        {
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
        }
        for e in emails
    ]


# ------------------------------------------------------------------ #
#  扫描邮件 -> 生成邮件待办
# ------------------------------------------------------------------ #

@router.post("/scan/{user_id}")
def scan_emails(user_id: int, db: Session = Depends(get_db)):
    """扫描用户邮件，调用 AI 判断是否需要处理，生成邮件待办。"""
    emails = db.query(Email).filter(
        Email.user_id == user_id,
        Email.is_reply == False,   # 只扫描原始邮件，不扫描回复邮件
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
        # 获取原始邮件的收件部门列表
        all_depts = [
            d.strip() for d in (tracker.unreplied_depts or "").split("|")
            if d.strip()
        ] + [
            d.strip() for d in (tracker.replied_depts or "").split("|")
            if d.strip()
        ]
        all_depts = list(set(all_depts))

        # 查找该邮件的回复邮件
        email_id_int = int(tracker.email_id) if tracker.email_id.isdigit() else None
        if email_id_int is None:
            continue

        reply_emails = db.query(Email).filter(
            Email.is_reply == True,
            Email.reply_to_email_id == email_id_int,
        ).all()

        # 收集已回复的部门
        replied_set = set()
        for d in (tracker.replied_depts or "").split("|"):
            d = d.strip()
            if d:
                replied_set.add(d)

        for reply in reply_emails:
            if reply.sender_dept:
                replied_set.add(reply.sender_dept.strip())

        # 计算未回复部门
        unreplied_set = set(all_depts) - replied_set

        old_replied = set(d.strip() for d in (tracker.replied_depts or "").split("|") if d.strip())
        if replied_set != old_replied:
            updated_count += 1

        tracker.replied_depts = "|".join(sorted(replied_set))
        tracker.unreplied_depts = "|".join(sorted(unreplied_set))
        tracker.last_checked_at = datetime.utcnow()

        # 如果所有部门都已回复，标记为完成
        if all_depts and not unreplied_set:
            tracker.status = "completed"
            completed_count += 1

    db.commit()

    return {
        "checked_count": checked_count,
        "updated_count": updated_count,
        "completed_count": completed_count,
        "message": (
            f"检查完成：检查了 {checked_count} 封追踪邮件，"
            f"{updated_count} 封有新回复，{completed_count} 封已全部回复"
        ),
    }
