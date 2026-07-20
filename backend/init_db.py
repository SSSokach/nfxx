from app import engine, Base, SessionLocal
from models import (
    User,
    Contact,
    UserContact,
    Message,
    File,
    Email,
    EmailTracker,
    UserSettings,
)
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

# Contacts represent conversations (chat rooms)
# For 1-on-1 chats, both participants share the SAME contact
contacts = [
    Contact(name="张三与李四", avatar="", is_group=False),   # id=1: 张三↔李四
    Contact(name="张三与王五", avatar="", is_group=False),   # id=2: 张三↔王五
    Contact(name="李四与王五", avatar="", is_group=False),   # id=3: 李四↔王五
    Contact(name="项目组", avatar="", is_group=True),         # id=4
    Contact(name="技术讨论群", avatar="", is_group=True),     # id=5
]
db.add_all(contacts)
db.commit()

# Both users link to the SAME contact for 1-on-1 conversations
user_contacts = [
    # 张三↔李四 (contact 1)
    UserContact(user_id=1, contact_id=1),
    UserContact(user_id=2, contact_id=1),
    # 张三↔王五 (contact 2)
    UserContact(user_id=1, contact_id=2),
    UserContact(user_id=3, contact_id=2),
    # 李四↔王五 (contact 3)
    UserContact(user_id=2, contact_id=3),
    UserContact(user_id=3, contact_id=3),
    # 项目组 (contact 4)
    UserContact(user_id=1, contact_id=4),
    UserContact(user_id=2, contact_id=4),
    UserContact(user_id=3, contact_id=4),
    # 技术讨论群 (contact 5)
    UserContact(user_id=1, contact_id=5),
    UserContact(user_id=2, contact_id=5),
    UserContact(user_id=3, contact_id=5),
]
db.add_all(user_contacts)
db.commit()

messages = [
    # 张三↔李四 (contact 1)
    Message(sender_id=2, contact_id=1, content="你好，最近工作怎么样？", message_type="text", created_at=datetime(2024, 1, 15, 10, 0)),
    Message(sender_id=1, contact_id=1, content="挺好的，项目进展顺利", message_type="text", created_at=datetime(2024, 1, 15, 10, 5)),
    Message(sender_id=2, contact_id=1, content="那就好，有需要帮忙的随时说", message_type="text", created_at=datetime(2024, 1, 15, 10, 6)),
    # 张三↔王五 (contact 2)
    Message(sender_id=3, contact_id=2, content="明天的会议准备得怎么样了？", message_type="text", created_at=datetime(2024, 1, 15, 11, 0)),
    Message(sender_id=1, contact_id=2, content="已经准备好了PPT", message_type="text", created_at=datetime(2024, 1, 15, 11, 10)),
    # 李四↔王五 (contact 3)
    Message(sender_id=3, contact_id=3, content="王五，上次那个bug修好了吗？", message_type="text", created_at=datetime(2024, 1, 15, 14, 0)),
    Message(sender_id=2, contact_id=3, content="已经修好了，提交了PR", message_type="text", created_at=datetime(2024, 1, 15, 14, 10)),
    # 项目组 (contact 4)
    Message(sender_id=1, contact_id=4, content="大家好，今天的周报我已经发到群里了", message_type="text", created_at=datetime(2024, 1, 15, 9, 0)),
    Message(sender_id=2, contact_id=4, content="收到，我看一下", message_type="text", created_at=datetime(2024, 1, 15, 9, 5)),
    Message(sender_id=3, contact_id=4, content="辛苦了！", message_type="text", created_at=datetime(2024, 1, 15, 9, 6)),
    # 技术讨论群 (contact 5)
    Message(sender_id=1, contact_id=5, content="有没有人知道怎么配置Nginx？", message_type="text", created_at=datetime(2024, 1, 14, 14, 0)),
    Message(sender_id=2, contact_id=5, content="我知道，需要帮忙吗？", message_type="text", created_at=datetime(2024, 1, 14, 14, 5)),
]
db.add_all(messages)
db.commit()

files = [
    File(name="项目计划.md", content="# 项目计划\n\n## 目标\n完成AI助手demo开发\n\n## 时间线\n- 第一周：完成后端API\n- 第二周：完成前端界面\n- 第三周：集成测试", file_type="markdown", owner_id=1, created_at=datetime(2024, 1, 10)),
    File(name="技术文档.md", content="# 技术文档\n\n## 技术栈\n- Vue3\n- FastAPI\n- SQLite\n\n## API设计\nRESTful风格", file_type="markdown", owner_id=1, created_at=datetime(2024, 1, 12)),
]
db.add_all(files)
db.commit()

# ===== 智能助手模拟数据 =====

now = datetime.utcnow()

# 1. 群聊中的@所有人消息（项目组，contact_id=4）
# 2. 群聊中的@张三消息（项目组，contact_id=4）
# 3. 私聊中的待办场景（张三↔李四，contact_id=1）
assistant_messages = [
    # @所有人消息
    Message(sender_id=1, contact_id=4, content="@所有人 本周五下午2点开项目评审会议，请各部门准备好汇报材料，截止日期7月18日", message_type="text", created_at=now),
    Message(sender_id=2, contact_id=4, content="@所有人 服务器将于本周六凌晨2点-4点进行维护升级，请提前保存工作", message_type="text", created_at=now),
    Message(sender_id=3, contact_id=4, content="@所有人 新版API文档已更新，请大家在本周内完成对接，截止7月20日", message_type="text", created_at=now),
    # @张三消息
    Message(sender_id=2, contact_id=4, content="@张三 周五前提交周报到我邮箱", message_type="text", created_at=now),
    Message(sender_id=3, contact_id=4, content="@张三 下周一前帮忙review一下PR #234", message_type="text", created_at=now),
    # 私聊待办场景（张三↔李四）
    Message(sender_id=2, contact_id=1, content="明天上午10点前把接口文档发给我", message_type="text", created_at=now),
    Message(sender_id=1, contact_id=1, content="好的，我整理一下", message_type="text", created_at=now),
    Message(sender_id=2, contact_id=1, content="这周五前帮忙review一下PR", message_type="text", created_at=now),
    Message(sender_id=1, contact_id=1, content="没问题", message_type="text", created_at=now),
]
db.add_all(assistant_messages)
db.commit()

# 4. 模拟邮件数据（张三 user_id=1）
email1_sent_at = datetime.utcnow()
emails = [
    # ===== 收件箱（folder=inbox）=====
    Email(user_id=1, subject="关于Q3季度考核的通知", sender="hr@company.com", sender_dept="人力资源部",
          recipients="技术部|产品部|设计部",
          content="各位同事好，Q3季度考核将于7月25日开始，请各部门负责人在7月20日前完成自评表格填写。考核标准：1. 业绩达成率 2. 团队协作 3. 创新贡献。请按时完成。",
          is_reply=False, sent_at=email1_sent_at, folder="inbox", body_type="text"),
    Email(user_id=1, subject="接口文档评审会议邀请", sender="pm@company.com", sender_dept="产品部",
          recipients="技术部",
          content="技术部同事，接口文档评审会议定于7月16日下午3点召开，请技术部提前准备好接口测试报告和性能数据，7月15日前发送到我邮箱。",
          is_reply=False, sent_at=datetime.utcnow(), folder="inbox", body_type="text"),
    Email(user_id=1, subject="关于团队建设的通知", sender="admin@company.com", sender_dept="行政部",
          recipients="技术部|产品部|设计部",
          content="本周五下午团队建设活动，请大家穿休闲装，下午2点在大厅集合。",
          is_reply=False, sent_at=datetime.utcnow(), folder="inbox", body_type="text"),
    Email(user_id=1, subject="Re: 关于Q3季度考核的通知", sender="tech@company.com", sender_dept="技术部",
          content="收到，我们会按时完成自评。",
          is_reply=True, reply_to_email_id=1, sent_at=datetime.utcnow(), folder="inbox", body_type="text"),
    Email(user_id=1, subject="Re: 关于Q3季度考核的通知", sender="design@company.com", sender_dept="设计部",
          content="设计部已收到通知，将按时提交。",
          is_reply=True, reply_to_email_id=1, sent_at=datetime.utcnow(), folder="inbox", body_type="text"),
    Email(user_id=1, subject="项目周报 - 第29周", sender="pm@company.com", sender_dept="产品部",
          recipients="技术部",
          content="# 第29周项目周报\n\n## 本周进展\n- 完成需求评审 3 项\n- 修复线上缺陷 5 个\n\n## 下周计划\n- 启动 v2.0 接口设计\n- 完成 QA 联调\n\n详见附件。",
          is_reply=False, sent_at=datetime.utcnow(), folder="inbox", body_type="markdown",
          attachment_file_ids=str(1)),  # 附加 项目计划.md
    # ===== 已发送（folder=sent）=====
    Email(user_id=1, subject="周报提交 - 张三", sender="张三 <zhangsan@company.com>", sender_dept="技术部",
          recipients="李四 <lisi@company.com>",
          content="李四你好，本周周报已整理完毕，详见附件，请查收。",
          is_reply=False, sent_at=datetime.utcnow(), folder="sent", body_type="text"),
    Email(user_id=1, subject="回复：接口文档评审", sender="张三 <zhangsan@company.com>", sender_dept="技术部",
          recipients="pm@company.com",
          content="收到，接口测试报告我会在7月15日前发到您邮箱。",
          is_reply=False, sent_at=datetime.utcnow(), folder="sent", body_type="text"),
]
db.add_all(emails)
db.commit()

# 5. 邮件回复追踪数据（email_tracker表）
email_tracker = EmailTracker(
    user_id=1,
    email_id="1",
    subject="关于Q3季度考核的通知",
    sent_at=email1_sent_at,
    replied_depts="技术部|设计部",
    unreplied_depts="产品部",
    status="tracking",
)
db.add(email_tracker)
db.commit()

# 6. 用户设置（user_settings表）
user_settings = UserSettings(
    user_id=1,
    model_provider="qwen",
    file_check_interval_min=60,
    email_check_interval_hours=12,
)
db.add(user_settings)
db.commit()

db.close()
print("Database initialized successfully")
