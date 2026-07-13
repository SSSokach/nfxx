from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import SessionLocal
from models import Favorite, Message
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{user_id}")
def get_favorites(user_id: int, db: Session = Depends(get_db)):
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).order_by(Favorite.created_at.desc()).all()
    result = []
    for fav in favs:
        msg = fav.message
        result.append({
            "id": fav.id,
            "message_id": msg.id,
            "content": msg.content,
            "sender_name": msg.sender.name,
            "created_at": fav.created_at.isoformat()
        })
    return result

@router.post("/add")
def add_favorite(user_id: int, message_id: int, db: Session = Depends(get_db)):
    existing = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.message_id == message_id).first()
    if existing:
        return {"message": "already favorited", "id": existing.id}
    fav = Favorite(user_id=user_id, message_id=message_id, created_at=datetime.utcnow())
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return {"id": fav.id, "message": "favorited"}

@router.delete("/remove/{favorite_id}")
def remove_favorite(favorite_id: int, db: Session = Depends(get_db)):
    fav = db.query(Favorite).filter(Favorite.id == favorite_id).first()
    if fav:
        db.delete(fav)
        db.commit()
        return {"message": "removed"}
    return {"error": "not found"}
