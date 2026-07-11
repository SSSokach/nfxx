from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import SessionLocal
from models import Contact, Message, UserContact, User
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/contacts/{user_id}")
def get_contacts(user_id: int, db: Session = Depends(get_db)):
    user_contacts = db.query(UserContact).filter(UserContact.user_id == user_id).all()
    contact_ids = [uc.contact_id for uc in user_contacts]
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
    result = []
    for contact in contacts:
        last_msg = db.query(Message).filter(Message.contact_id == contact.id).order_by(Message.created_at.desc()).first()
        result.append({
            "id": contact.id,
            "name": contact.name,
            "avatar": contact.avatar,
            "is_group": contact.is_group,
            "last_message": last_msg.content if last_msg else "",
            "last_time": last_msg.created_at.isoformat() if last_msg else ""
        })
    return result

@router.get("/messages")
def get_messages(user_id: int, contact_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.contact_id == contact_id).order_by(Message.created_at.asc()).all()
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender.name,
            "content": msg.content,
            "message_type": msg.message_type,
            "file_id": msg.file_id,
            "file_name": msg.file.name if msg.file else "",
            "created_at": msg.created_at.isoformat(),
            "is_self": msg.sender_id == user_id
        })
    return result

@router.post("/send")
def send_message(user_id: int, contact_id: int, content: str, message_type: str = "text", file_id: int = None, db: Session = Depends(get_db)):
    message = Message(
        sender_id=user_id,
        contact_id=contact_id,
        content=content,
        message_type=message_type,
        file_id=file_id,
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return {"id": message.id, "content": message.content, "created_at": message.created_at.isoformat()}
