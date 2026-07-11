from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import SessionLocal
from models import Message, Contact, File, User, UserContact
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ToolRegistry:
    def __init__(self):
        self.tools = {}
    
    def register(self, name, description):
        def decorator(func):
            self.tools[name] = {"description": description, "func": func}
            return func
        return decorator
    
    def get_tools(self):
        return [{"name": name, "description": info["description"]} for name, info in self.tools.items()]
    
    def call_tool(self, name, **kwargs):
        if name in self.tools:
            return self.tools[name]["func"](**kwargs)
        return {"error": f"Tool {name} not found"}

tool_registry = ToolRegistry()

@tool_registry.register("read_messages", "读取当前用户与指定联系人的聊天记录")
def _read_messages(user_id: int, contact_id: int, db: Session = None):
    if db is None:
        db = next(get_db())
    messages = db.query(Message).filter(Message.contact_id == contact_id).order_by(Message.created_at.asc()).all()
    result = []
    for msg in messages:
        result.append({
            "sender_name": msg.sender.name,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        })
    return {"messages": result}

@tool_registry.register("send_message", "替当前用户向指定联系人发送消息")
def _send_message(user_id: int, contact_id: int, content: str, db: Session = None):
    if db is None:
        db = next(get_db())
    message = Message(
        sender_id=user_id,
        contact_id=contact_id,
        content=content,
        message_type="text",
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"message": "消息发送成功"}

@tool_registry.register("get_file_content", "获取指定文件的内容")
def _get_file_content(file_id: int, db: Session = None):
    if db is None:
        db = next(get_db())
    file = db.query(File).filter(File.id == file_id).first()
    if file:
        return {"name": file.name, "content": file.content}
    return {"error": "文件不存在"}

@tool_registry.register("list_files", "获取当前用户的所有文件列表")
def _list_files(user_id: int, db: Session = None):
    if db is None:
        db = next(get_db())
    files = db.query(File).filter(File.owner_id == user_id).all()
    return {"files": [{"id": f.id, "name": f.name, "file_type": f.file_type} for f in files]}

@tool_registry.register("list_contacts", "获取当前用户的所有联系人列表")
def _list_contacts(user_id: int, db: Session = None):
    if db is None:
        db = next(get_db())
    user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
    contact_ids = [uc.contact_id for uc in user_contacts]
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
    return {"contacts": [{"id": c.id, "name": c.name, "is_group": c.is_group} for c in contacts]}

@router.get("/tools")
def get_tools():
    return {"tools": tool_registry.get_tools()}

@router.post("/call_tool")
def call_tool(user_id: int, tool_name: str, **kwargs):
    db = next(get_db())
    kwargs['db'] = db
    kwargs['user_id'] = user_id
    return tool_registry.call_tool(tool_name, **kwargs)

@router.post("/chat")
def ai_chat(user_id: int, message: str, db: Session = Depends(get_db)):
    tools = tool_registry.get_tools()
    
    tool_name = None
    tool_args = {}
    
    for tool in tools:
        if tool["name"] in message.lower():
            tool_name = tool["name"]
            break
    
    if tool_name == "read_messages":
        contact_name = message.replace("read_messages", "").replace("读取", "").strip()
        contact = db.query(Contact).filter(Contact.name.contains(contact_name)).first()
        if contact:
            tool_args["contact_id"] = contact.id
    
    elif tool_name == "send_message":
        parts = message.replace("send_message", "").replace("发送", "").split("给")
        if len(parts) >= 2:
            contact_name = parts[0].strip()
            content = parts[1].strip()
            contact = db.query(Contact).filter(Contact.name.contains(contact_name)).first()
            if contact:
                tool_args["contact_id"] = contact.id
                tool_args["content"] = content
    
    elif tool_name == "get_file_content":
        file_name = message.replace("get_file_content", "").replace("获取", "").strip()
        file = db.query(File).filter(File.name.contains(file_name)).first()
        if file:
            tool_args["file_id"] = file.id
    
    elif tool_name == "list_files":
        pass
    
    elif tool_name == "list_contacts":
        pass
    
    if tool_name:
        tool_args["user_id"] = user_id
        tool_args["db"] = db
        result = tool_registry.call_tool(tool_name, **tool_args)
        return {"response": f"已执行{tool_name}工具", "result": result}
    
    return {"response": "你好！我是你的AI办公助手。我可以帮你读取聊天记录、发送消息、获取文件内容等。你可以告诉我你想做什么。"}
