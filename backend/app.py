from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

SQLALCHEMY_DATABASE_URL = "sqlite:///./chat_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="AI Office Assistant Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import users, chats, files, ai, favorites, todos, emails, reports, forms, online_forms
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(todos.router, prefix="/api/todos", tags=["todos"])
app.include_router(emails.router, prefix="/api/emails", tags=["emails"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(forms.router, prefix="/api/forms", tags=["forms"])
app.include_router(online_forms.router, prefix="/api/online-forms", tags=["online-forms"])

# 自动创建缺失的表（不会影响已有表）
import models
models.Base.metadata.create_all(bind=engine)

# ===== 轻量级数据库迁移：为已存在的表补充新增列 =====
def _run_lightweight_migration():
    """对已存在的表执行 ALTER TABLE ADD COLUMN，补齐新增字段。
    SQLite 支持 ADD COLUMN，但不支持 IF NOT EXISTS，故先检查列是否存在。
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    migrations = [
        # (table, column, column_ddl)
        ("emails", "folder", "folder VARCHAR DEFAULT 'inbox'"),
        ("emails", "body_type", "body_type VARCHAR DEFAULT 'text'"),
        ("emails", "attachment_file_ids", "attachment_file_ids TEXT DEFAULT ''"),
        ("candidate_todo", "source_email_id", "source_email_id INTEGER"),
    ]
    with engine.begin() as conn:
        for table, column, ddl in migrations:
            if not insp.has_table(table):
                continue
            existing_cols = {c["name"] for c in insp.get_columns(table)}
            if column not in existing_cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

try:
    _run_lightweight_migration()
except Exception as _e:
    # 迁移失败不阻塞启动，已存在的列会抛错被忽略
    print(f"[migration] skipped: {_e}")

frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")

@app.get("/api")
def read_root():
    return {"message": "AI Office Assistant API"}
