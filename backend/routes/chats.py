from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from dependencies import get_db
from models import Contact, Message, UserContact, User, FileCollectionTask
from datetime import datetime
from typing import Optional

router = APIRouter()

@router.get("/contacts/{user_id}")
def get_contacts(user_id: int, db: Session = Depends(get_db)):
    user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
    contact_ids = [uc.contact_id for uc in user_contacts]
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
    result = []
    for contact in contacts:
        last_msg = db.query(Message).filter(Message.contact_id == contact.id).order_by(Message.created_at.desc()).first()
        # For 1-on-1 chats, display the other participant's name
        display_name = contact.name
        if not contact.is_group:
            other_uc = db.query(UserContact).filter(
                UserContact.contact_id == contact.id,
                UserContact.user_id != user_id
            ).first()
            if other_uc:
                other_user = db.query(User).filter(User.id == other_uc.user_id).first()
                if other_user:
                    display_name = other_user.name
        result.append({
            "id": contact.id,
            "name": display_name,
            "avatar": contact.avatar,
            "is_group": contact.is_group,
            "last_message": last_msg.content if last_msg else "",
            "last_time": last_msg.created_at.isoformat() if last_msg else ""
        })
    return result

@router.get("/contacts/{contact_id}/members")
def get_group_members(contact_id: int, db: Session = Depends(get_db)):
    """获取某个群聊/会话的所有成员列表。

    通过 UserContact 关联表反查所有属于该 contact 的用户。
    """
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"detail": "会话不存在"}, 404
    user_contacts = db.query(UserContact).filter(
        UserContact.contact_id == contact_id
    ).all()
    user_ids = [uc.user_id for uc in user_contacts]
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    return [
        {
            "id": u.id,
            "name": u.name,
            "avatar": u.avatar,
        }
        for u in users
    ]

@router.get("/messages")
def get_messages(user_id: int, contact_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.contact_id == contact_id).order_by(Message.created_at.asc()).all()
    result = []
    for msg in messages:
        reply_data = None
        if msg.reply_to_id:
            ref = db.query(Message).filter(Message.id == msg.reply_to_id).first()
            if ref:
                reply_data = {
                    "id": ref.id,
                    "sender_name": ref.sender.name,
                    "content": ref.content[:80]
                }
        # 检查是否已创建过文件收集任务
        file_collected = False
        if msg.message_type == "file" and msg.file_id:
            existing_task = db.query(FileCollectionTask).filter(
                FileCollectionTask.source_message_id == msg.id
            ).first()
            file_collected = existing_task is not None

        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender.name,
            "content": msg.content,
            "message_type": msg.message_type,
            "file_id": msg.file_id,
            "file_name": msg.file.name if msg.file else "",
            "file_collected": file_collected,
            "created_at": msg.created_at.isoformat(),
            "is_self": msg.sender_id == user_id,
            "reply_to": reply_data
        })
    return result

@router.post("/send")
def send_message(user_id: int = Query(...), contact_id: int = Query(...), content: str = Query(...), message_type: str = Query("text"), file_id: Optional[str] = Query(None), reply_to_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    fid = int(file_id) if file_id and file_id.strip() else None
    rid = int(reply_to_id) if reply_to_id and reply_to_id.strip() else None
    message = Message(
        sender_id=user_id,
        contact_id=contact_id,
        content=content,
        message_type=message_type,
        file_id=fid,
        reply_to_id=rid,
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "content": message.content, "created_at": message.created_at.isoformat()}
