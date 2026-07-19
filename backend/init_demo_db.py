"""
AI办公助手 - 演示数据生成脚本
覆盖所有功能模块的数据，用于产品演示。

功能覆盖清单：
1. 用户与联系人（11个用户，5个群聊，多个私聊）
2. 聊天消息（文本、文件、回复、@所有人、@某人）
3. 文件（markdown + Excel物理文件）
4. 文件收集任务（FileCollectionTask + Item）
5. 待办（ChatTodoItem：pending/completed/overdue）
6. 候选待办（CandidateTodo：pending/confirmed/dismissed）
7. @所有人摘要（ChatSummary）
8. 已扫描消息（ScannedMessage）
9. 邮件（Email + EmailTodoItem + EmailTracker）
10. 表格追踪（FormTracker）
11. 在线表单（OnlineForm + OnlineFormRow）
12. 收藏（Favorite）
13. 用户设置（UserSettings）
14. Token用量（TokenUsage）
15. 文件追踪（FileTracker）
"""
import sys, os, shutil
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

# 清空并重建表
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()
now = datetime.utcnow()
today = date.today()

# ============================================================
# 1. 用户（11人）
# ============================================================
users_data = [
    ("张三", 1), ("李四", 2), ("王五", 3), ("赵六", 4),
    ("孙七", 5), ("周八", 6), ("吴九", 7), ("郑十", 8),
    ("陈一", 9), ("林二", 10), ("黄三", 11),
]
users = []
for name, uid in users_data:
    u = User(id=uid, name=name, avatar="")
    users.append(u)
db.add_all(users)
db.commit()

# 用户索引
U = {u.name: u.id for u in users}  # {"张三": 1, ...}

# ============================================================
# 2. 联系人/会话
# ============================================================
contacts_data = [
    # 私聊
    ("张三与李四", False),
    ("张三与王五", False),
    ("李四与王五", False),
    ("张三与赵六", False),
    # 群聊
    ("全员周报群", True),
    ("项目组", True),
    ("技术讨论群", True),
    ("产品需求群", True),
    ("部门通知群", True),
]
contacts = []
for name, is_group in contacts_data:
    c = Contact(name=name, avatar="", is_group=is_group)
    contacts.append(c)
db.add_all(contacts)
db.commit()

C = {c.name: c.id for c in contacts}

# ============================================================
# 3. 用户-联系人关联
# ============================================================
# 所有群聊：全员11人加入
group_contacts = [c for c in contacts if c.is_group]
all_user_ids = [u.id for u in users]

ucs = []
for gc in group_contacts:
    for uid in all_user_ids:
        ucs.append(UserContact(user_id=uid, contact_id=gc.id))

# 私聊关联
# 张三(1)↔李四(2) → contact 1
ucs += [UserContact(user_id=1, contact_id=C["张三与李四"]), UserContact(user_id=2, contact_id=C["张三与李四"])]
# 张三(1)↔王五(3) → contact 2
ucs += [UserContact(user_id=1, contact_id=C["张三与王五"]), UserContact(user_id=3, contact_id=C["张三与王五"])]
# 李四(2)↔王五(3) → contact 3
ucs += [UserContact(user_id=2, contact_id=C["李四与王五"]), UserContact(user_id=3, contact_id=C["李四与王五"])]
# 张三(1)↔赵六(4) → contact 4
ucs += [UserContact(user_id=1, contact_id=C["张三与赵六"]), UserContact(user_id=4, contact_id=C["张三与赵六"])]

db.add_all(ucs)
db.commit()

# ============================================================
# 4. 消息
# ============================================================
msgs = []

# --- 全员周报群 (C["全员周报群"]) ---
# 普通聊天消息
msgs += [
    Message(sender_id=U["张三"], contact_id=C["全员周报群"],
            content="各位同事好，本周周报请大家在 Excel 模板中填写，周五下班前提交", created_at=now - timedelta(hours=48)),
    Message(sender_id=U["李四"], contact_id=C["全员周报群"],
            content="收到，会尽快填写", created_at=now - timedelta(hours=47)),
    Message(sender_id=U["赵六"], contact_id=C["全员周报群"],
            content="好的，今天下午就填", created_at=now - timedelta(hours=46)),
    Message(sender_id=U["孙七"], contact_id=C["全员周报群"],
            content="请问模板在哪里下载？", created_at=now - timedelta(hours=45)),
    Message(sender_id=U["张三"], contact_id=C["全员周报群"],
            content="模板就是群里发的那个Excel文件，直接在上面填写就行", created_at=now - timedelta(hours=44)),
]

# @所有人消息
msgs += [
    Message(sender_id=U["周八"], contact_id=C["全员周报群"],
            content="@所有人 本周五下午2点开项目评审会议，请各部门准备好汇报材料，截止日期7月18日", created_at=now - timedelta(hours=36)),
    Message(sender_id=U["吴九"], contact_id=C["全员周报群"],
            content="@所有人 服务器将于本周六凌晨2点-4点进行维护升级，请提前保存工作", created_at=now - timedelta(hours=24)),
]

# @张三消息
msgs += [
    Message(sender_id=U["李四"], contact_id=C["全员周报群"],
            content="@张三 周五前提交周报到我邮箱", created_at=now - timedelta(hours=30)),
    Message(sender_id=U["王五"], contact_id=C["全员周报群"],
            content="@张三 下周一前帮忙review一下PR #234", created_at=now - timedelta(hours=20)),
]

# --- 项目组 (C["项目组"]) ---
msgs += [
    Message(sender_id=U["张三"], contact_id=C["项目组"],
            content="新版API接口已部署到测试环境，大家开始联调", created_at=now - timedelta(hours=40)),
    Message(sender_id=U["李四"], contact_id=C["项目组"],
            content="好的，我这边前端已经准备好了", created_at=now - timedelta(hours=39)),
    Message(sender_id=U["王五"], contact_id=C["项目组"],
            content="数据库迁移脚本需要review一下", created_at=now - timedelta(hours=38)),
    Message(sender_id=U["赵六"], contact_id=C["项目组"],
            content="性能测试报告已出，QPS达到5000", created_at=now - timedelta(hours=37)),
    Message(sender_id=U["张三"], contact_id=C["项目组"],
            content="@所有人 请大家在今天下班前完成联调测试，有问题及时反馈", created_at=now - timedelta(hours=12)),
    Message(sender_id=U["李四"], contact_id=C["项目组"],
            content="联调发现3个接口返回格式不一致，已记录在文档中", created_at=now - timedelta(hours=10)),
    Message(sender_id=U["孙七"], contact_id=C["项目组"],
            content="移动端适配已完成，兼容iOS和Android", created_at=now - timedelta(hours=8)),
]

# --- 技术讨论群 (C["技术讨论群"]) ---
msgs += [
    Message(sender_id=U["赵六"], contact_id=C["技术讨论群"],
            content="有没有人遇到MySQL连接池超时的问题？", created_at=now - timedelta(hours=50)),
    Message(sender_id=U["周八"], contact_id=C["技术讨论群"],
            content="试试增大连接池大小，同时检查一下连接回收配置", created_at=now - timedelta(hours=49)),
    Message(sender_id=U["吴九"], contact_id=C["技术讨论群"],
            content="推荐用Druid连接池，自带监控面板", created_at=now - timedelta(hours=48)),
    Message(sender_id=U["郑十"], contact_id=C["技术讨论群"],
            content="Redis集群方案选型，主从还是Sentinel？", created_at=now - timedelta(hours=30)),
    Message(sender_id=U["赵六"], contact_id=C["技术讨论群"],
            content="看数据量，小于10G用Sentinel就够了", created_at=now - timedelta(hours=29)),
]

# --- 产品需求群 (C["产品需求群"]) ---
msgs += [
    Message(sender_id=U["陈一"], contact_id=C["产品需求群"],
            content="V2.0需求文档已更新，新增了以下功能：\n1. 消息批量操作\n2. 文件在线预览\n3. AI智能回复", created_at=now - timedelta(hours=60)),
    Message(sender_id=U["张三"], contact_id=C["产品需求群"],
            content="技术评估需要2天，明天给结论", created_at=now - timedelta(hours=58)),
    Message(sender_id=U["林二"], contact_id=C["产品需求群"],
            content="UI设计稿已完成，已同步到Figma", created_at=now - timedelta(hours=55)),
    Message(sender_id=U["黄三"], contact_id=C["产品需求群"],
            content="后端接口文档已更新，新增了12个API端点", created_at=now - timedelta(hours=50)),
]

# --- 部门通知群 (C["部门通知群"]) ---
msgs += [
    Message(sender_id=U["周八"], contact_id=C["部门通知群"],
            content="@所有人 下周三部门团建，地点待定，请大家投票选择", created_at=now - timedelta(hours=72)),
    Message(sender_id=U["吴九"], contact_id=C["部门通知群"],
            content="我投郊游", created_at=now - timedelta(hours=71)),
    Message(sender_id=U["郑十"], contact_id=C["部门通知群"],
            content="密室逃脱不错", created_at=now - timedelta(hours=70)),
    Message(sender_id=U["张三"], contact_id=C["部门通知群"],
            content="@所有人 本月绩效考核自评表请在本周五前提交到HR系统", created_at=now - timedelta(hours=15)),
]

# --- 私聊：张三↔李四 (C["张三与李四"]) ---
msgs += [
    Message(sender_id=U["李四"], contact_id=C["张三与李四"],
            content="明天上午10点前把接口文档发给我", created_at=now - timedelta(hours=25)),
    Message(sender_id=U["张三"], contact_id=C["张三与李四"],
            content="好的，我整理一下", created_at=now - timedelta(hours=24)),
    Message(sender_id=U["李四"], contact_id=C["张三与李四"],
            content="这周五前帮忙review一下PR", created_at=now - timedelta(hours=18)),
    Message(sender_id=U["张三"], contact_id=C["张三与李四"],
            content="没问题，今天下午就看", created_at=now - timedelta(hours=17)),
    Message(sender_id=U["李四"], contact_id=C["张三与李四"],
            content="对了，明天下午的会议你能参加吗？", created_at=now - timedelta(hours=5)),
    Message(sender_id=U["张三"], contact_id=C["张三与李四"],
            content="可以，2点准时到", created_at=now - timedelta(hours=4)),
]

# --- 私聊：张三↔王五 (C["张三与王五"]) ---
msgs += [
    Message(sender_id=U["王五"], contact_id=C["张三与王五"],
            content="明天的会议准备得怎么样了？", created_at=now - timedelta(hours=35)),
    Message(sender_id=U["张三"], contact_id=C["张三与王五"],
            content="已经准备好了PPT", created_at=now - timedelta(hours=34)),
    Message(sender_id=U["王五"], contact_id=C["张三与王五"],
            content="那太好了，我这边数据也整理完了", created_at=now - timedelta(hours=33)),
]

# --- 私聊：李四↔王五 (C["李四与王五"]) ---
msgs += [
    Message(sender_id=U["王五"], contact_id=C["李四与王五"],
            content="上次那个bug修好了吗？", created_at=now - timedelta(hours=28)),
    Message(sender_id=U["李四"], contact_id=C["李四与王五"],
            content="已经修好了，提交了PR", created_at=now - timedelta(hours=27)),
]

# --- 私聊：张三↔赵六 (C["张三与赵六"]) ---
msgs += [
    Message(sender_id=U["赵六"], contact_id=C["张三与赵六"],
            content="数据库优化方案我写好了，你看看", created_at=now - timedelta(hours=22)),
    Message(sender_id=U["张三"], contact_id=C["张三与赵六"],
            content="收到，我看完给你反馈", created_at=now - timedelta(hours=21)),
]

# 回复消息示例（张三回复李四在项目组的消息）
# 找到"联调发现3个接口返回格式不一致"那条消息
reply_target = None
for m in msgs:
    if m.contact_id == C["项目组"] and "联调发现3个" in m.content:
        reply_target = m
        break
if reply_target:
    msgs.append(Message(sender_id=U["张三"], contact_id=C["项目组"],
                        content="我来统一一下接口返回格式，今天搞定",
                        reply_to_id=reply_target.id, created_at=now - timedelta(hours=9)))

db.add_all(msgs)
db.commit()

print(f"[OK] 消息: {len(msgs)}条")

# ============================================================
# 5. 文件（文本文件 + Excel物理文件）
# ============================================================
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

text_files = [
    File(name="项目计划.md", content="# 项目计划\n\n## 目标\n完成AI助手demo开发\n\n## 时间线\n- 第一周：完成后端API\n- 第二周：完成前端界面\n- 第三周：集成测试\n\n## 里程碑\n- [x] 需求确认\n- [x] 技术方案设计\n- [ ] 后端开发\n- [ ] 前端开发\n- [ ] 联调测试",
         file_type="markdown", owner_id=U["张三"], created_at=now - timedelta(days=10)),
    File(name="技术文档.md", content="# 技术文档\n\n## 技术栈\n- Vue3 + Vite\n- FastAPI\n- SQLite\n- GLM AI\n\n## API设计\nRESTful风格，共10个路由模块，60+个端点\n\n## 数据库\nSQLite，21张表",
         file_type="markdown", owner_id=U["张三"], created_at=now - timedelta(days=8)),
    File(name="Q3季度OKR.md", content="# Q3季度OKR\n\n## O1: 提升产品稳定性\n- KR1: 线上Bug率降低50%\n- KR2: 自动化测试覆盖率达到80%\n\n## O2: 完成核心功能开发\n- KR1: 文件收集功能上线\n- KR2: AI扫描准确率达到90%\n\n## O3: 团队成长\n- KR1: 完成技术分享4次\n- KR2: 新人onboarding流程优化",
         file_type="markdown", owner_id=U["李四"], created_at=now - timedelta(days=5)),
    File(name="会议纪要_0715.md", content="# 项目周会纪要\n\n日期：2026年7月15日\n\n## 参会人员\n张三、李四、王五、赵六\n\n## 本周进展\n1. 后端API开发完成90%\n2. 前端界面完成85%\n3. AI模块集成完成\n\n## 待解决问题\n1. Excel大文件性能优化\n2. 移动端适配\n\n## 下周计划\n1. 完成联调测试\n2. 性能优化\n3. 准备演示环境",
         file_type="markdown", owner_id=U["张三"], created_at=now - timedelta(days=3)),
]

db.add_all(text_files)
db.commit()
print(f"[OK] 文本文件: {len(text_files)}个")

# --- Excel文件 ---
# 创建周报模板Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "周报"
headers = ["姓名", "部门", "本周工作内容", "完成情况", "下周计划"]
ws.append(headers)
# 样式
for col in range(1, 6):
    ws.cell(row=1, column=col).font = openpyxl.styles.Font(bold=True)

# 所有11个人都有行，部分已填写
excel_rows = [
    ("张三", "技术部", "完成AI对话模块开发", "已完成", "集成测试"),
    ("李四", "技术部", "前端界面开发", "已完成", "联调测试"),
    ("王五", "技术部", "数据库设计与优化", "已完成", "部署上线"),
    ("赵六", "技术部", "服务器部署与监控", "已完成", "性能优化"),
    ("孙七", "产品部", "需求文档编写", "已完成", "用户调研"),
    ("周八", "技术部", "API文档编写", "已完成", "接口测试"),
    ("吴九", "技术部", "代码审查", "已完成", "技术分享"),
    ("郑十", "产品部", "竞品分析报告", "", ""),  # 未填写
    ("陈一", "设计部", "UI设计稿", "", ""),  # 未填写
    ("林二", "设计部", "交互设计", "", ""),  # 未填写
    ("黄三", "技术部", "自动化测试", "", ""),  # 未填写
]
for row_data in excel_rows:
    ws.append(row_data)

# 保存物理文件
excel_filename = "周报填写模板.xlsx"
excel_path = os.path.join(UPLOADS_DIR, excel_filename)
wb.save(excel_path)

excel_file = File(name=excel_filename, content="", file_type="xlsx", owner_id=U["张三"], created_at=now - timedelta(hours=46))
db.add(excel_file)
db.commit()

# 复制已有的test_weekly_report.xlsx到uploads（如果不存在）
src_xlsx = os.path.join(UPLOADS_DIR, "test_weekly_report.xlsx")
if not os.path.exists(src_xlsx):
    shutil.copy(excel_path, src_xlsx)
    excel_file2 = File(name="test_weekly_report.xlsx", content="", file_type="xlsx", owner_id=U["张三"], created_at=now - timedelta(hours=47))
    db.add(excel_file2)
    db.commit()
    print("[OK] 复制test_weekly_report.xlsx")

# 在全员周报群中发送Excel文件消息
file_msg = Message(sender_id=U["张三"], contact_id=C["全员周报群"],
                   content="周报填写模板.xlsx", message_type="file", file_id=excel_file.id,
                   created_at=now - timedelta(hours=46))
db.add(file_msg)
db.commit()
print(f"[OK] Excel文件消息: {excel_file.name} (file_id={excel_file.id})")

# ============================================================
# 6. 文件收集任务
# ============================================================
# 为周报Excel创建收集任务
fct = FileCollectionTask(
    initiator_user_id=U["张三"],
    source_message_id=file_msg.id,
    group_name="全员周报群",
    file_name=excel_filename,
    description="请大家填写本周周报，7月18号前提交",
    deadline=date.today() + timedelta(days=3),
    status="collecting",
    created_at=now - timedelta(hours=46),
    updated_at=now,
)
db.add(fct)
db.commit()

# 为每个人创建收集项（已填写的标记submitted）
filled_users = ["张三", "李四", "王五", "赵六", "孙七", "周八", "吴九"]  # 7人已填
unfilled_users = ["郑十", "陈一", "林二", "黄三"]  # 4人未填

for name in filled_users + unfilled_users:
    is_filled = name in filled_users
    item = FileCollectionItem(
        task_id=fct.id,
        assignee_user_id=U[name],
        assignee_name=name,
        status="submitted" if is_filled else "pending",
        submitted_at=now - timedelta(hours=30) if is_filled else None,
        created_at=now - timedelta(hours=46),
    )
    db.add(item)
db.commit()
print(f"[OK] 文件收集任务: {fct.file_name}, 已填{len(filled_users)}/未填{len(unfilled_users)}")

# ============================================================
# 7. 待办（ChatTodoItem）
# ============================================================
todos = []

# 张三的待办
todos += [
    # 已完成的
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="全员周报群",
                 content="[文件收集] 周报填写模板.xlsx - 等待4人提交（7/11）",
                 deadline=date.today() + timedelta(days=3), status="pending",
                 created_at=now - timedelta(hours=46)),
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="项目组",
                 content="统一接口返回格式并修复联调问题", status="completed",
                 completed_at=now - timedelta(hours=5), created_at=now - timedelta(hours=10)),
    ChatTodoItem(user_id=U["张三"], source_type="private", peer_name="李四",
                 content="review PR（李四请求）", status="completed",
                 completed_at=now - timedelta(hours=10), created_at=now - timedelta(hours=18)),
    # pending
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="项目组",
                 content="@所有人：今天下班前完成联调测试",
                 deadline=today, status="pending",
                 created_at=now - timedelta(hours=12)),
    ChatTodoItem(user_id=U["张三"], source_type="private", peer_name="李四",
                 content="发送接口文档给李四", status="completed",
                 completed_at=now - timedelta(hours=20), created_at=now - timedelta(hours=25)),
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="全员周报群",
                 content="周五前提交周报到李四邮箱", deadline=today + timedelta(days=2),
                 status="pending", created_at=now - timedelta(hours=30)),
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="技术讨论群",
                 content="review PR #234（王五请求）",
                 deadline=today + timedelta(days=3), status="pending",
                 created_at=now - timedelta(hours=20)),
    # overdue
    ChatTodoItem(user_id=U["张三"], source_type="group", group_name="产品需求群",
                 content="V2.0技术评估（陈一需求）",
                 deadline=today - timedelta(days=1), status="pending",
                 created_at=now - timedelta(hours=60)),
]

# 郑十的待办（填写文件）
todos.append(ChatTodoItem(
    user_id=U["郑十"], source_type="group", group_name="全员周报群",
    content="[填写文件] 周报填写模板.xlsx - 由 张三 发起 (请大家填写本周周报，7月18号前提交)",
    deadline=date.today() + timedelta(days=3), status="pending",
    created_at=now - timedelta(hours=46),
))
todos.append(ChatTodoItem(
    user_id=U["陈一"], source_type="group", group_name="全员周报群",
    content="[填写文件] 周报填写模板.xlsx - 由 张三 发起 (请大家填写本周周报，7月18号前提交)",
    deadline=date.today() + timedelta(days=3), status="pending",
    created_at=now - timedelta(hours=46),
))

# 吴九的填写待办（已完成）
todos.append(ChatTodoItem(
    user_id=U["吴九"], source_type="group", group_name="全员周报群",
    content="[填写文件] 周报填写模板.xlsx - 由 张三 发起",
    deadline=date.today() + timedelta(days=3), status="completed",
    completed_at=now - timedelta(hours=30), created_at=now - timedelta(hours=46),
))

db.add_all(todos)
db.commit()
print(f"[OK] 待办: {len(todos)}条")

# ============================================================
# 8. 候选待办（CandidateTodo）
# ============================================================
candidates = [
    # 张三的候选待办
    CandidateTodo(user_id=U["张三"], source_type="group", source_name="部门通知群",
                  content="本月绩效考核自评表提交到HR系统",
                  deadline=today + timedelta(days=3), status="pending",
                  created_at=now - timedelta(hours=14)),
    CandidateTodo(user_id=U["张三"], source_type="group", source_name="全员周报群",
                  content="参加周五下午2点的项目评审会议",
                  deadline=today + timedelta(days=2), status="pending",
                  created_at=now - timedelta(hours=35)),
    CandidateTodo(user_id=U["张三"], source_type="group", source_name="项目组",
                  content="确认Redis集群方案选型（Sentinel vs 主从）",
                  status="pending", created_at=now - timedelta(hours=29)),
    # 已确认的
    CandidateTodo(user_id=U["张三"], source_type="group", source_name="全员周报群",
                  content="@所有人 服务器维护升级，提前保存工作",
                  status="confirmed", created_at=now - timedelta(hours=23),
                  updated_at=now - timedelta(hours=22)),
    # 已忽略的
    CandidateTodo(user_id=U["张三"], source_type="group", source_name="部门通知群",
                  content="部门团建投票（郊游/密室逃脱）",
                  status="dismissed", created_at=now - timedelta(hours=70),
                  updated_at=now - timedelta(hours=69)),
]
db.add_all(candidates)
db.commit()
print(f"[OK] 候选待办: {len(candidates)}条")

# ============================================================
# 9. @所有人摘要（ChatSummary）
# ============================================================
summaries = [
    ChatSummary(user_id=U["张三"], source_id=None, group_name="全员周报群",
                content="周八发起：本周五下午2点开项目评审会议，请各部门准备汇报材料，截止7月18日",
                original_message="@所有人 本周五下午2点开项目评审会议...",
                created_at=now - timedelta(hours=35)),
    ChatSummary(user_id=U["张三"], source_id=None, group_name="全员周报群",
                content="吴九发起：本周六凌晨2-4点服务器维护升级，请提前保存",
                original_message="@所有人 服务器将于本周六凌晨...",
                created_at=now - timedelta(hours=23)),
    ChatSummary(user_id=U["张三"], source_id=None, group_name="项目组",
                content="张三发起：今天下班前完成联调测试，有问题及时反馈",
                original_message="@所有人 请大家在今天下班前完成联调测试...",
                created_at=now - timedelta(hours=11)),
]
db.add_all(summaries)
db.commit()
print(f"[OK] 摘要: {len(summaries)}条")

# ============================================================
# 10. 已扫描消息（ScannedMessage）
# ============================================================
scanned = []
for m in msgs[-20:]:  # 最近的20条标记为已扫描
    scanned.append(ScannedMessage(user_id=U["张三"], message_id=m.id, scanned_at=now))
db.add_all(scanned)
db.commit()
print(f"[OK] 已扫描消息: {len(scanned)}条")

# ============================================================
# 11. 邮件
# ============================================================
emails = [
    Email(user_id=U["张三"], subject="关于Q3季度考核的通知", sender="hr@company.com",
          sender_dept="人力资源部", recipients="技术部|产品部|设计部",
          content="各位同事好，Q3季度考核将于7月25日开始，请各部门负责人在7月20日前完成自评表格填写。考核标准：1. 业绩达成率 2. 团队协作 3. 创新贡献。请按时完成。",
          is_reply=False, sent_at=now - timedelta(days=5)),
    Email(user_id=U["张三"], subject="接口文档评审会议邀请", sender="pm@company.com",
          sender_dept="产品部", recipients="技术部",
          content="技术部同事，接口文档评审会议定于7月16日下午3点召开，请提前准备好接口测试报告和性能数据。",
          is_reply=False, sent_at=now - timedelta(days=3)),
    Email(user_id=U["张三"], subject="关于团队建设的通知", sender="admin@company.com",
          sender_dept="行政部", recipients="技术部|产品部|设计部",
          content="本周五下午团队建设活动，请大家穿休闲装，下午2点在大厅集合。活动内容包括户外拓展和团队晚餐。",
          is_reply=False, sent_at=now - timedelta(days=2)),
    Email(user_id=U["张三"], subject="Re: 关于Q3季度考核的通知", sender="tech@company.com",
          sender_dept="技术部", content="收到，我们会按时完成自评。",
          is_reply=True, reply_to_email_id=1, sent_at=now - timedelta(days=4)),
    Email(user_id=U["张三"], subject="Re: 关于Q3季度考核的通知", sender="design@company.com",
          sender_dept="设计部", content="设计部已收到通知，将按时提交。",
          is_reply=True, reply_to_email_id=1, sent_at=now - timedelta(days=3)),
    Email(user_id=U["张三"], subject="V2.0版本发布计划", sender="pm@company.com",
          sender_dept="产品部", recipients="技术部|设计部",
          content="V2.0计划于8月1日发布，请各部门确认功能完成情况。技术部请在7月25日前完成所有开发和测试。",
          is_reply=False, sent_at=now - timedelta(hours=10)),
]
db.add_all(emails)
db.commit()
print(f"[OK] 邮件: {len(emails)}封")

# 邮件待办
email_todos = [
    EmailTodoItem(user_id=U["张三"], source_id="2", subject="接口文档评审会议邀请",
                  sender="pm@company.com", content="准备接口测试报告和性能数据，7月15日前发送",
                  deadline=today - timedelta(days=1), status="completed",
                  completed_at=now - timedelta(days=1), created_at=now - timedelta(days=3)),
    EmailTodoItem(user_id=U["张三"], source_id="1", subject="关于Q3季度考核的通知",
                  sender="hr@company.com", content="完成Q3自评表格填写，7月20日前提交",
                  deadline=today + timedelta(days=3), status="pending",
                  created_at=now - timedelta(days=5)),
    EmailTodoItem(user_id=U["张三"], source_id="6", subject="V2.0版本发布计划",
                  sender="pm@company.com", content="确认技术部功能完成情况，7月25日前完成",
                  deadline=today + timedelta(days=7), status="pending",
                  created_at=now - timedelta(hours=10)),
    EmailTodoItem(user_id=U["张三"], source_id="3", subject="关于团队建设的通知",
                  sender="admin@company.com", content="参加周五下午团队建设活动",
                  deadline=today + timedelta(days=3), status="no_action",
                  created_at=now - timedelta(days=2)),
]
db.add_all(email_todos)
db.commit()
print(f"[OK] 邮件待办: {len(email_todos)}条")

# 邮件追踪
email_trackers = [
    EmailTracker(user_id=U["张三"], email_id="1", subject="关于Q3季度考核的通知",
                 sent_at=now - timedelta(days=5),
                 replied_depts="技术部|设计部", unreplied_depts="产品部",
                 status="tracking", last_checked_at=now - timedelta(hours=12)),
    EmailTracker(user_id=U["张三"], email_id="2", subject="接口文档评审会议邀请",
                 sent_at=now - timedelta(days=3),
                 replied_depts="技术部", unreplied_depts="",
                 status="completed", last_checked_at=now - timedelta(days=1)),
]
db.add_all(email_trackers)
db.commit()
print(f"[OK] 邮件追踪: {len(email_trackers)}条")

# ============================================================
# 12. 表格追踪（FormTracker）
# ============================================================
form_trackers = [
    FormTracker(user_id=U["张三"], contact_id=C["全员周报群"],
                form_name="Q3季度考核自评表", form_url="",
                required_members="张三,李四,王五,赵六,孙七,周八,吴九,郑十,陈一,林二,黄三",
                filled_members="张三,李四,王五,赵六,孙七,周八,吴九",
                status="tracking", last_checked=now - timedelta(hours=2),
                created_at=now - timedelta(hours=48)),
    FormTracker(user_id=U["陈一"], contact_id=C["产品需求群"],
                form_name="V2.0功能确认表", form_url="",
                required_members="张三,李四,王五,赵六",
                filled_members="张三,李四",
                status="tracking", last_checked=now - timedelta(hours=5),
                created_at=now - timedelta(hours=60)),
]
db.add_all(form_trackers)
db.commit()
print(f"[OK] 表格追踪: {len(form_trackers)}条")

# ============================================================
# 13. 在线表单（OnlineForm + OnlineFormRow）
# ============================================================
online_form = OnlineForm(
    creator_id=U["张三"], contact_id=C["全员周报群"],
    title="7月第三周工作汇报",
    columns='[{"key":"weekly_work","label":"本周工作内容"},{"key":"progress","label":"完成进度"},{"key":"plan","label":"下周计划"},{"key":"remark","label":"备注"}]',
    required_members="张三,李四,王五,赵六,孙七,周八,吴九,郑十,陈一,林二,黄三",
    status="active",
    created_at=now - timedelta(hours=50),
)
db.add(online_form)
db.commit()

# 为每个人创建行数据，部分已填写
form_rows = []
filled_form_members = ["张三", "李四", "王五", "赵六", "孙七"]
unfilled_form_members = ["周八", "吴九", "郑十", "陈一", "林二", "黄三"]

sample_data = {
    "张三": '{"weekly_work":"完成AI对话模块和文件收集功能","progress":"100%","plan":"集成测试和性能优化","remark":"需要测试环境支持"}',
    "李四": '{"weekly_work":"前端界面开发和组件优化","progress":"95%","plan":"移动端适配","remark":"等待设计稿更新"}',
    "王五": '{"weekly_work":"数据库优化和迁移脚本","progress":"100%","plan":"生产环境部署","remark":""}',
    "赵六": '{"weekly_work":"服务器部署和监控配置","progress":"90%","plan":"性能压测","remark":"需要运维配合"}',
    "孙七": '{"weekly_work":"V2.0需求文档和用户调研","progress":"80%","plan":"需求评审","remark":"部分需求待确认"}',
}

for name in filled_form_members + unfilled_form_members:
    is_filled = name in filled_form_members
    row = OnlineFormRow(
        form_id=online_form.id,
        member_name=name,
        data=sample_data.get(name, "{}"),
        filled=is_filled,
        filled_at=now - timedelta(hours=40) if is_filled else None,
        created_at=now - timedelta(hours=50),
    )
    form_rows.append(row)

db.add_all(form_rows)
db.commit()
print(f"[OK] 在线表单: {online_form.title}, 已填{len(filled_form_members)}/未填{len(unfilled_form_members)}")

# ============================================================
# 14. 收藏
# ============================================================
# 找几条消息来收藏
fav_msgs = []
for m in msgs:
    if m.content == "新版API接口已部署到测试环境，大家开始联调":
        fav_msgs.append((U["李四"], m.id))
    elif m.content == "V2.0需求文档已更新":
        fav_msgs.append((U["张三"], m.id))
    elif "数据库优化方案" in m.content:
        fav_msgs.append((U["张三"], m.id))

for uid, mid in fav_msgs:
    db.add(Favorite(user_id=uid, message_id=mid, created_at=now - timedelta(hours=20)))
db.commit()
print(f"[OK] 收藏: {len(fav_msgs)}条")

# ============================================================
# 15. 用户设置
# ============================================================
for u in users[:5]:  # 前5个用户有设置
    db.add(UserSettings(
        user_id=u.id, model_provider="qwen",
        file_check_interval_min=60, email_check_interval_hours=12,
        updated_at=now,
    ))
db.commit()
print(f"[OK] 用户设置: 5条")

# ============================================================
# 16. Token用量
# ============================================================
for u in users[:5]:
    db.add(TokenUsage(
        user_id=u.id, date=today,
        request_count=15, token_count=12000,
        updated_at=now,
    ))
db.commit()
print(f"[OK] Token用量: 5条")

# ============================================================
# 17. 文件追踪（FileTracker）
# ============================================================
db.add(FileTracker(
    user_id=U["张三"], file_url="", file_name="周报填写模板.xlsx",
    status="tracking", unfilled_users="郑十,陈一,林二,黄三",
    last_checked_at=now - timedelta(hours=2), check_interval_min=60,
    created_at=now - timedelta(hours=46),
))
db.commit()
print("[OK] 文件追踪: 1条")

# ============================================================
# 完成
# ============================================================
db.close()
print("\n" + "=" * 50)
print("演示数据生成完成！")
print(f"用户: {len(users)}人")
print(f"联系人/会话: {len(contacts)}个")
print(f"消息: {len(msgs)}条")
print(f"文件: {len(text_files) + 1}个 (含1个Excel)")
print(f"文件收集任务: 1个 (7/11已填)")
print(f"待办: {len(todos)}条")
print(f"候选待办: {len(candidates)}条")
print(f"邮件: {len(emails)}封")
print(f"邮件待办: {len(email_todos)}条")
print(f"邮件追踪: {len(email_trackers)}条")
print(f"表格追踪: {len(form_trackers)}条")
print(f"在线表单: 1个 (5/11已填)")
print(f"收藏: {len(fav_msgs)}条")
print("=" * 50)