"""在线表格路由 - 创建表格、查看、填写、检测填写进度"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dependencies import get_db
from models import OnlineForm, OnlineFormRow, Message, FormTracker
from datetime import datetime
import json

router = APIRouter()


# ===== 请求模型 =====

class CreateFormRequest(BaseModel):
    creator_id: int
    contact_id: int
    title: str
    columns: list  # [{"key":"name","label":"姓名"},{"key":"progress","label":"进度"}]
    required_members: list  # ["张三","李四","王五"]


class FillRowRequest(BaseModel):
    member_name: str
    data: dict  # {"name":"张三","progress":"50%"}


# ===== API =====

@router.post("/create")
def create_online_form(req: CreateFormRequest, db: Session = Depends(get_db)):
    """创建在线表格，自动为每个需填写人员生成空行"""
    form = OnlineForm(
        creator_id=req.creator_id,
        contact_id=req.contact_id,
        title=req.title,
        columns=json.dumps(req.columns, ensure_ascii=False),
        required_members=",".join(req.required_members),
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(form)
    db.flush()  # 获取 form.id

    # 为每个需填写人员创建空行
    for member in req.required_members:
        row = OnlineFormRow(
            form_id=form.id,
            member_name=member,
            data="{}",
            filled=False,
            created_at=datetime.utcnow(),
        )
        db.add(row)

    # 同时创建一个 FormTracker 关联
    tracker = FormTracker(
        user_id=req.creator_id,
        contact_id=req.contact_id,
        form_name=req.title,
        form_url=f"/api/online-forms/{form.id}",
        required_members=",".join(req.required_members),
        filled_members="",
        status="tracking",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tracker)

    db.commit()
    return {
        "id": form.id,
        "tracker_id": tracker.id,
        "message": f"表格「{req.title}」已创建，共 {len(req.required_members)} 人需填写",
    }


@router.get("/{form_id}")
def get_online_form(form_id: int, db: Session = Depends(get_db)):
    """获取表格详情（含所有行数据）"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        return {"error": "表格不存在"}

    columns = json.loads(form.columns) if form.columns else []
    required = form.required_members.split(",") if form.required_members else []

    rows = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id
    ).all()

    row_data = []
    for r in rows:
        row_data.append({
            "id": r.id,
            "member_name": r.member_name,
            "data": json.loads(r.data) if r.data else {},
            "filled": r.filled,
            "filled_at": r.filled_at.strftime("%Y-%m-%d %H:%M") if r.filled_at else None,
        })

    filled_count = sum(1 for r in rows if r.filled)
    return {
        "id": form.id,
        "title": form.title,
        "columns": columns,
        "required_members": required,
        "rows": row_data,
        "progress": f"{filled_count}/{len(required)}",
        "filled_count": filled_count,
        "total_count": len(required),
        "status": form.status,
        "created_at": form.created_at.strftime("%Y-%m-%d %H:%M") if form.created_at else None,
    }


@router.post("/{form_id}/fill")
def fill_form_row(form_id: int, req: FillRowRequest, db: Session = Depends(get_db)):
    """填写表格（某人填写自己的行）"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        return {"error": "表格不存在"}
    if form.status != "active":
        return {"error": "表格已关闭"}

    row = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id,
        OnlineFormRow.member_name == req.member_name,
    ).first()

    if not row:
        # 该人员不在需填写名单中，自动创建一行
        row = OnlineFormRow(
            form_id=form_id,
            member_name=req.member_name,
            data="{}",
            filled=False,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()

    row.data = json.dumps(req.data, ensure_ascii=False)
    row.filled = True
    row.filled_at = datetime.utcnow()
    db.commit()

    # 同步更新 FormTracker
    _sync_tracker(form_id, db)

    return {"message": f"{req.member_name} 已填写", "filled": True}


@router.post("/{form_id}/check")
def check_form_progress(form_id: int, db: Session = Depends(get_db)):
    """检测表格填写进度"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        return {"error": "表格不存在"}

    required = form.required_members.split(",") if form.required_members else []
    rows = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id
    ).all()

    filled_members = [r.member_name for r in rows if r.filled]
    unfilled_members = [m for m in required if m not in filled_members]
    filled_count = len(filled_members)

    # 同步 FormTracker
    _sync_tracker(form_id, db)

    return {
        "form_id": form_id,
        "title": form.title,
        "progress": f"{filled_count}/{len(required)}",
        "filled_members": filled_members,
        "unfilled_members": unfilled_members,
        "all_done": filled_count == len(required),
    }


@router.get("/list/{user_id}")
def list_user_forms(user_id: int, db: Session = Depends(get_db)):
    """获取用户相关的所有表格"""
    forms = db.query(OnlineForm).filter(
        OnlineForm.creator_id == user_id
    ).order_by(OnlineForm.created_at.desc()).all()

    result = []
    for f in forms:
        required = f.required_members.split(",") if f.required_members else []
        rows = db.query(OnlineFormRow).filter(OnlineFormRow.form_id == f.id).all()
        filled_count = sum(1 for r in rows if r.filled)
        result.append({
            "id": f.id,
            "title": f.title,
            "required_members": required,
            "filled_count": filled_count,
            "total_count": len(required),
            "progress": f"{filled_count}/{len(required)}",
            "status": f.status,
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else None,
        })
    return result


@router.post("/{form_id}/close")
def close_form(form_id: int, db: Session = Depends(get_db)):
    """关闭表格"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        return {"error": "表格不存在"}
    form.status = "closed"
    db.commit()
    return {"message": "表格已关闭"}


def _sync_tracker(form_id: int, db: Session):
    """同步更新 FormTracker 的 filled_members 和 status"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        return

    rows = db.query(OnlineFormRow).filter(OnlineFormRow.form_id == form_id).all()
    filled_members = [r.member_name for r in rows if r.filled]
    required = form.required_members.split(",") if form.required_members else []

    # 更新关联的 FormTracker
    tracker = db.query(FormTracker).filter(
        FormTracker.form_url == f"/api/online-forms/{form_id}"
    ).first()

    if tracker:
        tracker.filled_members = ",".join(filled_members)
        tracker.last_checked = datetime.utcnow()
        tracker.updated_at = datetime.utcnow()
        if all(m in filled_members for m in required):
            tracker.status = "completed"
        db.commit()
