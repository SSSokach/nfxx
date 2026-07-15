"""文件收集路由：通过 AI 读取 Excel 模板，自动为未填写人创建待办。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import SessionLocal
from models import (
    FileCollectionTask, FileCollectionItem, Message, Contact, User, UserContact,
    ChatTodoItem, File,
)
from services.excel_analyzer import read_excel_template, analyze_excel_with_ai
from datetime import datetime, date, timedelta
from typing import Optional
import re
import os

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_deadline(deadline_str):
    if not deadline_str:
        return None
    try:
        return datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except Exception:
        return None


# ------------------------------------------------------------------ #
#  核心：从消息检测 Excel 文件收集请求，读取 Excel 提取待填写人
# ------------------------------------------------------------------ #

@router.post("/detect-from-message/{message_id}")
def detect_from_message(message_id: int, db: Session = Depends(get_db)):
    """检测群聊消息中的 Excel 文件收集请求。"""
    return _detect_file_collection(message_id, db)


def _detect_file_collection(message_id: int, db: Session):
    """检测群聊消息中的 Excel 文件收集请求（核心逻辑，可被其他模块调用）。
    
    流程：
    1. 检查消息是否在群聊中发送，且附带 Excel 文件
    2. 用 AI/规则读取 Excel 模板，提取姓名列中的待填写人名单
    3. 将名单匹配到系统用户
    4. 创建文件收集任务 + 为每个未填写人创建待办
    5. 为发起人创建进度跟踪待办
    """
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        return {"detected": False, "error": "消息不存在"}

    contact = db.query(Contact).filter(Contact.id == msg.contact_id).first()
    if not contact or not contact.is_group:
        return {"detected": False, "reason": "非群聊消息"}

    # 检查是否已创建过收集任务
    existing = db.query(FileCollectionTask).filter(
        FileCollectionTask.source_message_id == message_id
    ).first()
    if existing:
        return {"detected": False, "reason": "该消息已创建过收集任务"}

    content = msg.content or ""

    # === 如果消息附带文件，优先用 Excel 分析 ===
    if msg.file_id:
        file_obj = db.query(File).filter(File.id == msg.file_id).first()
        if file_obj and file_obj.name.endswith((".xlsx", ".xls")):
            # 读取 Excel 模板
            analysis = analyze_excel_with_ai(file_obj.id, file_obj.name, content)
            if "error" in analysis:
                return {"detected": False, "error": analysis["error"]}

            # 从 Excel 中提取的待填写人名单
            excel_names = analysis.get("assignees", [])
            unfilled_names = analysis.get("unfilled", [])

            if not excel_names:
                return {"detected": False, "reason": "Excel 中未找到待填写人"}

            # 将 Excel 中的姓名匹配到系统用户
            users = db.query(User).all()
            name_to_user = {u.name: u for u in users}

            matched_assignees = []
            unmatched_names = []
            for name in excel_names:
                if name in name_to_user:
                    matched_assignees.append(name_to_user[name])
                else:
                    unmatched_names.append(name)

            if not matched_assignees:
                return {
                    "detected": False,
                    "reason": f"Excel 中的姓名无法匹配到系统用户: {excel_names}",
                    "excel_names": excel_names,
                }

            # 创建文件收集任务
            initiator = db.query(User).filter(User.id == msg.sender_id).first()
            file_name = file_obj.name
            deadline = analysis.get("deadline")
            description = content[:200] if content else f"填写{file_name}"

            task = FileCollectionTask(
                initiator_user_id=msg.sender_id,
                source_message_id=message_id,
                group_name=contact.name,
                file_name=file_name,
                description=description,
                deadline=_parse_deadline(deadline),
                status="collecting",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(task)
            db.flush()

            # 为每个匹配到的待填写人创建明细
            for assignee in matched_assignees:
                # 根据 Excel 分析结果判断是否已填写
                person_detail = next(
                    (p for p in analysis.get("people_detail", []) if p["name"] == assignee.name),
                    None,
                )
                is_filled = person_detail["filled"] if person_detail else False

                item = FileCollectionItem(
                    task_id=task.id,
                    assignee_user_id=assignee.id,
                    assignee_name=assignee.name,
                    status="submitted" if is_filled else "pending",
                    submitted_at=datetime.utcnow() if is_filled else None,
                    created_at=datetime.utcnow(),
                )
                db.add(item)

            total = len(matched_assignees)
            filled_count = analysis.get("filled_count", 0)

            # 发起人待办（跟踪进度）
            initiator_todo = ChatTodoItem(
                user_id=msg.sender_id,
                source_id=message_id,
                source_type="group",
                group_name=contact.name,
                content=f"[文件收集] {file_name} - 等待 {total} 人提交（{filled_count}/{total}）",
                deadline=_parse_deadline(deadline),
                status="pending",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(initiator_todo)

            # 为未填写人创建待办
            todo_created = 0
            for assignee in matched_assignees:
                person_detail = next(
                    (p for p in analysis.get("people_detail", []) if p["name"] == assignee.name),
                    None,
                )
                if person_detail and person_detail["filled"]:
                    continue  # 已填写的跳过

                assignee_todo = ChatTodoItem(
                    user_id=assignee.id,
                    source_id=message_id,
                    source_type="group",
                    group_name=contact.name,
                    content=f"[填写文件] {file_name} - 由 {initiator.name} 发起" + (f" ({description})" if description else ""),
                    deadline=_parse_deadline(deadline),
                    status="pending",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(assignee_todo)
                todo_created += 1

            db.commit()

            return {
                "detected": True,
                "task_id": task.id,
                "file_name": file_name,
                "total": total,
                "filled_count": filled_count,
                "unfilled_count": total - filled_count,
                "todos_created": todo_created,
                "unmatched_names": unmatched_names,
                "message": f"已读取Excel模板，共{total}人待填写，已填写{filled_count}人，为{todo_created}名未填写人创建了待办",
            }

    # === 没有附带 Excel 文件的常规检测 ===
    collect_keywords = ["填写", "提交", "收集", "汇总", "填报", "收一下", "交一下"]
    file_keywords = ["文件", "文档", "表格", "周报", "月报", "报告", "清单", "模板"]

    is_collect = any(kw in content for kw in collect_keywords)
    has_file_ref = any(kw in content for kw in file_keywords)

    if not is_collect or not has_file_ref:
        return {"detected": False, "reason": "未检测到文件收集意图"}

    # 提取文件名
    file_name = "未命名文件"
    for kw in file_keywords:
        if kw in content:
            idx = content.find(kw)
            start = max(0, idx - 10)
            end = min(len(content), idx + len(kw) + 10)
            file_name = content[start:end].strip()
            break

    # 提取截止时间
    deadline = _extract_deadline(content)

    # 获取群成员作为待填写人
    group_user_ids = db.query(UserContact).filter(
        UserContact.contact_id == contact.id
    ).all()
    assignee_ids = [uc.user_id for uc in group_user_ids if uc.user_id != msg.sender_id]

    if not assignee_ids:
        return {"detected": False, "reason": "群聊中没有其他成员"}

    initiator = db.query(User).filter(User.id == msg.sender_id).first()

    task = FileCollectionTask(
        initiator_user_id=msg.sender_id,
        source_message_id=message_id,
        group_name=contact.name,
        file_name=file_name[:50],
        description=content[:200],
        deadline=_parse_deadline(deadline),
        status="collecting",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(task)
    db.flush()

    assignees = db.query(User).filter(User.id.in_(assignee_ids)).all()
    for assignee in assignees:
        db.add(FileCollectionItem(
            task_id=task.id,
            assignee_user_id=assignee.id,
            assignee_name=assignee.name,
            status="pending",
            created_at=datetime.utcnow(),
        ))

    # 发起人待办
    db.add(ChatTodoItem(
        user_id=msg.sender_id,
        source_id=message_id,
        source_type="group",
        group_name=contact.name,
        content=f"[文件收集] {file_name[:50]} - 等待 {len(assignees)} 人提交（0/{len(assignees)}）",
        deadline=_parse_deadline(deadline),
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))

    # 填写人待办
    for assignee in assignees:
        db.add(ChatTodoItem(
            user_id=assignee.id,
            source_id=message_id,
            source_type="group",
            group_name=contact.name,
            content=f"[填写文件] {file_name[:50]} - 由 {initiator.name} 发起",
            deadline=_parse_deadline(deadline),
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

    db.commit()
    return {
        "detected": True,
        "task_id": task.id,
        "file_name": file_name[:50],
        "total": len(assignees),
        "todos_created": len(assignees),
        "message": f"文件收集任务已创建，已为 {len(assignees)} 人创建待办",
    }


# ------------------------------------------------------------------ #
#  进度扫描：重新读取 Excel 检查填写状态，更新待办
# ------------------------------------------------------------------ #

@router.post("/scan-progress/{task_id}")
def scan_progress(task_id: int, db: Session = Depends(get_db)):
    """重新读取 Excel 文件，检查每个人的填写状态，更新待办。
    
    流程：
    1. 读取 Excel 文件
    2. 对比每人的填写状态
    3. 新填写的 → 标记为已提交，更新填写人待办为完成
    4. 更新发起人待办的进度显示
    5. 为仍然未填写的人确保有待办存在
    """
    task = db.query(FileCollectionTask).filter(FileCollectionTask.id == task_id).first()
    if not task:
        return {"error": "任务不存在"}

    # 找到关联的文件
    msg = db.query(Message).filter(Message.id == task.source_message_id).first()
    file_obj = None
    if msg and msg.file_id:
        file_obj = db.query(File).filter(File.id == msg.file_id).first()

    if not file_obj:
        # 尝试通过文件名查找
        file_obj = db.query(File).filter(File.name == task.file_name).first()

    if not file_obj:
        return {"error": "找不到关联的Excel文件"}

    # 读取 Excel
    result = read_excel_template(file_obj.id, file_obj.name)
    if "error" in result:
        return result

    # 获取当前任务的所有填写项
    items = db.query(FileCollectionItem).filter(
        FileCollectionItem.task_id == task_id
    ).all()

    # 更新每个填写项的状态
    newly_submitted = 0
    for item in items:
        person = next((p for p in result["people"] if p["name"] == item.assignee_name), None)
        if person and person["filled"] and item.status != "submitted":
            # 新填写了
            item.status = "submitted"
            item.submitted_at = datetime.utcnow()
            newly_submitted += 1

            # 更新填写人待办为完成
            assignee_todos = db.query(ChatTodoItem).filter(
                ChatTodoItem.user_id == item.assignee_user_id,
                ChatTodoItem.source_id == task.source_message_id,
            ).all()
            for at in assignee_todos:
                if "[填写文件]" in at.content and task.file_name in at.content:
                    at.status = "completed"
                    at.completed_at = datetime.utcnow()
                    at.updated_at = datetime.utcnow()
                    break

    # 计算最新进度
    submitted = sum(1 for i in items if i.status == "submitted")
    total = len(items)

    # 更新发起人待办进度
    initiator_todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == task.initiator_user_id,
        ChatTodoItem.source_id == task.source_message_id,
    ).all()
    for it in initiator_todos:
        if "[文件收集]" in it.content and task.file_name in it.content:
            if submitted == total:
                it.content = f"[文件收集] {task.file_name} - 全部已提交（{submitted}/{total}）✓"
                task.status = "completed"
            else:
                it.content = f"[文件收集] {task.file_name} - 等待 {total} 人提交（{submitted}/{total}）"
            it.updated_at = datetime.utcnow()
            break

    task.updated_at = datetime.utcnow()
    db.commit()

    # 返回未填写人名单
    unfilled = [
        i.assignee_name for i in items if i.status != "submitted"
    ]

    return {
        "task_id": task_id,
        "total": total,
        "submitted": submitted,
        "unfilled_count": total - submitted,
        "newly_submitted": newly_submitted,
        "unfilled_names": unfilled,
        "message": f"扫描完成：{submitted}/{total} 已填写" + (f"，新增 {newly_submitted} 人提交" if newly_submitted > 0 else ""),
    }


# ------------------------------------------------------------------ #
#  获取任务列表 / 详情 / 提交
# ------------------------------------------------------------------ #

@router.get("/tasks/{user_id}")
def get_collection_tasks(user_id: int, db: Session = Depends(get_db)):
    """获取用户相关的文件收集任务。"""
    initiated = db.query(FileCollectionTask).filter(
        FileCollectionTask.initiator_user_id == user_id
    ).order_by(FileCollectionTask.created_at.desc()).all()

    assigned_items = db.query(FileCollectionItem).filter(
        FileCollectionItem.assignee_user_id == user_id
    ).all()
    assigned_task_ids = {item.task_id for item in assigned_items}

    tasks = []

    for t in initiated:
        items = db.query(FileCollectionItem).filter(
            FileCollectionItem.task_id == t.id
        ).all()
        submitted = sum(1 for i in items if i.status == "submitted")
        total = len(items)
        tasks.append({
            "task_id": t.id,
            "role": "initiator",
            "file_name": t.file_name,
            "description": t.description,
            "group_name": t.group_name,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "total": total,
            "submitted": submitted,
            "progress": f"{submitted}/{total}",
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "items": [
                {
                    "assignee_name": i.assignee_name,
                    "status": i.status,
                    "submitted_at": i.submitted_at.isoformat() if i.submitted_at else None,
                }
                for i in items
            ],
        })

    for tid in assigned_task_ids:
        t = db.query(FileCollectionTask).filter(FileCollectionTask.id == tid).first()
        if not t:
            continue
        my_item = next((i for i in assigned_items if i.task_id == tid), None)
        initiator = db.query(User).filter(User.id == t.initiator_user_id).first()
        tasks.append({
            "task_id": t.id,
            "role": "assignee",
            "file_name": t.file_name,
            "description": t.description,
            "group_name": t.group_name,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "my_status": my_item.status if my_item else "pending",
            "item_id": my_item.id if my_item else None,
            "initiator": initiator.name if initiator else "",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return tasks


@router.post("/items/{item_id}/submit")
def submit_collection_item(
    item_id: int,
    file_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """待填写人提交文件。"""
    item = db.query(FileCollectionItem).filter(FileCollectionItem.id == item_id).first()
    if not item:
        return {"error": "填写项不存在"}

    if item.status == "submitted":
        return {"message": "已提交过", "item_id": item.id}

    item.status = "submitted"
    item.submitted_file_id = file_id
    item.submitted_at = datetime.utcnow()

    task = db.query(FileCollectionTask).filter(FileCollectionTask.id == item.task_id).first()
    if task:
        all_items = db.query(FileCollectionItem).filter(
            FileCollectionItem.task_id == task.id
        ).all()
        submitted = sum(1 for i in all_items if i.status == "submitted")
        total = len(all_items)

        # 更新发起人待办
        initiator_todos = db.query(ChatTodoItem).filter(
            ChatTodoItem.user_id == task.initiator_user_id,
            ChatTodoItem.source_id == task.source_message_id,
        ).all()
        for it in initiator_todos:
            if "[文件收集]" in it.content and task.file_name in it.content:
                if submitted == total:
                    it.content = f"[文件收集] {task.file_name} - 全部已提交（{submitted}/{total}）✓"
                    task.status = "completed"
                else:
                    it.content = f"[文件收集] {task.file_name} - 等待 {total} 人提交（{submitted}/{total}）"
                it.updated_at = datetime.utcnow()
                break

        # 更新填写人待办为已完成
        assignee_todos = db.query(ChatTodoItem).filter(
            ChatTodoItem.user_id == item.assignee_user_id,
            ChatTodoItem.source_id == task.source_message_id,
        ).all()
        for at in assignee_todos:
            if "[填写文件]" in at.content and task.file_name in at.content:
                at.status = "completed"
                at.completed_at = datetime.utcnow()
                at.updated_at = datetime.utcnow()
                break

        task.updated_at = datetime.utcnow()

    db.commit()
    return {"item_id": item.id, "status": "submitted", "message": "提交成功"}


@router.get("/tasks/{task_id}/detail")
def get_task_detail(task_id: int, db: Session = Depends(get_db)):
    """获取文件收集任务详细进度。"""
    task = db.query(FileCollectionTask).filter(FileCollectionTask.id == task_id).first()
    if not task:
        return {"error": "任务不存在"}

    items = db.query(FileCollectionItem).filter(
        FileCollectionItem.task_id == task_id
    ).all()
    submitted = sum(1 for i in items if i.status == "submitted")
    total = len(items)

    return {
        "task_id": task.id,
        "file_name": task.file_name,
        "description": task.description,
        "group_name": task.group_name,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "status": task.status,
        "total": total,
        "submitted": submitted,
        "progress": f"{submitted}/{total}",
        "items": [
            {
                "item_id": i.id,
                "assignee_name": i.assignee_name,
                "status": i.status,
                "submitted_at": i.submitted_at.isoformat() if i.submitted_at else None,
            }
            for i in items
        ],
    }


# ------------------------------------------------------------------ #
#  辅助函数
# ------------------------------------------------------------------ #

def _extract_deadline(content):
    """从消息内容中提取截止时间。"""
    m = re.search(r'(\d{1,2})月(\d{1,2})号?', content)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            return date(date.today().year, month, day).isoformat()
        except ValueError:
            pass
    if "今天" in content:
        return date.today().isoformat()
    elif "明天" in content:
        return (date.today() + timedelta(days=1)).isoformat()
    elif "本周五" in content or "周五" in content:
        today = date.today()
        days_ahead = (4 - today.weekday() + 7) % 7
        return (today + timedelta(days=days_ahead)).isoformat()
    elif "下周一" in content or "周一" in content:
        today = date.today()
        days_ahead = (0 - today.weekday() + 7) % 7
        return (today + timedelta(days=days_ahead)).isoformat()
    elif "下周" in content:
        return (date.today() + timedelta(days=7)).isoformat()
    return None
