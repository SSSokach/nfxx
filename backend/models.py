from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    avatar = Column(String, default="")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    avatar = Column(String, default="")
    is_group = Column(Boolean, default=False)

class UserContact(Base):
    __tablename__ = "user_contacts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    user = relationship("User", backref="user_contacts")
    contact = relationship("Contact", backref="user_contacts")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    content = Column(Text)
    message_type = Column(String, default="text")
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    reply_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sender = relationship("User", backref="messages")
    contact = relationship("Contact", backref="messages")
    file = relationship("File", backref="messages")
    reply_to = relationship("Message", remote_side=[id], backref="replies")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    content = Column(Text)
    file_type = Column(String, default="markdown")
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", backref="files")

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="favorites")
    message = relationship("Message", backref="favorites")


# ===== 智能助手扩展表 =====

class ChatSummary(Base):
    """@所有人 消息摘要表"""
    __tablename__ = "chat_summary"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_id = Column(Integer, ForeignKey("messages.id"))
    group_name = Column(String)
    content = Column(Text)
    original_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatTodoItem(Base):
    """群聊/私聊待办事项表"""
    __tablename__ = "chat_todo_item"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    source_type = Column(String, default="group")  # group / private
    group_name = Column(String, nullable=True)
    peer_name = Column(String, nullable=True)
    content = Column(Text)
    deadline = Column(Date, nullable=True)
    status = Column(String, default="pending")  # pending / completed / deleted
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EmailTodoItem(Base):
    """邮件待办事项表"""
    __tablename__ = "email_todo_item"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_id = Column(String)  # email id
    subject = Column(String)
    sender = Column(String)
    content = Column(Text)
    deadline = Column(Date, nullable=True)
    status = Column(String, default="pending")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class FileTracker(Base):
    """文件回填追踪表"""
    __tablename__ = "file_tracker"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_url = Column(String)
    file_name = Column(String)
    status = Column(String, default="tracking")  # tracking / completed / cancelled
    unfilled_users = Column(Text, default="")
    last_checked_at = Column(DateTime, nullable=True)
    check_interval_min = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailTracker(Base):
    """邮件回复追踪表"""
    __tablename__ = "email_tracker"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_id = Column(String)
    subject = Column(String)
    sent_at = Column(DateTime)
    replied_depts = Column(Text, default="")
    unreplied_depts = Column(Text, default="")
    status = Column(String, default="tracking")
    check_interval_hours = Column(Integer, default=12)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSettings(Base):
    """用户设置表"""
    __tablename__ = "user_settings"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    model_provider = Column(String, default="qwen")
    file_check_interval_min = Column(Integer, default=60)
    email_check_interval_hours = Column(Integer, default=12)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CandidateTodo(Base):
    """候选待办表 - AI自动检测出的待办事项，需用户确认"""
    __tablename__ = "candidate_todo"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    source_type = Column(String, default="group")  # group / private
    source_name = Column(String, nullable=True)
    content = Column(Text)
    deadline = Column(Date, nullable=True)
    status = Column(String, default="pending")  # pending / confirmed / dismissed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ScannedMessage(Base):
    """已扫描消息记录表 - 记录哪些消息已经被候选待办扫描处理过"""
    __tablename__ = "scanned_message"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message_id = Column(Integer, ForeignKey("messages.id"))
    scanned_at = Column(DateTime, default=datetime.utcnow)


class FileCollectionTask(Base):
    """文件收集任务表 - 发起人创建的文件收集任务"""
    __tablename__ = "file_collection_task"
    id = Column(Integer, primary_key=True, index=True)
    initiator_user_id = Column(Integer, ForeignKey("users.id"))
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    group_name = Column(String, nullable=True)
    file_name = Column(String)
    description = Column(Text, default="")
    deadline = Column(Date, nullable=True)
    status = Column(String, default="collecting")  # collecting / completed / cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("FileCollectionItem", backref="task", cascade="all, delete-orphan")


class FileCollectionItem(Base):
    """文件收集明细表 - 每个待填写人的填写状态"""
    __tablename__ = "file_collection_item"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("file_collection_task.id"))
    assignee_user_id = Column(Integer, ForeignKey("users.id"))
    assignee_name = Column(String)
    status = Column(String, default="pending")  # pending / submitted
    submitted_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Email(Base):
    """邮件表（模拟邮件系统）"""
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    sender = Column(String)
    sender_dept = Column(String)
    recipients = Column(Text)  # | separated departments
    content = Column(Text)
    is_reply = Column(Boolean, default=False)
    reply_to_email_id = Column(Integer, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
