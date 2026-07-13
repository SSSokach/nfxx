from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import SessionLocal
from models import User

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
@router.get("/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "avatar": u.avatar} for u in users]

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return {"id": user.id, "name": user.name, "avatar": user.avatar}
    return {"error": "User not found"}
