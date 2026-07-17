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

frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")

@app.get("/api")
def read_root():
    return {"message": "AI Office Assistant API"}
