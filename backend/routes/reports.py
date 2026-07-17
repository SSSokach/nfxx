"""文件摘要和工作报告路由。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from dependencies import get_db
from models import File, ChatTodoItem, EmailTodoItem
from datetime import datetime
import glm_ai

router = APIRouter()


# ------------------------------------------------------------------ #
#  文件摘要
# ------------------------------------------------------------------ #

@router.post("/file-summary")
def generate_file_summary(file_id: int = Query(..., description="文件ID"), db: Session = Depends(get_db)):
    """生成文件摘要。

    接收 file_id，读取文件内容，调用 AI 生成结构化摘要。
    """
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return {"error": "文件不存在"}

    if not file.content:
        return {"error": "文件内容为空"}

    try:
        result = glm_ai.generate_file_summary(file.content)
        return {
            "file_id": file.id,
            "file_name": file.name,
            "title": result.get("title", file.name),
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", []),
            "action_items": result.get("action_items", []),
            "topics": result.get("topics", []),
        }
    except Exception as e:
        return {"error": f"文件摘要生成失败: {e}"}


# ------------------------------------------------------------------ #
#  工作报告
# ------------------------------------------------------------------ #

@router.post("/work-report/{user_id}")
def generate_work_report(
    user_id: int,
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """生成工作报告。

    接收 start_date 和 end_date 参数，查询已完成和未完成待办，
    调用 AI 生成 Markdown 报告。
    """
    # 解析日期
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "日期格式错误，请使用 YYYY-MM-DD 格式"}

    # 查询该时间段内已完成的待办（chat + email）
    completed_chat_todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.status == "completed",
        ChatTodoItem.completed_at >= start_dt,
        ChatTodoItem.completed_at <= end_dt,
    ).all()

    completed_email_todos = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.status == "completed",
        EmailTodoItem.completed_at >= start_dt,
        EmailTodoItem.completed_at <= end_dt,
    ).all()

    # 查询未完成的待办（截止日期在范围内或创建日期在范围内）
    pending_chat_todos = db.query(ChatTodoItem).filter(
        ChatTodoItem.user_id == user_id,
        ChatTodoItem.status == "pending",
    ).all()

    pending_email_todos = db.query(EmailTodoItem).filter(
        EmailTodoItem.user_id == user_id,
        EmailTodoItem.status == "pending",
    ).all()

    # 组装任务列表文本
    completed_tasks = []
    for t in completed_chat_todos:
        source = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
        completed_tasks.append(f"{source} {t.content}")
    for t in completed_email_todos:
        completed_tasks.append(f"[邮件:{t.subject}] {t.content}")

    pending_tasks = []
    for t in pending_chat_todos:
        source = f"[{t.group_name}]" if t.group_name else (f"[{t.peer_name}]" if t.peer_name else "")
        deadline_str = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
        pending_tasks.append(f"{source} {t.content}{deadline_str}")
    for t in pending_email_todos:
        deadline_str = f" (截止:{t.deadline.isoformat()})" if t.deadline else ""
        pending_tasks.append(f"[邮件:{t.subject}] {t.content}{deadline_str}")

    # 调用 AI 生成报告
    try:
        report = glm_ai.generate_work_report(completed_tasks, pending_tasks)
        if not report:
            report = _generate_fallback_report(
                start_date, end_date, completed_tasks, pending_tasks
            )
    except Exception as e:
        report = _generate_fallback_report(
            start_date, end_date, completed_tasks, pending_tasks
        )

    return {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
        "completed_count": len(completed_tasks),
        "pending_count": len(pending_tasks),
        "report": report,
    }


def _generate_fallback_report(start_date, end_date, completed_tasks, pending_tasks):
    """当 AI 调用失败时的备用报告生成。"""
    completed_text = "\n".join(f"- {t}" for t in completed_tasks) if completed_tasks else "- 暂无"
    pending_text = "\n".join(f"- {t}" for t in pending_tasks) if pending_tasks else "- 暂无"

    return f"""# 工作报告

**报告周期：** {start_date} ~ {end_date}

## 本期工作总结

本期共完成 {len(completed_tasks)} 项工作：

{completed_text}

## 待办事项

当前仍有 {len(pending_tasks)} 项待办未完成：

{pending_text}

## 下周计划

请根据上述待办事项合理安排下周工作，优先处理有截止日期的任务。
"""
