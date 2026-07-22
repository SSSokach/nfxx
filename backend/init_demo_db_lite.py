"""
AI办公助手 - 精简版演示数据
只保留能证明系统功能的最小数据集
覆盖功能：IM通讯、文件预览、Excel编辑、文件收集、候选待办、待办进度、
        AI对话、智能回复、在线表格、表格追踪、AI总结、催办、邮件追踪
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta, date
from app import engine, Base, SessionLocal
from models import (
    User, Contact, UserContact, Message, File, Favorite,
    ChatSummary, ChatTodoItem, Email, EmailTodoItem, EmailTracker,
    UserSettings, CandidateTodo, ScannedMessage,
    FileCollectionTask, FileCollectionItem, FileTracker,
    FormTracker, OnlineForm, OnlineFormRow, TokenUsage,
)
import openpyxl

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()
now = datetime.utcnow()
today = date.today()

# ============================================================
# 1. 用户（5人，覆盖3个部门）
# ============================================================
users_data = [
    ("张三", 1, "技术部"),   # 主视角用户
    ("李四", 2, "技术部"),
    ("王五", 3, "产品部"),
    ("赵六", 4, "设计部"),
    ("郑十", 5, "技术部"),
]
users = [User(id=uid, name=name, avatar="") for name, uid, _ in users_data]
db.add_all(users)
db.commit()
U = {u.name: u.id for u in users}
print(f"[OK] 用户: {len(users)}人")

# ============================================================
# 2. 联系人（2群聊 + 2私聊）
# ============================================================
contacts = [
    Contact(name="全员周报群", avatar="", is_group=True),
    Contact(name="项目组", avatar="", is_group=True),
    Contact(name="张三与李四", avatar="", is_group=False),
    Contact(name="张三与王五", avatar="", is_group=False),
]
db.add_all(contacts)
db.commit()
C = {c.name: c.id for c in contacts}

# ============================================================
# 3. 用户-联系人关联
# ============================================================
ucs = []
for gc in [c for c in contacts if c.is_group]:
    for u in users:
        ucs.append(UserContact(user_id=u.id, contact_id=gc.id))
ucs.append(UserContact(user_id=U["张三"], contact_id=C["张三与李四"]))
ucs.append(UserContact(user_id=U["李四"], contact_id=C["张三与李四"]))
ucs.append(UserContact(user_id=U["张三"], contact_id=C["张三与王五"]))
ucs.append(UserContact(user_id=U["王五"], contact_id=C["张三与王五"]))
db.add_all(ucs)
db.commit()
print(f"[OK] 联系人: {len(contacts)}个, 关联: {len(ucs)}条")

# ============================================================
# 4. 消息（丰富场景：周报通知、讨论、催办、项目协作、私聊）
# ============================================================
msgs = []
gid = C["全员周报群"]

# === 全员周报群 ===
msgs += [
    Message(sender_id=U["张三"], contact_id=gid, content="各位同事好，本周周报请大家在Excel模板中填写，周五下班前提交", created_at=now - timedelta(hours=72)),
    Message(sender_id=U["李四"], contact_id=gid, content="收到，会尽快填写", created_at=now - timedelta(hours=70)),
    Message(sender_id=U["王五"], contact_id=gid, content="请问模板在哪里下载？", created_at=now - timedelta(hours=68)),
    Message(sender_id=U["张三"], contact_id=gid, content="模板就是群里发的那个Excel文件，直接在上面填写就行", created_at=now - timedelta(hours=67)),
    Message(sender_id=U["赵六"], contact_id=gid, content="设计部的汇报PPT也需要提交吗？", created_at=now - timedelta(hours=48)),
    Message(sender_id=U["张三"], contact_id=gid, content="@赵六 设计部先填周报表格就行，PPT下周再准备", created_at=now - timedelta(hours=47)),
]
# @所有人消息
msg_at_all = Message(sender_id=U["张三"], contact_id=gid,
    content="@所有人 本周五下午2点开项目评审会议，请各部门准备好汇报材料，截止日期7月25日",
    created_at=now - timedelta(hours=24))
msgs.append(msg_at_all)
# @张三消息
msg_at_zhangsan = Message(sender_id=U["李四"], contact_id=gid,
    content="@张三 周五前提交周报到我邮箱",
    created_at=now - timedelta(hours=20))
msgs.append(msg_at_zhangsan)
# 催办消息
msg_remind1 = Message(sender_id=U["张三"], contact_id=gid,
    content="@赵六 @郑十 请尽快填写表格《7月工作汇报》，截止日期：" + (today + timedelta(days=5)).isoformat(),
    created_at=now - timedelta(hours=6))
msgs.append(msg_remind1)
msg_remind2 = Message(sender_id=U["张三"], contact_id=gid,
    content="@赵六 @郑十 请尽快填写表格《测试文件260720》，截止日期：" + (today + timedelta(days=10)).isoformat(),
    created_at=now - timedelta(hours=2))
msgs.append(msg_remind2)

# === 项目组 ===
msgs += [
    Message(sender_id=U["张三"], contact_id=C["项目组"], content="新版API接口已部署到测试环境，大家开始联调", created_at=now - timedelta(hours=30)),
    Message(sender_id=U["李四"], contact_id=C["项目组"], content="好的，我这边前端已经准备好了", created_at=now - timedelta(hours=29)),
    Message(sender_id=U["王五"], contact_id=C["项目组"], content="产品需求文档已更新到最新版本，请开发同学查阅", created_at=now - timedelta(hours=28)),
    Message(sender_id=U["郑十"], contact_id=C["项目组"], content="接口联调遇到个问题，登录接口返回500，帮忙看下", created_at=now - timedelta(hours=20)),
    Message(sender_id=U["张三"], contact_id=C["项目组"], content="@郑十 我查了一下，是数据库连接池配置的问题，已经修复了", created_at=now - timedelta(hours=18)),
    Message(sender_id=U["郑十"], contact_id=C["项目组"], content="好的，我再试试", created_at=now - timedelta(hours=17)),
    Message(sender_id=U["李四"], contact_id=C["项目组"], content="前端联调基本通过，还有几个小问题我整理一下", created_at=now - timedelta(hours=10)),
]

# === 私聊 ===
msgs += [
    Message(sender_id=U["李四"], contact_id=C["张三与李四"], content="明天上午10点前把接口文档发给我", created_at=now - timedelta(hours=25)),
    Message(sender_id=U["张三"], contact_id=C["张三与李四"], content="好的，我整理一下", created_at=now - timedelta(hours=24)),
    Message(sender_id=U["李四"], contact_id=C["张三与李四"], content="接口文档收到了，谢谢", created_at=now - timedelta(hours=18)),
    Message(sender_id=U["王五"], contact_id=C["张三与王五"], content="需求评审会改到周四下午3点了", created_at=now - timedelta(hours=15)),
    Message(sender_id=U["张三"], contact_id=C["张三与王五"], content="收到，我把日历更新一下", created_at=now - timedelta(hours=14)),
]

db.add_all(msgs)
db.commit()
print(f"[OK] 消息: {len(msgs)}条")

# ============================================================
# 5. 文件（1个Markdown + 1个Excel）
# ============================================================
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

md_file = File(
    name="项目计划.md",
    content="# 项目计划\n\n## 目标\n完成AI助手demo开发\n\n## 时间线\n- 第一周：完成后端API\n- 第二周：完成前端界面\n- 第三周：集成测试\n\n## 里程碑\n- [x] 需求确认\n- [x] 技术方案设计\n- [ ] 后端开发\n- [ ] 前端开发\n\n## 风险\n- 接口联调可能延期\n- 人员不足",
    file_type="markdown", owner_id=U["张三"], created_at=now - timedelta(days=5),
)
db.add(md_file)
db.commit()

# Excel文件（周报填写模板）—— 5人，3人已填，2人未填
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "周报"
ws.append(["姓名", "部门", "本周工作内容", "完成情况", "下周计划"])
for col in range(1, 6):
    ws.cell(row=1, column=col).font = openpyxl.styles.Font(bold=True)

excel_filled = ["张三", "李四", "王五"]
excel_unfilled = ["赵六", "郑十"]
excel_data = {
    "张三": ("张三", "技术部", "完成AI对话模块开发", "已完成", "集成测试"),
    "李四": ("李四", "技术部", "前端界面开发", "已完成", "联调测试"),
    "王五": ("王五", "产品部", "需求文档编写", "已完成", "用户调研"),
    "赵六": ("赵六", "设计部", "", "", ""),
    "郑十": ("郑十", "技术部", "", "", ""),
}
for name in ["张三", "李四", "王五", "赵六", "郑十"]:
    ws.append(list(excel_data[name]))

excel_filename = "周报填写模板.xlsx"
excel_path = os.path.join(UPLOADS_DIR, excel_filename)
wb.save(excel_path)

excel_file = File(name=excel_filename, content="", file_type="xlsx", owner_id=U["张三"], created_at=now - timedelta(hours=72))
db.add(excel_file)
db.commit()

file_msg = Message(sender_id=U["张三"], contact_id=gid,
                   content="周报填写模板.xlsx", message_type="file", file_id=excel_file.id,
                   created_at=now - timedelta(hours=72))
db.add(file_msg)
db.commit()
print(f"[OK] 文件: 2个 (1 Markdown + 1 Excel)")

# ============================================================
# 6. 文件收集任务（与Excel一致：3/5已填）
# ============================================================
fct = FileCollectionTask(
    initiator_user_id=U["张三"],
    source_message_id=file_msg.id,
    group_name="全员周报群",
    file_name=excel_filename,
    description="请大家填写本周周报，周五下班前提交",
    deadline=date.today() + timedelta(days=5),
    status="collecting",
    created_at=now - timedelta(hours=72),
    updated_at=now - timedelta(hours=2),
)
db.add(fct)
db.commit()

for name in ["张三", "李四", "王五", "赵六", "郑十"]:
    is_filled = name in excel_filled
    db.add(FileCollectionItem(
        task_id=fct.id, assignee_user_id=U[name], assignee_name=name,
        status="submitted" if is_filled else "pending",
        submitted_at=now - timedelta(hours=24) if is_filled else None,
        created_at=now - timedelta(hours=72),
    ))
db.commit()
print(f"[OK] 文件收集: {len(excel_filled)}/5已提交")

# ============================================================
# 7. 待办（覆盖 pending/completed/overdue + 填写表格待办）
# ============================================================
todos = [
    # 文件收集进度待办
    ChatTodoItem(user_id=U["张三"], source_id=file_msg.id, source_type="group", group_name="全员周报群",
                 content=f"[文件收集] {excel_filename} - 等待2人提交（3/5）",
                 deadline=date.today() + timedelta(days=5), status="pending", created_at=now - timedelta(hours=72)),
    # 项目评审会议（pending）
    ChatTodoItem(user_id=U["张三"], source_id=msg_at_all.id, source_type="group", group_name="全员周报群",
                 content="参加周五下午2点的项目评审会议", deadline=today + timedelta(days=2), status="pending", created_at=now - timedelta(hours=24)),
    # 提交周报到邮箱（pending）
    ChatTodoItem(user_id=U["张三"], source_id=msg_at_zhangsan.id, source_type="group", group_name="全员周报群",
                 content="周五前提交周报到李四邮箱", deadline=today + timedelta(days=2), status="pending", created_at=now - timedelta(hours=20)),
    # 已完成：发送接口文档
    ChatTodoItem(user_id=U["张三"], source_id=None, source_type="private", peer_name="李四",
                 content="发送接口文档给李四", status="completed",
                 completed_at=now - timedelta(hours=18), created_at=now - timedelta(hours=25)),
    # 已逾期：需求评审准备
    ChatTodoItem(user_id=U["张三"], source_id=None, source_type="private", peer_name="王五",
                 content="准备需求评审材料", deadline=today - timedelta(days=1), status="pending",
                 created_at=now - timedelta(hours=48)),
    # 郑十的填写待办（pending，带form_id）
    ChatTodoItem(user_id=U["郑十"], source_id=file_msg.id, source_type="group", group_name="全员周报群",
                 content=f"[填写文件] {excel_filename} - 由 张三 发起",
                 deadline=date.today() + timedelta(days=5), status="pending", created_at=now - timedelta(hours=72)),
]
db.add_all(todos)
db.commit()
print(f"[OK] 待办: {len(todos)}条 (含1条逾期)")

# ============================================================
# 8. 候选待办（2条：1 pending + 1 dismissed）
# ============================================================
candidates = [
    CandidateTodo(user_id=U["张三"], source_message_id=msg_at_zhangsan.id, source_type="group", source_name="全员周报群",
                 content="周五前提交周报到李四邮箱", deadline=today + timedelta(days=2), status="pending", created_at=now - timedelta(hours=20)),
    CandidateTodo(user_id=U["张三"], source_message_id=None, source_type="group", source_name="项目组",
                 content="确认联调测试完成情况", status="dismissed", created_at=now - timedelta(hours=28)),
]
db.add_all(candidates)
db.commit()
print(f"[OK] 候选待办: {len(candidates)}条")

# ============================================================
# 9. @所有人摘要（1条）
# ============================================================
db.add(ChatSummary(
    user_id=U["张三"], source_id=msg_at_all.id, group_name="全员周报群",
    content="张三发起：本周五下午2点开项目评审会议，请各部门准备汇报材料，截止7月25日",
    original_message=msg_at_all.content, created_at=now - timedelta(hours=24),
))
db.commit()
print(f"[OK] 摘要: 1条")

# ============================================================
# 10. 已扫描消息
# ============================================================
for m in msgs[-8:]:
    db.add(ScannedMessage(user_id=U["张三"], message_id=m.id, scanned_at=now))
db.commit()
print(f"[OK] 已扫描: 8条")

# ============================================================
# 11. 邮件（3封：通知+回复+催办）+ 邮件待办 + 邮件追踪
# ============================================================
email1 = Email(user_id=U["张三"], subject="关于Q3季度考核的通知", sender="hr@company.com", sender_dept="人力资源部",
               recipients="技术部|产品部|设计部",
               content="各位同事好，Q3季度考核将于7月25日开始，请各部门负责人在7月20日前完成自评表格填写。",
               is_reply=False, sent_at=now - timedelta(days=3))
db.add(email1); db.commit()
email2 = Email(user_id=U["张三"], subject="Re: 关于Q3季度考核的通知", sender="tech@company.com", sender_dept="技术部",
               content="收到，我们会按时完成自评。", is_reply=True, reply_to_email_id=email1.id, sent_at=now - timedelta(days=2))
db.add(email2); db.commit()
email3 = Email(user_id=U["张三"], subject="提醒：Q3自评表格提交截止7月20日", sender="hr@company.com", sender_dept="人力资源部",
               content="提醒各位，Q3自评表格提交截止日期为7月20日，尚未提交的同事请尽快完成。",
               is_reply=False, sent_at=now - timedelta(days=1))
db.add(email3); db.commit()
print(f"[OK] 邮件: 3封 (含回复+催办提醒)")

# 邮件待办
db.add(EmailTodoItem(user_id=U["张三"], source_id=str(email1.id), subject="关于Q3季度考核的通知",
                    sender="hr@company.com", content="完成Q3自评表格填写，7月20日前提交",
                    deadline=today + timedelta(days=3), status="pending", created_at=now - timedelta(days=3)))
db.commit()
print(f"[OK] 邮件待办: 1条")

# 邮件追踪（技术部已回复，产品部/设计部未回复）
db.add(EmailTracker(user_id=U["张三"], email_id=str(email1.id), subject="关于Q3季度考核的通知",
                    sent_at=email1.sent_at, replied_depts="技术部", unreplied_depts="产品部|设计部",
                    status="tracking", last_checked_at=now - timedelta(hours=12)))
db.commit()
print(f"[OK] 邮件追踪: 1条")

# ---- 张三发送的多收件人邮件 + 人名级追踪 ----
email_sent = Email(
    user_id=U["张三"], subject="关于下周一项目评审会议的通知",
    sender="张三 <zhangsan@company.com>", sender_dept="技术部",
    recipients="李四 <lisi@company.com>, 王五 <wangwu@company.com>, 赵六 <zhaoliu@company.com>",
    content="各位好，下周一上午10点开项目评审会议，请各自准备汇报材料，收到请回复确认。",
    is_reply=False, sent_at=now - timedelta(days=2),
    folder="sent", body_type="markdown",
)
db.add(email_sent); db.commit()

# 给各收件人创建 inbox 副本
for name in ["李四", "王五", "赵六"]:
    db.add(Email(
        user_id=U[name], subject="关于下周一项目评审会议的通知",
        sender="张三 <zhangsan@company.com>", sender_dept="技术部",
        recipients="李四 <lisi@company.com>, 王五 <wangwu@company.com>, 赵六 <zhaoliu@company.com>",
        content="各位好，下周一上午10点开项目评审会议，请各自准备汇报材料，收到请回复确认。",
        is_reply=False, sent_at=now - timedelta(days=2),
        folder="inbox", body_type="markdown",
    ))
db.commit()

# 李四回复了
email_reply = Email(
    user_id=U["张三"], subject="Re: 关于下周一项目评审会议的通知",
    sender="李四 <lisi@company.com>", sender_dept="技术部",
    recipients="张三 <zhangsan@company.com>",
    content="收到，我会准备前端部分的汇报材料。",
    is_reply=True, reply_to_email_id=email_sent.id, sent_at=now - timedelta(days=1),
    folder="inbox", body_type="text",
)
db.add(email_reply); db.commit()
print(f"[OK] 邮件(新增): 1封发送+1封回复, 追踪3人回复(1已回/2未回)")

# 人名级邮件追踪
db.add(EmailTracker(
    user_id=U["张三"], email_id=str(email_sent.id),
    subject="关于下周一项目评审会议的通知",
    sent_at=email_sent.sent_at,
    replied_depts="李四",
    unreplied_depts="王五|赵六",
    status="tracking",
    last_checked_at=now - timedelta(hours=6),
    created_at=now - timedelta(days=2),
))
db.commit()

# ============================================================
# 12. 在线表单 — 两个表格，覆盖不同场景
# ============================================================

# ---- 表单1: 7月工作汇报（3/5全部完成 + 2/5完全未填）----
form1 = OnlineForm(
    creator_id=U["张三"], contact_id=C["全员周报群"],
    title="7月工作汇报",
    columns='[{"key":"name","label":"姓名","type":"name","required":true,"editable":false},'
            '{"key":"weekly_work","label":"本周工作内容","type":"text","required":true,"editable":true},'
            '{"key":"progress","label":"完成进度","type":"text","required":false,"editable":true},'
            '{"key":"plan","label":"下周计划","type":"text","required":false,"editable":true}]',
    required_members="张三,李四,王五,赵六,郑十",
    deadline=date.today() + timedelta(days=5),
    status="active", created_at=now - timedelta(hours=72),
)
db.add(form1)
db.commit()

form1_filled = ["张三", "李四", "王五"]
form1_data = {
    "张三": '{"name":"张三","weekly_work":"完成AI对话模块开发","progress":"100%","plan":"集成测试"}',
    "李四": '{"name":"李四","weekly_work":"前端界面开发","progress":"95%","plan":"联调测试"}',
    "王五": '{"name":"王五","weekly_work":"需求文档编写","progress":"100%","plan":"用户调研"}',
    "赵六": '{"name":"赵六"}',
    "郑十": '{"name":"郑十"}',
}
for name in ["张三", "李四", "王五", "赵六", "郑十"]:
    is_filled = name in form1_filled
    db.add(OnlineFormRow(
        form_id=form1.id, member_name=name,
        data=form1_data.get(name, '{"name":"' + name + '"}'), filled=is_filled,
        filled_at=now - timedelta(hours=24) if is_filled else None,
        created_at=now - timedelta(hours=72),
    ))
db.commit()

# 表单1追踪
db.add(FormTracker(
    user_id=U["张三"], contact_id=C["全员周报群"],
    form_name="7月工作汇报", form_url=f"online-forms/{form1.id}",
    online_form_id=form1.id,
    required_members="张三,李四,王五,赵六,郑十",
    filled_members=",".join(form1_filled),
    deadline=date.today() + timedelta(days=5),
    status="tracking", last_checked=now - timedelta(hours=2),
    created_at=now - timedelta(hours=72), updated_at=now - timedelta(hours=2),
))
db.commit()

# 为未填写人创建填写待办
for name in ["赵六", "郑十"]:
    db.add(ChatTodoItem(
        user_id=U[name], source_type="group", group_name="7月工作汇报",
        content=f"[填写表格] 7月工作汇报 - 由 张三 发起",
        form_id=form1.id,
        deadline=date.today() + timedelta(days=5),
        status="pending", created_at=now - timedelta(hours=72),
    ))
db.commit()
print(f"[OK] 在线表单1: 7月工作汇报 ({len(form1_filled)}/5全部完成)")

# ---- 表单2: 测试文件260720（1/5完成 + 1/5部分填写 + 3/5完全未填）----
# 这个表单专门展示"部分填写"场景：赵六只填了"部门"列，郑十填了2列但缺2列
form2 = OnlineForm(
    creator_id=U["张三"], contact_id=C["全员周报群"],
    title="测试文件260720",
    columns='[{"key":"name","label":"姓名","type":"name","required":true,"editable":false},'
            '{"key":"dept","label":"部门","type":"text","required":true,"editable":true},'
            '{"key":"weekly_work","label":"本周工作内容","type":"text","required":true,"editable":true},'
            '{"key":"status","label":"完成情况","type":"text","required":false,"editable":true},'
            '{"key":"plan","label":"下周计划","type":"text","required":false,"editable":true}]',
    required_members="张三,李四,王五,赵六,郑十",
    deadline=date.today() + timedelta(days=10),
    status="active", created_at=now - timedelta(hours=48),
)
db.add(form2)
db.commit()

# 数据说明：
# 张三：全部5列都填了 → ✅ 完成
# 李四：只填了部门和本周工作内容 → ⏳ 部分填写（已填2/4，未填2列）
# 王五：完全未填 → ❌ 未填
# 赵六：只填了部门 → ⏳ 部分填写（已填1/4，未填3列）
# 郑十：填了部门+本周工作内容+完成情况 → ⏳ 部分填写（已填3/4，未填1列）
form2_data = {
    "张三": '{"name":"张三","dept":"技术部","weekly_work":"完成AI对话模块开发","status":"已完成","plan":"集成测试"}',
    "李四": '{"name":"李四","dept":"技术部","weekly_work":"前端界面开发","status":"","plan":""}',
    "王五": '{"name":"王五"}',
    "赵六": '{"name":"赵六","dept":"设计部","weekly_work":"","status":"","plan":""}',
    "郑十": '{"name":"郑十","dept":"技术部","weekly_work":"接口联调测试","status":"进行中","plan":""}',
}
for name in ["张三", "李四", "王五", "赵六", "郑十"]:
    db.add(OnlineFormRow(
        form_id=form2.id, member_name=name,
        data=form2_data[name], filled=True,  # filled=True 但实际列不一定全填——模拟真实场景
        filled_at=now - timedelta(hours=12),
        created_at=now - timedelta(hours=48),
    ))
db.commit()

# 表单2追踪
db.add(FormTracker(
    user_id=U["张三"], contact_id=C["全员周报群"],
    form_name="测试文件260720", form_url=f"online-forms/{form2.id}",
    online_form_id=form2.id,
    required_members="张三,李四,王五,赵六,郑十",
    filled_members="张三,李四,赵六,郑十",  # 按旧逻辑标记4人已填，但实际只有张三全部完成
    deadline=date.today() + timedelta(days=10),
    status="tracking", last_checked=now - timedelta(hours=2),
    created_at=now - timedelta(hours=48), updated_at=now - timedelta(hours=2),
))
db.commit()

# 为未填写人创建填写待办
for name in ["王五"]:
    db.add(ChatTodoItem(
        user_id=U[name], source_type="group", group_name="测试文件260720",
        content=f"[填写表格] 测试文件260720 - 由 张三 发起",
        form_id=form2.id,
        deadline=date.today() + timedelta(days=10),
        status="pending", created_at=now - timedelta(hours=48),
    ))
db.commit()
print(f"[OK] 在线表单2: 测试文件260720 (1/5全部完成, 3/5部分填写, 1/5未填)")

# ============================================================
# 13. 文件追踪
# ============================================================
db.add(FileTracker(
    user_id=U["张三"], file_url="", file_name=excel_filename,
    status="tracking", unfilled_users=",".join(excel_unfilled),
    last_checked_at=now - timedelta(hours=2), check_interval_min=60,
    created_at=now - timedelta(hours=72),
))
db.commit()
print(f"[OK] 文件追踪: 1条 (未填: {','.join(excel_unfilled)})")

# ============================================================
# 14. 收藏 + 设置 + Token用量
# ============================================================
for m in msgs:
    if m.content == "新版API接口已部署到测试环境，大家开始联调":
        db.add(Favorite(user_id=U["张三"], message_id=m.id, created_at=now - timedelta(hours=20)))
        break
db.commit()

db.add(UserSettings(user_id=U["张三"], model_provider="qwen", file_check_interval_min=60, email_check_interval_hours=12, updated_at=now))
db.add(TokenUsage(user_id=U["张三"], date=today, request_count=15, token_count=12000, updated_at=now))
db.commit()
print(f"[OK] 收藏:1 设置:1 Token:1")

# ============================================================
# 完成
# ============================================================
db.close()
print("\n" + "=" * 60)
print("精简版演示数据生成完成！")
print("=" * 60)
print(f"用户: 5人 (3个部门)")
print(f"联系人: 4个 (2群聊+2私聊)")
print(f"消息: {len(msgs)}条")
print(f"文件: 2个 (1 Markdown + 1 Excel)")
print(f"文件收集: 1个 ({len(excel_filled)}/5已提交)")
print(f"待办: {len(todos)+1}条 (含1条逾期)")
print(f"候选待办: {len(candidates)}条")
print(f"邮件: 3封 (含回复+催办提醒)")
print(f"邮件追踪: 1条")
print(f"在线表单: 2个")
print(f"  表单1「7月工作汇报」: 3/5全部完成, 2/5未填")
print(f"  表单2「测试文件260720」: 1/5全部完成, 3/5部分填写, 1/5未填")
print(f"表格追踪: 2条")
print(f"文件追踪: 1条")
print("=" * 60)
print("数据亮点:")
print(f"  ✓ 部分填写场景：李四填2/4列、赵六填1/4列、郑十填3/4列 → AI总结能精准检测")
print(f"  ✓ 催办消息：群聊中有2条催办记录")
print(f"  ✓ 逾期待办：1条已过期未完成")
print(f"  ✓ 邮件催办：3封邮件含回复链+催办提醒")
print(f"  ✓ 接口联调讨论：项目组群有完整的bug修复对话")
print("=" * 60)
