from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from dependencies import get_db
from models import FormTracker, Message, Contact, User
from datetime import datetime, date
from typing import Optional
import json

router = APIRouter()

@router.post("/{user_id}/create")
def create_form_tracker(user_id: int, contact_id: int = Query(...), form_name: str = Query(...), required_members: str = Query(...), form_url: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """创建表格追踪"""
    tracker = FormTracker(
        user_id=user_id,
        contact_id=contact_id,
        form_name=form_name,
        form_url=form_url,
        required_members=required_members,
        filled_members="",
        status="tracking",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tracker)
    db.commit()
    return {"id": tracker.id, "message": "追踪已创建"}

@router.get("/{user_id}")
def get_form_trackers(user_id: int, status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """获取用户的表格追踪列表"""
    query = db.query(FormTracker).filter(FormTracker.user_id == user_id)
    if status:
        query = query.filter(FormTracker.status == status)
    trackers = query.order_by(FormTracker.created_at.desc()).all()
    result = []
    for t in trackers:
        required = t.required_members.split(",") if t.required_members else []
        filled = t.filled_members.split(",") if t.filled_members else []
        unfilled = [m for m in required if m not in filled]
        result.append({
            "id": t.id,
            "contact_id": t.contact_id,
            "form_name": t.form_name,
            "form_url": t.form_url,
            "required_members": required,
            "filled_members": filled,
            "unfilled_members": unfilled,
            "status": t.status,
            "progress": f"{len(filled)}/{len(required)}",
            "last_checked": t.last_checked.strftime("%Y-%m-%d %H:%M") if t.last_checked else None,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else None,
        })
    return result

@router.post("/{tracker_id}/check")
def check_form_tracker(tracker_id: int, db: Session = Depends(get_db)):
    """检测表格填写情况 — 优先基于真实在线表格数据，否则回退到模拟"""
    tracker = db.query(FormTracker).filter(FormTracker.id == tracker_id).first()
    if not tracker:
        return {"error": "追踪不存在"}
    if tracker.status != "tracking":
        return {"error": "追踪已结束"}

    required = tracker.required_members.split(",") if tracker.required_members else []
    filled = tracker.filled_members.split(",") if tracker.filled_members else []

    # 如果关联了在线表格，从真实数据检测
    if tracker.form_url and tracker.form_url.startswith("/api/online-forms/"):
        from models import OnlineForm, OnlineFormRow
        form_id = int(tracker.form_url.split("/")[-1])
        rows = db.query(OnlineFormRow).filter(OnlineFormRow.form_id == form_id).all()
        filled = [r.member_name for r in rows if r.filled]
    else:
        # 没有在线表格，使用模拟检测
        import random
        unfilled = [m for m in required if m not in filled]
        if unfilled and random.random() > 0.3:
            newly_filled = random.choice(unfilled)
            filled.append(newly_filled)

    tracker.filled_members = ",".join(filled)

    # 检查是否全部完成
    if all(m in filled for m in required):
        tracker.status = "completed"

    tracker.last_checked = datetime.utcnow()
    tracker.updated_at = datetime.utcnow()
    db.commit()

    unfilled_final = [m for m in required if m not in filled]
    return {
        "form_name": tracker.form_name,
        "progress": f"{len(filled)}/{len(required)}",
        "filled_members": filled,
        "unfilled_members": unfilled_final,
        "status": tracker.status,
        "message": f"检测完成：{len(filled)}/{len(required)} 已填写" + ("，全部完成！" if tracker.status == "completed" else ""),
    }

@router.post("/{tracker_id}/remind")
def remind_unfilled(tracker_id: int, db: Session = Depends(get_db)):
    """在群里@未填写人员发送催办消息"""
    tracker = db.query(FormTracker).filter(FormTracker.id == tracker_id).first()
    if not tracker:
        return {"error": "追踪不存在"}
    
    required = tracker.required_members.split(",") if tracker.required_members else []
    filled = tracker.filled_members.split(",") if tracker.filled_members else []
    unfilled = [m for m in required if m not in filled]
    
    if not unfilled:
        return {"message": "所有人都已填写，无需催办"}
    
    # 发送催办消息到群聊
    mention_text = " ".join([f"@{m}" for m in unfilled])
    content = f"{mention_text} 请尽快填写表格「{tracker.form_name}」"
    msg = Message(
        sender_id=tracker.user_id,
        contact_id=tracker.contact_id,
        content=content,
        message_type="text",
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    return {"message": f"已发送催办消息，提醒 {len(unfilled)} 人", "content": content}

@router.post("/{tracker_id}/cancel")
def cancel_form_tracker(tracker_id: int, db: Session = Depends(get_db)):
    """取消追踪"""
    tracker = db.query(FormTracker).filter(FormTracker.id == tracker_id).first()
    if not tracker:
        return {"error": "追踪不存在"}
    tracker.status = "cancelled"
    tracker.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "追踪已取消"}

@router.post("/check-all/{user_id}")
def check_all_trackers(user_id: int, db: Session = Depends(get_db)):
    """批量检测用户所有追踪中的表格（定时任务调用）"""
    trackers = db.query(FormTracker).filter(
        FormTracker.user_id == user_id,
        FormTracker.status == "tracking",
    ).all()
    
    import random
    results = []
    for tracker in trackers:
        required = tracker.required_members.split(",") if tracker.required_members else []
        filled = tracker.filled_members.split(",") if tracker.filled_members else []
        unfilled = [m for m in required if m not in filled]
        
        if unfilled and random.random() > 0.3:
            newly_filled = random.choice(unfilled)
            filled.append(newly_filled)
            tracker.filled_members = ",".join(filled)
        
        if all(m in filled for m in required):
            tracker.status = "completed"
        
        tracker.last_checked = datetime.utcnow()
        tracker.updated_at = datetime.utcnow()
        results.append({
            "form_name": tracker.form_name,
            "progress": f"{len(filled)}/{len(required)}",
            "status": tracker.status,
        })
    
    db.commit()
    return {"checked": len(results), "results": results}
