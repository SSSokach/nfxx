"""SQLite 数据库初始化、表结构与预置数据。"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (group_id, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_type TEXT NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT NOT NULL,
            file_name TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # 仅在 users 表为空时插入预置数据
    c.execute("SELECT COUNT(*) as cnt FROM users")
    if c.fetchone()["cnt"] == 0:
        _seed_data(c)

    conn.commit()
    conn.close()


def _seed_data(c):
    users = [
        (1, "张三", "张"),
        (2, "李四", "李"),
        (3, "王五", "王"),
        (4, "赵六", "赵"),
    ]
    c.executemany("INSERT INTO users (id, name, avatar) VALUES (?, ?, ?)", users)

    groups = [
        (1, "技术讨论组", "技"),
        (2, "项目协作组", "项"),
    ]
    c.executemany("INSERT INTO groups (id, name, avatar) VALUES (?, ?, ?)", groups)

    members = [
        (1, 1), (1, 2), (1, 3), (1, 4),  # 技术讨论组：全员
        (2, 1), (2, 2), (2, 3),           # 项目协作组：张三、李四、王五
    ]
    c.executemany("INSERT INTO group_members (group_id, user_id) VALUES (?, ?)", members)

    base = datetime(2026, 7, 11, 9, 0, 0)
    msgs = [
        # 张三 <-> 李四 私聊
        (1, "user", 2, "李四，明天的需求评审准备好了吗？", "text", "", base),
        (2, "user", 1, "基本差不多了，还有几个细节想当面确认下", "text", "", base + timedelta(minutes=5)),
        (1, "user", 2, "好的，那明天上午10点会议室见", "text", "", base + timedelta(minutes=8)),
        (2, "user", 1, "没问题，到时见", "text", "", base + timedelta(minutes=10)),

        # 张三 <-> 王五 私聊
        (1, "user", 3, "王五，那个接口文档你发我一份呗", "text", "", base + timedelta(hours=1)),
        (3, "user", 1, "我整理个 markdown 发你", "text", "", base + timedelta(hours=1, minutes=3)),
        (3, "user", 1,
         "# 用户接口文档\n\n## 1. 获取用户列表\n\n`GET /api/users`\n\n返回所有用户信息。\n\n## 2. 获取联系人\n\n`GET /api/users/{id}/contacts`\n\n返回该用户的联系人和群组。\n\n## 3. 发送消息\n\n`POST /api/messages`\n\n| 字段 | 类型 | 说明 |\n|---|---|---|\n| sender_id | int | 发送者 |\n| receiver_type | string | user/group |\n| content | string | 内容 |\n",
         "file", "用户接口文档.md", base + timedelta(hours=1, minutes=10)),

        # 技术讨论组 群聊
        (1, "group", 1, "大家好，本周技术分享定在周五下午", "text", "", base + timedelta(hours=2)),
        (2, "group", 1, "主题是什么？", "text", "", base + timedelta(hours=2, minutes=2)),
        (1, "group", 1, "AI Agent 在办公场景中的应用实践", "text", "", base + timedelta(hours=2, minutes=5)),
        (3, "group", 1, "听起来很有意思，期待", "text", "", base + timedelta(hours=2, minutes=8)),
        (4, "group", 1, "我刚好有个相关的问题想讨论", "text", "", base + timedelta(hours=2, minutes=12)),

        # 项目协作组 群聊
        (1, "group", 2, "这周迭代任务已拆分，大家看下看板", "text", "", base + timedelta(hours=3)),
        (2, "group", 2, "收到，我今天先开始前端部分", "text", "", base + timedelta(hours=3, minutes=5)),
        (3, "group", 2, "后端接口我明天能给到", "text", "", base + timedelta(hours=3, minutes=8)),
    ]
    c.executemany(
        "INSERT INTO messages (sender_id, receiver_type, receiver_id, content, msg_type, file_name, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        msgs,
    )
