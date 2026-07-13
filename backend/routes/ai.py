from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import SessionLocal
from models import User
import glm_ai

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/tools")
def get_tools():
    """返回可用工具列表（兼容旧接口）。"""
    return {"tools": [
        {"name": "read_chat_history", "description": "读取与指定联系人的聊天记录"},
        {"name": "send_message", "description": "替用户向联系人发送消息"},
        {"name": "get_contacts_list", "description": "获取联系人列表"},
        {"name": "get_files_list", "description": "获取文件列表"},
        {"name": "get_file_content", "description": "获取文件内容"},
    ]}

@router.post("/chat")
def ai_chat(user_id: int, message: str, db: Session = Depends(get_db)):
    """与 GLM AI 对话，支持 function calling 工具调用。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"response": "用户不存在", "result": None}

    result = glm_ai.chat_with_ai(user_id, user.name, message)
    return result
