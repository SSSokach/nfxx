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
    form_id = Column(Integer, nullable=True)  # 关联在线表格 ID（无外键约束，便于跨表查询）
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
    source_email_id = Column(Integer, nullable=True)  # 邮件来源（无外键约束，引用 Email.id）
    source_type = Column(String, default="group")  # group / private / email
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


class ScannedEmail(Base):
    """已扫描邮件记录表 - 记录哪些邮件已经被候选待办扫描处理过"""
    __tablename__ = "scanned_email"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    email_id = Column(Integer, ForeignKey("emails.id"))
    scanned_at = Column(DateTime, default=datetime.utcnow)


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
    # 邮箱页面扩展字段
    folder = Column(String, default="inbox")  # inbox / sent / draft
    body_type = Column(String, default="text")  # text / markdown
    attachment_file_ids = Column(Text, default="")  # 逗号分隔的 File.id


class FormTracker(Base):
    """在线表格追踪表（统一追踪入口，关联 OnlineForm 或 FileCollectionTask）"""
    __tablename__ = "form_tracker"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # 追踪人（通常等于发起人）
    contact_id = Column(Integer, ForeignKey("contacts.id"))  # 所在群聊/会话
    form_name = Column(String)  # 表格名称
    form_url = Column(Text, nullable=True)  # 表格链接（可选）
    online_form_id = Column(Integer, ForeignKey("online_form.id"), nullable=True)  # 关联在线表格
    file_collection_task_id = Column(Integer, ForeignKey("file_collection_tasks.id"), nullable=True)  # 关联文件收集任务
    required_members = Column(Text)  # 需要填写的人员名单，逗号分隔
    filled_members = Column(Text, default="")  # 已填写人员，逗号分隔
    deadline = Column(Date, nullable=True)  # 截止日期
    status = Column(String, default="tracking")  # tracking / completed / cancelled
    last_checked = Column(DateTime, nullable=True)  # 上次检测时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OnlineForm(Base):
    """在线表格表 - 存储表格定义和列结构

    columns JSON 格式（增强版，支持列类型）:
    [
        {"key":"name","label":"姓名","type":"name","required":true,"editable":false},
        {"key":"col_0","label":"周报","type":"text","required":true,"editable":true},
        {"key":"col_1","label":"进度","type":"number","required":false,"editable":true},
        {"key":"col_2","label":"截止日期","type":"date","required":false,"editable":true},
        {"key":"col_3","label":"状态","type":"select","options":["进行中","已完成","延期"],"required":false,"editable":true}
    ]
    type 取值: name(姓名列,唯一,不可编辑) / text / number / date / select
    """
    __tablename__ = "online_form"
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"))  # 创建人
    contact_id = Column(Integer, ForeignKey("contacts.id"))  # 关联群聊
    title = Column(String)  # 表格标题
    columns = Column(Text)  # 列定义 JSON（见上方格式）
    required_members = Column(Text)  # 需要填写的人员名单，逗号分隔
    deadline = Column(Date, nullable=True)  # 截止日期
    status = Column(String, default="active")  # active / closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OnlineFormRow(Base):
    """在线表格行数据 - 每人一行"""
    __tablename__ = "online_form_row"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("online_form.id"))
    member_name = Column(String)  # 填写人姓名
    member_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 填写人用户ID（可空）
    data = Column(Text, default="{}")  # 行数据 JSON: {"name":"张三","col_0":"50%"}
    filled = Column(Boolean, default=False)  # 是否已填写
    filled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class TokenUsage(Base):
    """用户AI Token用量记录表"""
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)  # 日期，每天一条记录
    request_count = Column(Integer, default=0)  # 请求次数
    token_count = Column(Integer, default=0)  # token用量估算
    updated_at = Column(DateTime, default=datetime.utcnow)


class FileCollectionTask(Base):
    """文件收集任务表（群聊中发起的 Excel 文件收集）"""
    __tablename__ = "file_collection_tasks"
    id = Column(Integer, primary_key=True, index=True)
    initiator_user_id = Column(Integer, ForeignKey("users.id"))  # 发起人
    source_message_id = Column(Integer, ForeignKey("messages.id"))  # 触发消息
    group_name = Column(String(100))  # 群聊名称
    file_name = Column(String(200))  # 要收集的文件名
    description = Column(Text)  # 任务描述
    deadline = Column(Date, nullable=True)  # 截止日期
    status = Column(String(20), default="collecting")  # collecting / completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class FileCollectionItem(Base):
    """文件收集明细表（每个待填写人一条记录）"""
    __tablename__ = "file_collection_items"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("file_collection_tasks.id"))  # 所属任务
    assignee_user_id = Column(Integer, ForeignKey("users.id"))  # 待填写人
    assignee_name = Column(String(50))  # 待填写人姓名
    status = Column(String(20), default="pending")  # pending / submitted
    submitted_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)  # 提交的文件
    submitted_at = Column(DateTime, nullable=True)  # 提交时间
    created_at = Column(DateTime, default=datetime.utcnow)
