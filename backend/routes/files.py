from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import SessionLocal
from models import File
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{user_id}")
def get_files(user_id: int, db: Session = Depends(get_db)):
    files = db.query(File).filter(File.owner_id == user_id).all()
    return [{"id": f.id, "name": f.name, "file_type": f.file_type, "created_at": f.created_at.isoformat()} for f in files]

@router.get("/content/{file_id}")
def get_file_content(file_id: int, db: Session = Depends(get_db)):
    file = db.query(File).filter(File.id == file_id).first()
    if file:
        return {"id": file.id, "name": file.name, "content": file.content, "file_type": file.file_type}
    return {"error": "File not found"}

@router.post("/save")
def save_file(user_id: int, name: str, content: str, file_type: str = "markdown", db: Session = Depends(get_db)):
    file = File(
        name=name,
        content=content,
        file_type=file_type,
        owner_id=user_id,
        created_at=datetime.utcnow()
    )
    db.add(file)
    db.commit()
    db.refresh(file)
    return {"id": file.id, "name": file.name, "created_at": file.created_at.isoformat()}

@router.put("/update/{file_id}")
def update_file(file_id: int, content: str, db: Session = Depends(get_db)):
    file = db.query(File).filter(File.id == file_id).first()
    if file:
        file.content = content
        db.commit()
        return {"message": "File updated successfully"}
    return {"error": "File not found"}
