from fastapi import APIRouter, Depends, UploadFile, File as FastAPIFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app import SessionLocal
from models import File
from datetime import datetime
import os
import io

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

@router.post("/upload/{user_id}")
async def upload_file(user_id: int, file: UploadFile = FastAPIFile(...), db: Session = Depends(get_db)):
    """上传本地文件，保存内容到数据库，同时保存物理文件到uploads目录。"""
    content = await file.read()
    text_content = ""
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        text_content = f"[二进制文件，大小: {len(content)} 字节]"

    # Determine file type
    filename = file.filename or "unnamed"
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext in ("md", "markdown"):
        file_type = "markdown"
    elif ext in ("txt",):
        file_type = "text"
    elif ext in ("json",):
        file_type = "json"
    elif ext in ("py", "js", "ts", "java", "go", "rs", "c", "cpp", "html", "css", "vue"):
        file_type = "code"
    else:
        file_type = ext or "file"

    # Save to database
    file_obj = File(
        name=filename,
        content=text_content,
        file_type=file_type,
        owner_id=user_id,
        created_at=datetime.utcnow()
    )
    db.add(file_obj)
    db.commit()
    db.refresh(file_obj)

    # Save physical file
    phys_path = os.path.join(UPLOAD_DIR, f"{file_obj.id}_{filename}")
    with open(phys_path, "wb") as f:
        f.write(content)

    return {
        "id": file_obj.id,
        "name": file_obj.name,
        "file_type": file_obj.file_type,
        "size": len(content),
        "created_at": file_obj.created_at.isoformat()
    }

@router.get("/download/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db)):
    """下载文件，优先返回物理文件，没有则用数据库内容生成。"""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return {"error": "File not found"}

    phys_path = os.path.join(UPLOAD_DIR, f"{file.id}_{file.name}")
    if os.path.exists(phys_path):
        with open(phys_path, "rb") as f:
            content = f.read()
    else:
        content = file.content.encode("utf-8")

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{file.name}"}
    )

@router.delete("/delete/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    """删除文件。"""
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return {"error": "File not found"}

    # Delete physical file if exists
    phys_path = os.path.join(UPLOAD_DIR, f"{file.id}_{file.name}")
    if os.path.exists(phys_path):
        os.remove(phys_path)

    db.delete(file)
    db.commit()
    return {"message": "File deleted successfully"}
