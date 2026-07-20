"""在线表格路由：支持自定义列、发送追踪、自动生成待办。

核心能力：
1. 创建在线表格（自定义列类型：text/number/date/select/name）
2. 列结构增删改（创建后仍可调整）
3. 发送给他人时自动创建追踪 + 为每个待填写人生成待办
4. 统一追踪视图：融合 OnlineForm 和 FileCollectionTask
5. 填写时按列类型校验，并同步追踪进度
"""
import json
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import SessionLocal
from models import (
    OnlineForm, OnlineFormRow, FormTracker, ChatTodoItem,
    User, UserContact, Contact, Message, File,
)
from services.excel_analyzer import read_excel_template

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ Schemas ============

class ColumnDef(BaseModel):
    key: str
    label: str
    type: str = "text"  # name / text / number / date / select
    required: bool = False
    editable: bool = True
    options: Optional[List[str]] = None  # 仅 type=select 使用


class CreateFormRequest(BaseModel):
    creator_id: int
    contact_id: int
    title: str
    columns: List[ColumnDef]
    required_members: List[str]  # 待填写人姓名列表
    deadline: Optional[str] = None  # YYYY-MM-DD
    send_message: bool = True  # 是否在群聊中发送表格消息并自动追踪


class UpdateColumnsRequest(BaseModel):
    columns: List[ColumnDef]


class FillRowRequest(BaseModel):
    member_name: str
    member_user_id: Optional[int] = None
    data: dict  # {col_key: value}


class AddMembersRequest(BaseModel):
    members: List[str]  # 追加待填写人


# ============ 工具函数 ============

def _parse_deadline(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _normalize_columns(cols: List[ColumnDef]):
    """规范化列定义：保证有 name 列、key 唯一。"""
    result = []
    has_name = False
    for c in cols:
        item = {
            "key": c.key,
            "label": c.label,
            "type": c.type,
            "required": c.required,
            "editable": c.editable if c.type != "name" else False,
        }
        if c.type == "select" and c.options:
            item["options"] = c.options
        if c.type == "name":
            has_name = True
        result.append(item)
    # 如果用户没定义 name 列，自动补一个
    if not has_name:
        result.insert(0, {
            "key": "name", "label": "姓名", "type": "name",
            "required": True, "editable": False,
        })
    return result


def _sync_tracker(db: Session, form: OnlineForm):
    """同步关联的 FormTracker：根据行数据计算进度。"""
    tracker = db.query(FormTracker).filter(
        FormTracker.online_form_id == form.id
    ).first()
    if not tracker:
        return None

    rows = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form.id
    ).all()
    filled = [r.member_name for r in rows if r.filled]
    tracker.filled_members = ",".join(filled)
    tracker.last_checked = datetime.utcnow()
    if len(filled) >= len(form.required_members.split(",")) if form.required_members else False:
        tracker.status = "completed"
    else:
        tracker.status = "tracking"
    tracker.updated_at = datetime.utcnow()
    db.commit()
    return tracker


def _create_todos_for_members(db: Session, form: OnlineForm, tracker: FormTracker,
                              initiator: User, members: List[str]):
    """为每个待填写人生成待办（自动跳过发起人自己）。

    注意：这里只创建 [填写表格] 待办（别人让我填的）。
    发起人的追踪进度通过 "表格追踪" tab 的 FormTracker 单独展示，
    不再写入 ChatTodoItem（避免待办和追踪混在一起）。
    """
    existing_contents = {t.content for t in db.query(ChatTodoItem).filter(
        ChatTodoItem.source_type == "group",
        ChatTodoItem.group_name == tracker.form_name,
    ).all()}
    for name in members:
        # 跳过发起人自己 —— 发起人不需要填写，只需在"表格追踪"tab 追踪
        if name == initiator.name:
            continue
        user = db.query(User).filter(User.name == name).first()
        if not user:
            continue
        content = f"[填写表格] {form.title} - 由 {initiator.name} 发起"
        if content in existing_contents:
            continue
        todo = ChatTodoItem(
            user_id=user.id,
            source_type="group",
            group_name=tracker.form_name,
            content=content,
            form_id=form.id,  # 关联在线表格，前端可据此跳转
            deadline=form.deadline,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(todo)
    db.commit()


def _update_initiator_todo(db: Session, form: OnlineForm, tracker: FormTracker):
    """更新发起人追踪进度。

    注意：不再写入 ChatTodoItem（追踪≠待办）。
    进度更新只同步到 FormTracker，由"表格追踪"tab 展示。
    """
    # 只同步 FormTracker 的 filled_members 和 status
    required = form.required_members.split(",") if form.required_members else []
    filled = tracker.filled_members.split(",") if tracker.filled_members else []
    filled_count = len([m for m in required if m in filled])
    total = len(required)
    if total > 0 and filled_count >= total:
        tracker.status = "completed"
    else:
        tracker.status = "tracking"
    tracker.last_checked = datetime.utcnow()
    tracker.updated_at = datetime.utcnow()
    db.commit()


def _complete_member_todo(db: Session, form: OnlineForm, member_name: str):
    """标记某个填写人的待办为完成。

    精确匹配：只标记 content 同时满足以下条件的待办：
    - content 以 "[填写表格] {form.title}" 开头
    - 该待办的 user 对应的 User.name 等于 member_name（按用户匹配，而非字符串包含）
    """
    member_user = db.query(User).filter(User.name == member_name).first()
    if not member_user:
        return
    todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == member_user.id,
        ChatTodoItem.content.like(f"[填写表格] {form.title}%"),
        ChatTodoItem.status == "pending",
    ).all()
    for t in todos:
        t.status = "completed"
        t.completed_at = datetime.utcnow()
    db.commit()


# ============ 路由 ============

@router.post("/create")
def create_form(req: CreateFormRequest, db: Session = Depends(get_db)):
    """创建在线表格 + 自动创建追踪 + 为待填写人生成待办。"""
    creator = db.query(User).filter(User.id == req.creator_id).first()
    if not creator:
        raise HTTPException(404, "创建人不存在")
    contact = db.query(Contact).filter(Contact.id == req.contact_id).first()
    if not contact:
        raise HTTPException(404, "会话不存在")

    cols = _normalize_columns(req.columns)
    form = OnlineForm(
        creator_id=req.creator_id,
        contact_id=req.contact_id,
        title=req.title,
        columns=json.dumps(cols, ensure_ascii=False),
        required_members=",".join(req.required_members),
        deadline=_parse_deadline(req.deadline),
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(form)
    db.flush()

    # 为每个待填写人创建空行
    for name in req.required_members:
        user = db.query(User).filter(User.name == name).first()
        row = OnlineFormRow(
            form_id=form.id,
            member_name=name,
            member_user_id=user.id if user else None,
            data=json.dumps({"name": name}, ensure_ascii=False),
            filled=False,
            created_at=datetime.utcnow(),
        )
        db.add(row)

    # 创建关联追踪器
    tracker = FormTracker(
        user_id=req.creator_id,
        contact_id=req.contact_id,
        form_name=req.title,
        form_url=f"/api/online-forms/{form.id}",
        online_form_id=form.id,
        required_members=",".join(req.required_members),
        filled_members="",
        deadline=form.deadline,
        status="tracking",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tracker)
    db.commit()
    db.refresh(form)
    db.refresh(tracker)

    # 为待填写人生成待办
    _create_todos_for_members(db, form, tracker, creator, req.required_members)

    return {
        "form_id": form.id,
        "tracker_id": tracker.id,
        "title": form.title,
        "columns": cols,
        "required_members": req.required_members,
        "message": f"表格已创建，已为 {len(req.required_members)} 人生成待办",
    }


@router.get("/{form_id}")
def get_form(form_id: int, db: Session = Depends(get_db)):
    """获取表格详情（含列定义 + 所有行数据 + 进度）。"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    rows = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id
    ).order_by(OnlineFormRow.created_at.asc()).all()
    required = form.required_members.split(",") if form.required_members else []
    filled = [r.member_name for r in rows if r.filled]
    return {
        "id": form.id,
        "title": form.title,
        "columns": json.loads(form.columns),
        "required_members": required,
        "filled_members": filled,
        "deadline": form.deadline.isoformat() if form.deadline else None,
        "status": form.status,
        "creator_id": form.creator_id,
        "contact_id": form.contact_id,
        "progress": {
            "total": len(required),
            "filled": len(filled),
            "percent": round(len(filled) / len(required) * 100, 1) if required else 0,
        },
        "rows": [
            {
                "id": r.id,
                "member_name": r.member_name,
                "member_user_id": r.member_user_id,
                "data": json.loads(r.data),
                "filled": r.filled,
                "filled_at": r.filled_at.isoformat() if r.filled_at else None,
            }
            for r in rows
        ],
    }


@router.put("/{form_id}/columns")
def update_columns(form_id: int, req: UpdateColumnsRequest, db: Session = Depends(get_db)):
    """更新表格列结构（支持创建后增删改列）。

    注意：删除列时，已有行数据中对应的 key 会被移除。
    """
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    if form.status == "closed":
        raise HTTPException(400, "表格已关闭，无法修改列结构")

    new_cols = _normalize_columns(req.columns)
    old_cols = {c["key"]: c for c in json.loads(form.columns)}
    new_keys = {c["key"] for c in new_cols}

    form.columns = json.dumps(new_cols, ensure_ascii=False)
    form.updated_at = datetime.utcnow()

    # 同步行数据：移除已删除的列
    rows = db.query(OnlineFormRow).filter(OnlineFormRow.form_id == form_id).all()
    for r in rows:
        data = json.loads(r.data)
        data = {k: v for k, v in data.items() if k in new_keys}
        r.data = json.dumps(data, ensure_ascii=False)
        r.updated_at = datetime.utcnow()

    db.commit()
    return {"ok": True, "columns": new_cols}


@router.post("/{form_id}/fill")
def fill_row(form_id: int, req: FillRowRequest, db: Session = Depends(get_db)):
    """填写自己的行（按列类型校验）。"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    if form.status == "closed":
        raise HTTPException(400, "表格已关闭")

    cols = json.loads(form.columns)
    # 校验必填项
    for c in cols:
        if c.get("required") and c["key"] != "name":
            if c["key"] not in req.data or not str(req.data[c["key"]]).strip():
                raise HTTPException(400, f"必填项「{c['label']}」不能为空")
        # 校验 select 类型
        if c["type"] == "select" and c["key"] in req.data:
            if req.data[c["key"]] and req.data[c["key"]] not in c.get("options", []):
                raise HTTPException(400, f"「{c['label']}」的值不在选项中")

    # 查找或创建行
    row = db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id,
        OnlineFormRow.member_name == req.member_name,
    ).first()
    if not row:
        user = db.query(User).filter(User.id == req.member_user_id).first() if req.member_user_id else None
        row = OnlineFormRow(
            form_id=form_id,
            member_name=req.member_name,
            member_user_id=req.member_user_id,
            data=json.dumps({"name": req.member_name}, ensure_ascii=False),
            filled=False,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.flush()

    # 合并数据（name 列不可改）
    old_data = json.loads(row.data)
    for k, v in req.data.items():
        if k == "name":
            continue
        old_data[k] = v
    row.data = json.dumps(old_data, ensure_ascii=False)
    row.filled = True
    row.filled_at = datetime.utcnow()
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)

    # 同步追踪器
    tracker = _sync_tracker(db, form)
    # 更新发起人待办进度
    if tracker:
        _update_initiator_todo(db, form, tracker)
        # 标记填写人待办完成
        _complete_member_todo(db, form, req.member_name)

    return {
        "ok": True,
        "row_id": row.id,
        "filled": True,
        "progress": {
            "total": len(form.required_members.split(",")) if form.required_members else 0,
            "filled": len([r for r in db.query(OnlineFormRow).filter(
                OnlineFormRow.form_id == form_id, OnlineFormRow.filled == True
            ).all()]),
        },
    }


@router.post("/{form_id}/check")
def check_progress(form_id: int, db: Session = Depends(get_db)):
    """手动检测进度。"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    tracker = _sync_tracker(db, form)
    if tracker:
        _update_initiator_todo(db, form, tracker)
    return get_form(form_id, db)


@router.get("/list/{user_id}")
def list_forms(user_id: int, db: Session = Depends(get_db)):
    """列出用户创建的表格。"""
    forms = db.query(OnlineForm).filter(
        OnlineForm.creator_id == user_id
    ).order_by(OnlineForm.created_at.desc()).all()
    result = []
    for f in forms:
        required = f.required_members.split(",") if f.required_members else []
        filled = db.query(OnlineFormRow).filter(
            OnlineFormRow.form_id == f.id,
            OnlineFormRow.filled == True,
        ).count()
        result.append({
            "id": f.id,
            "title": f.title,
            "columns": json.loads(f.columns),
            "required_count": len(required),
            "filled_count": filled,
            "deadline": f.deadline.isoformat() if f.deadline else None,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    return result


@router.post("/{form_id}/add-members")
def add_members(form_id: int, req: AddMembersRequest, db: Session = Depends(get_db)):
    """追加待填写人（会自动创建空行 + 待办）。"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    if form.status == "closed":
        raise HTTPException(400, "表格已关闭")

    existing = {r.member_name for r in db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id
    ).all()}
    required = set(form.required_members.split(",") if form.required_members else [])
    for name in req.members:
        if name in existing:
            continue
        user = db.query(User).filter(User.name == name).first()
        db.add(OnlineFormRow(
            form_id=form_id,
            member_name=name,
            member_user_id=user.id if user else None,
            data=json.dumps({"name": name}, ensure_ascii=False),
            filled=False,
            created_at=datetime.utcnow(),
        ))
        required.add(name)

    form.required_members = ",".join(required)
    form.updated_at = datetime.utcnow()

    # 更新追踪器
    tracker = db.query(FormTracker).filter(
        FormTracker.online_form_id == form_id
    ).first()
    if tracker:
        tracker.required_members = form.required_members
        tracker.updated_at = datetime.utcnow()
        _update_initiator_todo(db, form, tracker)

    db.commit()

    # 为新增成员生成待办
    initiator = db.query(User).filter(User.id == form.creator_id).first()
    if initiator and tracker:
        _create_todos_for_members(db, form, tracker, initiator, req.members)

    return {"ok": True, "required_members": list(required)}


@router.post("/{form_id}/close")
def close_form(form_id: int, db: Session = Depends(get_db)):
    """关闭表格。"""
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")
    form.status = "closed"
    form.updated_at = datetime.utcnow()
    tracker = db.query(FormTracker).filter(
        FormTracker.online_form_id == form_id
    ).first()
    if tracker:
        tracker.status = "completed"
        tracker.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": "closed"}


@router.delete("/{form_id}")
def delete_form(form_id: int, db: Session = Depends(get_db)):
    """彻底删除在线表格。

    会级联删除：
    - OnlineFormRow（行数据）
    - FormTracker（追踪记录）
    - ChatTodoItem（关联的 [填写表格] 待办）

    用于发起人主动终止追踪的场景（即使表格未填写完毕）。
    """
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")

    title = form.title

    # 删除行数据
    db.query(OnlineFormRow).filter(
        OnlineFormRow.form_id == form_id
    ).delete(synchronize_session=False)

    # 删除追踪器
    db.query(FormTracker).filter(
        FormTracker.online_form_id == form_id
    ).delete(synchronize_session=False)

    # 删除关联的待办（[填写表格] {title}）
    db.query(ChatTodoItem).filter(
        ChatTodoItem.form_id == form_id,
    ).delete(synchronize_session=False)

    # 删除表格本身
    db.delete(form)
    db.commit()

    return {
        "ok": True,
        "message": f"已删除表格《{title}》及其追踪记录和关联待办",
    }


# ============ 催办：向群聊发送 @未填写人 消息 ============

@router.post("/{form_id}/remind")
def remind_unfilled(form_id: int, db: Session = Depends(get_db)):
    """向表格所在群聊发送催办消息，@所有未填写人。

    会在 contact_id 对应的会话中插入一条由发起人发送的系统消息：
    "@李四 @王五 请尽快填写表格《{标题}》，截止日期：{deadline}"
    """
    form = db.query(OnlineForm).filter(OnlineForm.id == form_id).first()
    if not form:
        raise HTTPException(404, "表格不存在")

    tracker = db.query(FormTracker).filter(
        FormTracker.online_form_id == form_id
    ).first()
    if not tracker:
        raise HTTPException(404, "追踪记录不存在")

    required = tracker.required_members.split(",") if tracker.required_members else []
    filled = tracker.filled_members.split(",") if tracker.filled_members else []
    unfilled = [m for m in required if m not in filled]
    if not unfilled:
        return {"ok": True, "message": "全员已填写，无需催办", "unfilled_count": 0}

    # 构造催办消息内容
    at_mentions = " ".join(f"@{m}" for m in unfilled)
    deadline_str = f"，截止日期：{form.deadline.isoformat()}" if form.deadline else ""
    content = f"{at_mentions} 请尽快填写表格《{form.title}》{deadline_str}"

    # 在群聊中插入一条消息（发起人发送）
    msg = Message(
        sender_id=form.creator_id,
        contact_id=form.contact_id,
        content=content,
        message_type="text",
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()

    return {
        "ok": True,
        "message": f"已在群聊中向 {len(unfilled)} 位未填写人发送催办提醒",
        "unfilled_members": unfilled,
        "unfilled_count": len(unfilled),
        "sent_content": content,
    }


# ============ 从 Excel 模板创建在线表格 ============

class CreateFromExcelRequest(BaseModel):
    creator_id: int
    contact_id: int
    file_id: int  # 已上传的 Excel 文件 ID
    title: Optional[str] = None  # 表格标题，不填则用文件名
    deadline: Optional[str] = None


@router.post("/create-from-excel")
def create_from_excel(req: CreateFromExcelRequest, db: Session = Depends(get_db)):
    """上传 Excel → AI 自动识别列结构 + 人员 → 创建在线表格 + 生成待办。

    流程：
    1. 读取 Excel，解析表头作为列定义（全部按 text 类型，姓名列自动识别）
    2. 读取姓名列的所有人作为待填写人
    3. 创建 OnlineForm + FormTracker + 为每个待填写人生成待办
    4. Excel 中已填写的行，自动标记为已填写（跳过待办）
    """
    creator = db.query(User).filter(User.id == req.creator_id).first()
    if not creator:
        raise HTTPException(404, "创建人不存在")
    contact = db.query(Contact).filter(Contact.id == req.contact_id).first()
    if not contact:
        raise HTTPException(404, "会话不存在")

    file_obj = db.query(File).filter(File.id == req.file_id).first()
    if not file_obj:
        raise HTTPException(404, "文件不存在")

    # 解析 Excel
    analysis = read_excel_template(file_obj.id, file_obj.name)
    if "error" in analysis:
        raise HTTPException(400, f"Excel 解析失败: {analysis['error']}")

    headers = analysis.get("headers", [])
    people = analysis.get("people", [])
    if not headers or not people:
        raise HTTPException(400, "Excel 中未找到有效的表头或人员数据")

    # 识别姓名列
    name_col_candidates = ["姓名", "名字", "name", "Name", "NAME", "员工姓名"]
    name_col_index = None
    for i, h in enumerate(headers):
        if h in name_col_candidates:
            name_col_index = i
            break
    if name_col_index is None:
        name_col_index = 0  # 默认第一列为姓名

    # 构造列定义：姓名列 + 其余列
    columns = []
    for i, h in enumerate(headers):
        if i == name_col_index:
            columns.append({
                "key": "name", "label": h or "姓名",
                "type": "name", "required": True, "editable": False,
            })
        else:
            columns.append({
                "key": f"col_{i}", "label": h or f"列{i+1}",
                "type": "text", "required": False, "editable": True,
            })

    # 提取成员名单 + 预填数据
    required_members = [p["name"] for p in people if p["name"]]
    pre_filled = {p["name"]: p["filled"] for p in people if p["name"]}
    pre_filled_data = {}
    for p in people:
        if not p["name"]:
            continue
        row_data = {"name": p["name"]}
        # 把 Excel 中已填写的列数据也带过来
        for i, h in enumerate(headers):
            if i == name_col_index:
                continue
            col_key = f"col_{i}" if i != name_col_index else "name"
            # filled_columns 存的是列名，需要映射回 col_key
            if h in p.get("filled_columns", []):
                row_data[col_key] = "已填写"  # 占位，实际数据需要从 Excel 读取
        pre_filled_data[p["name"]] = row_data

    title = req.title or file_obj.name.rsplit(".", 1)[0]

    # 创建在线表格
    form = OnlineForm(
        creator_id=req.creator_id,
        contact_id=req.contact_id,
        title=title,
        columns=json.dumps(columns, ensure_ascii=False),
        required_members=",".join(required_members),
        deadline=_parse_deadline(req.deadline),
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(form)
    db.flush()

    # 为每个成员创建行（已填写的标记为 filled）
    for name in required_members:
        user = db.query(User).filter(User.name == name).first()
        is_filled = pre_filled.get(name, False)
        row = OnlineFormRow(
            form_id=form.id,
            member_name=name,
            member_user_id=user.id if user else None,
            data=json.dumps(pre_filled_data.get(name, {"name": name}), ensure_ascii=False),
            filled=is_filled,
            filled_at=datetime.utcnow() if is_filled else None,
            created_at=datetime.utcnow(),
        )
        db.add(row)

    # 创建追踪器
    filled_names = [n for n in required_members if pre_filled.get(n)]
    tracker = FormTracker(
        user_id=req.creator_id,
        contact_id=req.contact_id,
        form_name=title,
        form_url=f"/api/online-forms/{form.id}",
        online_form_id=form.id,
        required_members=",".join(required_members),
        filled_members=",".join(filled_names),
        deadline=form.deadline,
        status="tracking" if len(filled_names) < len(required_members) else "completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tracker)
    db.commit()
    db.refresh(form)
    db.refresh(tracker)

    # 为未填写的人生成待办
    unfilled_members = [n for n in required_members if not pre_filled.get(n)]
    if unfilled_members:
        _create_todos_for_members(db, form, tracker, creator, unfilled_members)
    # 更新发起人待办进度
    _update_initiator_todo(db, form, tracker)

    return {
        "form_id": form.id,
        "tracker_id": tracker.id,
        "title": title,
        "columns": columns,
        "required_members": required_members,
        "pre_filled_count": len(filled_names),
        "unfilled_count": len(unfilled_members),
        "message": f"已从 Excel 创建表格，识别到 {len(required_members)} 人，"
                   f"其中 {len(filled_names)} 人已填写，{len(unfilled_members)} 人待填写（已生成待办）",
    }


# ============ 统一追踪视图 ============

@router.get("/trackers/{user_id}")
def list_trackers(user_id: int, db: Session = Depends(get_db)):
    """统一追踪视图：融合 OnlineForm 和 FileCollectionTask。"""
    result = []

    # 1. OnlineForm 关联的 trackers
    of_trackers = db.query(FormTracker).filter(
        FormTracker.user_id == user_id,
        FormTracker.online_form_id.isnot(None),
    ).order_by(FormTracker.created_at.desc()).all()
    for t in of_trackers:
        form = db.query(OnlineForm).filter(OnlineForm.id == t.online_form_id).first()
        if not form:
            continue
        required = t.required_members.split(",") if t.required_members else []
        filled = t.filled_members.split(",") if t.filled_members else []
        unfilled = [m for m in required if m not in filled]
        result.append({
            "tracker_id": t.id,
            "type": "online_form",
            "source_id": form.id,
            "title": form.title,
            "form_url": t.form_url,
            "contact_id": t.contact_id,
            "required_members": required,
            "filled_members": filled,
            "unfilled_members": unfilled,
            "deadline": form.deadline.isoformat() if form.deadline else None,
            "status": t.status,
            "last_checked": t.last_checked.isoformat() if t.last_checked else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "progress": {
                "total": len(required),
                "filled": len(filled),
                "percent": round(len(filled) / len(required) * 100, 1) if required else 0,
            },
        })

    # 2. FileCollectionTask 关联的 trackers
    from models import FileCollectionTask, FileCollectionItem
    fc_trackers = db.query(FormTracker).filter(
        FormTracker.user_id == user_id,
        FormTracker.file_collection_task_id.isnot(None),
    ).order_by(FormTracker.created_at.desc()).all()
    for t in fc_trackers:
        task = db.query(FileCollectionTask).filter(
            FileCollectionTask.id == t.file_collection_task_id
        ).first()
        if not task:
            continue
        items = db.query(FileCollectionItem).filter(
            FileCollectionItem.task_id == task.id
        ).all()
        required = [i.assignee_name for i in items]
        filled = [i.assignee_name for i in items if i.status == "submitted"]
        unfilled = [i.assignee_name for i in items if i.status != "submitted"]
        result.append({
            "tracker_id": t.id,
            "type": "file_collection",
            "source_id": task.id,
            "title": task.file_name,
            "form_url": None,
            "contact_id": t.contact_id,
            "required_members": required,
            "filled_members": filled,
            "unfilled_members": unfilled,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "status": t.status,
            "last_checked": t.last_checked.isoformat() if t.last_checked else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "progress": {
                "total": len(required),
                "filled": len(filled),
                "percent": round(len(filled) / len(required) * 100, 1) if required else 0,
            },
        })

    # 3. 纯 FormTracker（无关联，兼容旧数据）
    pure_trackers = db.query(FormTracker).filter(
        FormTracker.user_id == user_id,
        FormTracker.online_form_id.is_(None),
        FormTracker.file_collection_task_id.is_(None),
    ).order_by(FormTracker.created_at.desc()).all()
    for t in pure_trackers:
        required = t.required_members.split(",") if t.required_members else []
        filled = t.filled_members.split(",") if t.filled_members else []
        unfilled = [m for m in required if m not in filled]
        result.append({
            "tracker_id": t.id,
            "type": "tracker_only",
            "source_id": t.id,
            "title": t.form_name,
            "form_url": t.form_url,
            "contact_id": t.contact_id,
            "required_members": required,
            "filled_members": filled,
            "unfilled_members": unfilled,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "last_checked": t.last_checked.isoformat() if t.last_checked else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "progress": {
                "total": len(required),
                "filled": len(filled),
                "percent": round(len(filled) / len(required) * 100, 1) if required else 0,
            },
        })

    # 按创建时间倒序
    result.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return result
