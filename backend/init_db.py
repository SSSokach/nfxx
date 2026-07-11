from app import engine, Base, SessionLocal
from models import User, Contact, UserContact, Message, File
from datetime import datetime

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

users = [
    User(name="张三", avatar=""),
    User(name="李四", avatar=""),
    User(name="王五", avatar=""),
]
db.add_all(users)
db.commit()

contacts = [
    Contact(name="张三", avatar="", is_group=False),
    Contact(name="李四", avatar="", is_group=False),
    Contact(name="王五", avatar="", is_group=False),
    Contact(name="项目组", avatar="", is_group=True),
    Contact(name="技术讨论群", avatar="", is_group=True),
]
db.add_all(contacts)
db.commit()

user_contacts = [
    UserContact(user_id=1, contact_id=2),
    UserContact(user_id=1, contact_id=3),
    UserContact(user_id=1, contact_id=4),
    UserContact(user_id=1, contact_id=5),
    UserContact(user_id=2, contact_id=1),
    UserContact(user_id=2, contact_id=3),
    UserContact(user_id=2, contact_id=4),
    UserContact(user_id=3, contact_id=1),
    UserContact(user_id=3, contact_id=2),
    UserContact(user_id=3, contact_id=4),
    UserContact(user_id=3, contact_id=5),
]
db.add_all(user_contacts)
db.commit()

messages = [
    Message(sender_id=2, contact_id=1, content="你好，最近工作怎么样？", message_type="text", created_at=datetime(2024, 1, 15, 10, 0)),
    Message(sender_id=1, contact_id=1, content="挺好的，项目进展顺利", message_type="text", created_at=datetime(2024, 1, 15, 10, 5)),
    Message(sender_id=2, contact_id=1, content="那就好，有需要帮忙的随时说", message_type="text", created_at=datetime(2024, 1, 15, 10, 6)),
    Message(sender_id=3, contact_id=2, content="明天的会议准备得怎么样了？", message_type="text", created_at=datetime(2024, 1, 15, 11, 0)),
    Message(sender_id=1, contact_id=2, content="已经准备好了PPT", message_type="text", created_at=datetime(2024, 1, 15, 11, 10)),
    Message(sender_id=1, contact_id=3, content="大家好，今天的周报我已经发到群里了", message_type="text", created_at=datetime(2024, 1, 15, 9, 0)),
    Message(sender_id=2, contact_id=3, content="收到，我看一下", message_type="text", created_at=datetime(2024, 1, 15, 9, 5)),
    Message(sender_id=3, contact_id=3, content="辛苦了！", message_type="text", created_at=datetime(2024, 1, 15, 9, 6)),
    Message(sender_id=1, contact_id=4, content="有没有人知道怎么配置Nginx？", message_type="text", created_at=datetime(2024, 1, 14, 14, 0)),
    Message(sender_id=2, contact_id=4, content="我知道，需要帮忙吗？", message_type="text", created_at=datetime(2024, 1, 14, 14, 5)),
]
db.add_all(messages)
db.commit()

files = [
    File(name="项目计划.md", content="# 项目计划\n\n## 目标\n完成AI助手demo开发\n\n## 时间线\n- 第一周：完成后端API\n- 第二周：完成前端界面\n- 第三周：集成测试", file_type="markdown", owner_id=1, created_at=datetime(2024, 1, 10)),
    File(name="技术文档.md", content="# 技术文档\n\n## 技术栈\n- Vue3\n- FastAPI\n- SQLite\n\n## API设计\nRESTful风格", file_type="markdown", owner_id=1, created_at=datetime(2024, 1, 12)),
]
db.add_all(files)
db.commit()

db.close()
print("Database initialized successfully")
