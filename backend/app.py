"""FastAPI 应用：API 路由 + 静态文件服务。"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import database
import ai

app = FastAPI(title="AI 办公助手 Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 数据模型 ----------

class MessageCreate(BaseModel):
    sender_id: int
    receiver_type: str  # 'user' | 'group'
    receiver_id: int
    content: str
    msg_type: str = "text"
    file_name: str = ""


class FileUpdate(BaseModel):
    content: str


class AIChatRequest(BaseModel):
    user_id: int
    message: str
    history: Optional[list] = None


# ---------- 用户与联系人 ----------

@app.get("/api/users")
def get_users():
    conn = database.get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/users/{user_id}/contacts")
def get_contacts(user_id: int):
    conn = database.get_conn()
    c = conn.cursor()

    users = c.execute(
        "SELECT id, name, avatar FROM users WHERE id != ? ORDER BY id", (user_id,)
    ).fetchall()

    groups = c.execute(
        "SELECT g.id, g.name, g.avatar FROM groups g "
        "JOIN group_members gm ON g.id = gm.group_id "
        "WHERE gm.user_id = ? ORDER BY g.id",
        (user_id,),
    ).fetchall()

    conn.close()
    return {
        "users": [dict(r) for r in users],
        "groups": [dict(r) for r in groups],
    }


# ---------- 消息 ----------

@app.get("/api/messages")
def get_messages(user_id: int, peer_type: str, peer_id: int):
    conn = database.get_conn()
    c = conn.cursor()

    if peer_type == "user":
        rows = c.execute(
            "SELECT m.*, s.name as sender_name FROM messages m "
            "JOIN users s ON m.sender_id = s.id "
            "WHERE (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?) "
            "OR (m.sender_id = ? AND m.receiver_type = 'user' AND m.receiver_id = ?) "
            "ORDER BY m.created_at ASC",
            (user_id, peer_id, peer_id, user_id),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT m.*, s.name as sender_name FROM messages m "
            "JOIN users s ON m.sender_id = s.id "
            "WHERE m.receiver_type = 'group' AND m.receiver_id = ? "
            "ORDER BY m.created_at ASC",
            (peer_id,),
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/messages")
def send_message(msg: MessageCreate):
    conn = database.get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO messages (sender_id, receiver_type, receiver_id, content, msg_type, file_name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (msg.sender_id, msg.receiver_type, msg.receiver_id, msg.content, msg.msg_type, msg.file_name, now),
    )
    msg_id = c.lastrowid
    conn.commit()
    row = c.execute(
        "SELECT m.*, s.name as sender_name FROM messages m "
        "JOIN users s ON m.sender_id = s.id WHERE m.id = ?",
        (msg_id,),
    ).fetchone()
    conn.close()
    return dict(row)


# ---------- 文件 ----------

@app.get("/api/files/{message_id}")
def get_file(message_id: int):
    conn = database.get_conn()
    row = conn.execute(
        "SELECT id, file_name, content, created_at FROM messages WHERE id = ? AND msg_type = 'file'",
        (message_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="文件不存在")
    return dict(row)


@app.put("/api/files/{message_id}")
def update_file(message_id: int, body: FileUpdate):
    conn = database.get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT id FROM messages WHERE id = ? AND msg_type = 'file'", (message_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="文件不存在")
    c.execute("UPDATE messages SET content = ? WHERE id = ?", (body.content, message_id))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------- AI 助手 ----------

@app.post("/api/ai/chat")
def ai_chat(req: AIChatRequest):
    conn = database.get_conn()
    user = conn.execute("SELECT name FROM users WHERE id = ?", (req.user_id,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    result = ai.chat_with_ai(req.user_id, user["name"], req.message, req.history)
    return result


# ---------- 静态文件服务（部署模式） ----------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


@app.on_event("startup")
def startup():
    database.init_db()
