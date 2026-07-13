<template>
  <div class="ai-panel">
    <!-- Header (keep existing purple gradient) -->
    <div class="ai-header">
      <div class="ai-header-top">
        <div>
          <div class="ai-title">AI办公助手</div>
          <div class="ai-description">智能办公多面手 · 待办 / 邮件 / 摘要 / 报告</div>
        </div>
        <div class="ai-user-badge">用户 {{ currentUserLabel }}</div>
      </div>
    </div>

    <!-- Tab bar -->
    <div class="ai-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="ai-tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        <span class="ai-tab-icon">{{ tab.icon }}</span>
        <span class="ai-tab-label">{{ tab.label }}</span>
      </div>
    </div>

    <!-- Tab content -->
    <div class="ai-tab-content">
      <!-- ===== AI Chat Tab ===== -->
      <div v-show="activeTab === 'chat'" class="tab-pane tab-pane-chat">
        <div class="ai-messages" ref="aiMessagesContainer">
          <div
            v-for="(msg, index) in aiMessages"
            :key="index"
            class="ai-message"
            :class="msg.role"
          >
            <template v-if="msg.role === 'user'">{{ msg.content }}</template>
            <template v-else>
              {{ msg.content }}
              <div
                v-if="msg.result"
                class="ai-message-result"
              >
                <strong>执行结果:</strong>
                <pre>{{ JSON.stringify(msg.result, null, 2) }}</pre>
              </div>
            </template>
          </div>
          <div v-if="aiLoading" class="ai-message assistant">处理中...</div>
        </div>

        <div class="ai-context-banner" v-if="localContext">
          <div class="ai-context-card">
            <div class="ai-context-line"></div>
            <div class="ai-context-body">
              <span class="ai-context-name">{{ localContext.sender_name }}</span>
              <span class="ai-context-text">: {{ localContext.content.substring(0, 60) }}{{ localContext.content.length > 60 ? '...' : '' }}</span>
            </div>
          </div>
          <button class="ai-context-close" @click="clearContext">×</button>
        </div>

        <div class="ai-input-area">
          <input
            class="ai-input"
            v-model="aiInput"
            :placeholder="localContext ? '基于该消息提问...' : '请输入指令...'"
            @keydown.enter.exact.prevent="sendAiMessage()"
          />
          <button class="ai-send-btn" @click="sendAiMessage()">发送</button>
        </div>

        <div class="ai-quick-buttons">
          <button
            v-for="btn in quickButtons"
            :key="btn"
            class="ai-quick-btn"
            :disabled="aiLoading"
            @click="sendQuickMessage(btn)"
          >{{ btn }}</button>
        </div>
      </div>

      <!-- ===== Message Todo Tab ===== -->
      <div v-show="activeTab === 'msgTodo'" class="tab-pane tab-pane-scroll">
        <div class="pane-toolbar">
          <button class="pane-btn primary" :disabled="scanningMessages" @click="scanMessages">
            {{ scanningMessages ? '扫描中...' : '扫描消息' }}
          </button>
          <button class="pane-btn" :disabled="msgTodoLoading" @click="loadChatSummary(); loadChatTodos()">刷新</button>
        </div>

        <div v-if="msgTodoError" class="pane-error">{{ msgTodoError }}</div>
        <div v-if="msgTodoLoading && chatSummary.length === 0" class="pane-loading">处理中...</div>

        <div class="section-title">@所有人消息摘要</div>
        <div v-if="chatSummary.length === 0 && !msgTodoLoading" class="pane-empty">暂无消息摘要，点击"扫描消息"</div>
        <div class="summary-list">
          <div v-for="item in chatSummary" :key="item.id || item.message_id" class="summary-item">
            <div class="summary-content">{{ item.summary || item.content || '（无摘要内容）' }}</div>
            <div class="summary-meta">
              <span class="meta-tag" v-if="item.group_name || item.source">📁 {{ item.group_name || item.source }}</span>
              <span class="meta-time">{{ formatDateTime(item.created_at || item.time) }}</span>
            </div>
            <button class="mini-btn" @click="convertSummaryToTodo(item)">转为待办</button>
          </div>
        </div>

        <div class="section-title">待办列表</div>
        <div v-if="chatTodos.length === 0 && !msgTodoLoading" class="pane-empty">暂无待办</div>
        <div class="todo-list">
          <div
            v-for="todo in chatTodos"
            :key="todo.id"
            class="todo-item"
            :class="{ overdue: !todo.completed && isOverdue(todo.deadline), completed: todo.status === 'completed' }"
          >
            <div class="todo-content">{{ todo.content || todo.title }}</div>
            <div class="todo-meta">
              <span class="meta-tag" v-if="todo.source || todo.source_group">📁 {{ todo.source || todo.source_group }}</span>
              <span class="meta-time" v-if="todo.deadline">⏰ {{ formatDate(todo.deadline) }}</span>
              <span class="status-badge" :class="todo.status">{{ statusLabel(todo.status) }}</span>
            </div>
            <div class="todo-actions" v-if="todo.status === 'pending'">
              <button class="mini-btn success" @click="updateChatTodo(todo, 'complete')">完成</button>
              <button class="mini-btn danger" @click="updateChatTodo(todo, 'delete')">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== Email Todo Tab ===== -->
      <div v-show="activeTab === 'emailTodo'" class="tab-pane tab-pane-scroll">
        <div class="pane-toolbar">
          <button class="pane-btn primary" :disabled="scanningEmails" @click="scanEmails">
            {{ scanningEmails ? '扫描中...' : '扫描邮件' }}
          </button>
          <button class="pane-btn" :disabled="emailLoading" @click="loadEmailTodos(); loadEmailTrackers()">刷新</button>
        </div>

        <div v-if="emailError" class="pane-error">{{ emailError }}</div>
        <div v-if="emailLoading && emailTodos.length === 0" class="pane-loading">处理中...</div>

        <div class="section-title">邮件待办</div>
        <div v-if="emailTodos.length === 0 && !emailLoading" class="pane-empty">暂无邮件待办，点击"扫描邮件"</div>
        <div class="todo-list">
          <div
            v-for="todo in emailTodos"
            :key="todo.id"
            class="todo-item"
            :class="{ overdue: !todo.completed && isOverdue(todo.deadline), completed: todo.status === 'completed' }"
          >
            <div class="todo-content">{{ todo.todo_content || todo.content || todo.subject }}</div>
            <div class="todo-meta">
              <span class="meta-tag" v-if="todo.subject">✉️ {{ todo.subject }}</span>
              <span class="meta-tag" v-if="todo.sender || todo.from">👤 {{ todo.sender || todo.from }}</span>
              <span class="meta-time" v-if="todo.deadline">⏰ {{ formatDate(todo.deadline) }}</span>
              <span class="status-badge" :class="todo.status">{{ statusLabel(todo.status) }}</span>
            </div>
            <div class="todo-actions" v-if="todo.status === 'pending'">
              <button class="mini-btn success" @click="updateEmailTodo(todo, 'complete')">完成</button>
              <button class="mini-btn danger" @click="updateEmailTodo(todo, 'delete')">删除</button>
            </div>
          </div>
        </div>

        <div class="section-title">邮件回复追踪</div>
        <div class="tracker-toolbar">
          <button class="pane-btn" @click="checkTrackers">检查回复</button>
        </div>
        <div v-if="emailTrackers.length === 0" class="pane-empty">暂无追踪记录</div>
        <div class="tracker-list">
          <div v-for="tracker in emailTrackers" :key="tracker.id || tracker.email_id" class="tracker-card">
            <div class="tracker-subject">{{ tracker.subject || tracker.title || '（无主题）' }}</div>
            <div class="tracker-row">
              <span class="tracker-label">已回复部门：</span>
              <span class="tracker-tags replied">
                <span v-if="!trackerReplied(tracker).length" class="tracker-none">无</span>
                <span v-for="d in trackerReplied(tracker)" :key="d" class="dept-tag ok">{{ d }}</span>
              </span>
            </div>
            <div class="tracker-row">
              <span class="tracker-label">未回复部门：</span>
              <span class="tracker-tags unreplied">
                <span v-if="!trackerUnreplied(tracker).length" class="tracker-none">无</span>
                <span v-for="d in trackerUnreplied(tracker)" :key="d" class="dept-tag warn">{{ d }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== File Summary Tab ===== -->
      <div v-show="activeTab === 'fileSummary'" class="tab-pane tab-pane-scroll">
        <div class="section-title">文件摘要生成</div>
        <div class="file-summary-input">
          <input
            class="pane-input"
            v-model="fileIdInput"
            placeholder="输入文件ID或文件名"
            @keydown.enter="generateFileSummary"
          />
          <button class="pane-btn primary" :disabled="fileSummaryLoading" @click="generateFileSummary">
            {{ fileSummaryLoading ? '处理中...' : '生成摘要' }}
          </button>
        </div>

        <div v-if="fileSummaryError" class="pane-error">{{ fileSummaryError }}</div>
        <div v-if="fileSummaryLoading" class="pane-loading">处理中...</div>

        <div v-if="fileSummaryResult && !fileSummaryLoading" class="summary-result">
          <div v-if="typeof fileSummaryResult === 'string'" class="markdown-content" v-html="renderMarkdown(fileSummaryResult)"></div>
          <div v-else class="summary-card">
            <div v-for="entry in summaryEntries" :key="entry.label" class="summary-field">
              <div class="summary-field-label">{{ entry.label }}</div>
              <div class="summary-field-value">{{ entry.value }}</div>
            </div>
          </div>
        </div>
        <div v-if="!fileSummaryResult && !fileSummaryLoading && !fileSummaryError" class="pane-empty">
          输入文件ID后点击"生成摘要"
        </div>
      </div>

      <!-- ===== Work Report Tab ===== -->
      <div v-show="activeTab === 'workReport'" class="tab-pane tab-pane-scroll">
        <div class="section-title">工作报告生成</div>
        <div class="report-date-row">
          <label class="report-field">
            <span>开始日期</span>
            <input type="date" class="pane-input" v-model="reportStartDate" />
          </label>
          <label class="report-field">
            <span>结束日期</span>
            <input type="date" class="pane-input" v-model="reportEndDate" />
          </label>
        </div>
        <div class="pane-toolbar">
          <button
            class="pane-btn primary"
            :disabled="workReportLoading || !reportStartDate || !reportEndDate"
            @click="generateWorkReport"
          >
            {{ workReportLoading ? '处理中...' : '生成报告' }}
          </button>
        </div>

        <div v-if="workReportError" class="pane-error">{{ workReportError }}</div>
        <div v-if="workReportLoading" class="pane-loading">处理中...</div>

        <div v-if="workReportContent && !workReportLoading" class="report-content markdown-content" v-html="renderMarkdown(workReportContent)"></div>
        <div v-if="!workReportContent && !workReportLoading && !workReportError" class="pane-empty">
          选择时间段后点击"生成报告"
        </div>
      </div>

      <!-- ===== Smart Reply Tab ===== -->
      <div v-show="activeTab === 'smartReply'" class="tab-pane tab-pane-scroll">
        <div class="section-title">智能回复建议</div>
        <div class="smart-reply-hint">在聊天区域右键点击对方消息，选择「智能回复」即可在此查看建议</div>

        <div v-if="smartReplyLoading" class="pane-loading">AI 正在生成回复建议...</div>
        <div v-if="smartReplyError" class="pane-error">{{ smartReplyError }}</div>

        <div v-if="smartReplyData && !smartReplyLoading" class="smart-reply-result">
          <div class="smart-reply-source">
            <span class="meta-tag">来自 {{ smartReplyData.message?.sender_name || '对方' }}</span>
            <span class="meta-time" v-if="smartReplyData.tone">建议语气：{{ smartReplyData.tone }}</span>
          </div>
          <div class="smart-reply-original">{{ smartReplyData.message?.content }}</div>
          <div class="smart-reply-list">
            <div
              v-for="(reply, idx) in smartReplyData.replies"
              :key="idx"
              class="smart-reply-option"
              @click="useSmartReply(reply)"
            >
              <div class="smart-reply-num">{{ idx + 1 }}</div>
              <div class="smart-reply-text">{{ reply }}</div>
              <div class="smart-reply-use">点击使用</div>
            </div>
          </div>
        </div>

        <div v-if="!smartReplyData && !smartReplyLoading && !smartReplyError" class="pane-empty">
          暂无回复建议
        </div>
      </div>

      <!-- ===== Daily Digest Tab ===== -->
      <div v-show="activeTab === 'dailyDigest'" class="tab-pane tab-pane-scroll">
        <div class="section-title">AI 工作日报</div>
        <div class="pane-toolbar">
          <button
            class="pane-btn primary"
            :disabled="dailyDigestLoading"
            @click="generateDailyDigest"
          >
            {{ dailyDigestLoading ? '生成中...' : '生成今日日报' }}
          </button>
        </div>

        <div v-if="dailyDigestError" class="pane-error">{{ dailyDigestError }}</div>
        <div v-if="dailyDigestLoading" class="pane-loading">AI 正在汇总今日工作动态...</div>

        <div v-if="dailyDigestContent && !dailyDigestLoading" class="report-content markdown-content" v-html="renderMarkdown(dailyDigestContent)"></div>
        <div v-if="!dailyDigestContent && !dailyDigestLoading && !dailyDigestError" class="pane-empty">
          点击"生成今日日报"自动汇总今天的工作动态
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { marked } from 'marked'
import { aiApi, todosApi, emailsApi, reportsApi } from '../api'

const props = defineProps({
  currentUserId: Number,
  contextMessage: { type: Object, default: null },
  smartReplyEvent: { type: Object, default: null }
})

// ===== Tab management =====
const activeTab = ref('chat')
const tabs = [
  { key: 'chat', label: 'AI对话', icon: '💬' },
  { key: 'msgTodo', label: '消息待办', icon: '📋' },
  { key: 'emailTodo', label: '邮件待办', icon: '📧' },
  { key: 'fileSummary', label: '文件摘要', icon: '📄' },
  { key: 'workReport', label: '工作报告', icon: '📊' },
  { key: 'smartReply', label: '智能回复', icon: '💡' },
  { key: 'dailyDigest', label: 'AI日报', icon: '📰' }
]

const currentUserLabel = computed(() => {
  const names = ['张三', '李四', '王五']
  return names[(props.currentUserId || 1) - 1] || `#${props.currentUserId || 1}`
})

const switchTab = (key) => {
  activeTab.value = key
  if (key === 'msgTodo') {
    if (chatSummary.value.length === 0) loadChatSummary()
    if (chatTodos.value.length === 0) loadChatTodos()
  } else if (key === 'emailTodo') {
    if (emailTodos.value.length === 0) loadEmailTodos()
    if (emailTrackers.value.length === 0) loadEmailTrackers()
  }
}

// ===== AI Chat (preserved) =====
const aiMessages = ref([
  { role: 'assistant', content: '你好！我是你的AI办公助手。我可以帮你：\n- 📄 读取和总结文件内容\n- 💬 读取聊天记录、发送消息\n- 👥 查看联系人列表\n- 🔍 搜索文件内容\n- 📋 查看最近消息\n\n你可以直接告诉我文件名，我会自动读取内容并处理。右键聊天消息选择"AI对话"可基于消息内容对话。' }
])
const aiInput = ref('')
const aiLoading = ref(false)
const localContext = ref(null)
const aiMessagesContainer = ref(null)
const quickButtons = ['查看文件列表', '查看联系人', '查看最近消息']

const scrollToBottom = () => {
  nextTick(() => {
    if (aiMessagesContainer.value) {
      aiMessagesContainer.value.scrollTop = aiMessagesContainer.value.scrollHeight
    }
  })
}

watch(() => props.contextMessage, (newVal) => {
  if (newVal) {
    localContext.value = newVal
    activeTab.value = 'chat'
    nextTick(() => {
      const input = document.querySelector('.ai-input')
      if (input) input.focus()
    })
  }
})

const clearContext = () => {
  localContext.value = null
}

const sendAiMessage = async (overrideMsg) => {
  const isQuick = overrideMsg !== undefined && overrideMsg !== null
  const userMsg = (isQuick ? overrideMsg : aiInput.value).trim()
  if (!userMsg || aiLoading.value) return

  let prompt = userMsg
  if (localContext.value) {
    const ctx = localContext.value
    prompt = `消息内容来自${ctx.sender_name}：「${ctx.content}」\n用户问题：${userMsg}`
  }

  aiMessages.value.push({ role: 'user', content: userMsg })
  if (!isQuick) aiInput.value = ''
  aiLoading.value = true
  scrollToBottom()

  if (localContext.value) {
    localContext.value = null
  }

  try {
    const res = await aiApi.chat(props.currentUserId, prompt)
    aiMessages.value.push({ role: 'assistant', content: res.data.response, result: res.data.result })
  } catch (error) {
    aiMessages.value.push({ role: 'assistant', content: '抱歉，我遇到了一个错误。' })
  }
  aiLoading.value = false
  scrollToBottom()
}

const sendQuickMessage = (btn) => {
  sendAiMessage(btn)
}

// ===== Shared helpers =====
const formatDateTime = (str) => {
  if (!str) return ''
  const d = new Date(str)
  if (isNaN(d)) return str
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const formatDate = (str) => {
  if (!str) return ''
  const d = new Date(str)
  if (isNaN(d)) return str
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const isOverdue = (deadline) => {
  if (!deadline) return false
  const d = new Date(deadline)
  if (isNaN(d)) return false
  return d < new Date()
}

const statusLabel = (status) => {
  const map = { pending: '待处理', completed: '已完成', deleted: '已删除' }
  return map[status] || status || '待处理'
}

// ===== Message Todos =====
const chatSummary = ref([])
const chatTodos = ref([])
const msgTodoLoading = ref(false)
const scanningMessages = ref(false)
const msgTodoError = ref('')

const loadChatSummary = async () => {
  if (!props.currentUserId) return
  msgTodoLoading.value = true
  msgTodoError.value = ''
  try {
    const res = await todosApi.getChatSummary(props.currentUserId)
    chatSummary.value = res.data || []
  } catch (e) {
    msgTodoError.value = '加载消息摘要失败'
  }
  msgTodoLoading.value = false
}

const loadChatTodos = async () => {
  if (!props.currentUserId) return
  try {
    const res = await todosApi.getChatTodos(props.currentUserId, 'pending')
    chatTodos.value = res.data || []
  } catch (e) {
    msgTodoError.value = '加载待办失败'
  }
}

const scanMessages = async () => {
  if (!props.currentUserId) return
  scanningMessages.value = true
  msgTodoError.value = ''
  try {
    await todosApi.scanMessages(props.currentUserId)
    await Promise.all([loadChatSummary(), loadChatTodos()])
  } catch (e) {
    msgTodoError.value = '扫描消息失败'
  }
  scanningMessages.value = false
}

const convertSummaryToTodo = async (item) => {
  msgTodoError.value = ''
  try {
    const id = item.id || item.message_id || item.msg_id
    await todosApi.convertToTodo(id)
    await Promise.all([loadChatSummary(), loadChatTodos()])
  } catch (e) {
    msgTodoError.value = '转为待办失败'
  }
}

const updateChatTodo = async (todo, action) => {
  msgTodoError.value = ''
  try {
    await todosApi.updateTodo(todo.id, action)
    await loadChatTodos()
  } catch (e) {
    msgTodoError.value = '操作失败'
  }
}

// ===== Email Todos =====
const emailTodos = ref([])
const emailTrackers = ref([])
const emailLoading = ref(false)
const scanningEmails = ref(false)
const emailError = ref('')

const loadEmailTodos = async () => {
  if (!props.currentUserId) return
  emailLoading.value = true
  emailError.value = ''
  try {
    const res = await emailsApi.getTodos(props.currentUserId)
    emailTodos.value = res.data || []
  } catch (e) {
    emailError.value = '加载邮件待办失败'
  }
  emailLoading.value = false
}

const loadEmailTrackers = async () => {
  if (!props.currentUserId) return
  try {
    const res = await emailsApi.getTrackers(props.currentUserId)
    emailTrackers.value = res.data || []
  } catch (e) {
    emailError.value = '加载追踪失败'
  }
}

const scanEmails = async () => {
  if (!props.currentUserId) return
  scanningEmails.value = true
  emailError.value = ''
  try {
    await emailsApi.scan(props.currentUserId)
    await loadEmailTodos()
  } catch (e) {
    emailError.value = '扫描邮件失败'
  }
  scanningEmails.value = false
}

const updateEmailTodo = async (todo, action) => {
  emailError.value = ''
  try {
    await emailsApi.updateTodo(todo.id, action)
    await loadEmailTodos()
  } catch (e) {
    emailError.value = '操作失败'
  }
}

const checkTrackers = async () => {
  if (!props.currentUserId) return
  emailError.value = ''
  try {
    await emailsApi.checkTrackers(props.currentUserId)
    await loadEmailTrackers()
  } catch (e) {
    emailError.value = '检查回复失败'
  }
}

const trackerReplied = (tracker) => {
  return tracker.replied_departments || tracker.replied || tracker.replied_depts || []
}

const trackerUnreplied = (tracker) => {
  return tracker.unreplied_departments || tracker.unreplied || tracker.unreplied_depts || []
}

// ===== File Summary =====
const fileIdInput = ref('')
const fileSummaryResult = ref(null)
const fileSummaryLoading = ref(false)
const fileSummaryError = ref('')

const fieldLabelMap = {
  topic: '主题',
  subject: '主题',
  title: '标题',
  amount: '金额',
  money: '金额',
  value: '金额',
  rules: '规则',
  rule: '规则',
  standards: '考核标准',
  assessment: '考核标准',
  summary: '摘要',
  content: '内容',
  description: '描述',
  file_name: '文件名',
  filename: '文件名',
  file_id: '文件ID',
  category: '分类',
  date: '日期',
  deadline: '截止日期',
  notes: '备注',
  remark: '备注'
}

const summaryEntries = computed(() => {
  const r = fileSummaryResult.value
  if (!r || typeof r === 'string') return []
  const entries = []
  for (const [k, v] of Object.entries(r)) {
    if (v === null || v === undefined) continue
    let value
    if (Array.isArray(v)) {
      value = v.join('；')
    } else if (typeof v === 'object') {
      value = JSON.stringify(v)
    } else {
      value = String(v)
    }
    entries.push({ label: fieldLabelMap[k] || k, value })
  }
  return entries
})

const generateFileSummary = async () => {
  const fid = fileIdInput.value.trim()
  if (!fid || fileSummaryLoading.value) return
  fileSummaryLoading.value = true
  fileSummaryError.value = ''
  fileSummaryResult.value = null
  try {
    const res = await reportsApi.fileSummary(fid)
    fileSummaryResult.value = res.data
  } catch (e) {
    fileSummaryError.value = '生成摘要失败'
  }
  fileSummaryLoading.value = false
}

// ===== Work Report =====
const reportStartDate = ref('')
const reportEndDate = ref('')
const workReportContent = ref('')
const workReportLoading = ref(false)
const workReportError = ref('')

const generateWorkReport = async () => {
  if (!props.currentUserId || !reportStartDate.value || !reportEndDate.value || workReportLoading.value) return
  workReportLoading.value = true
  workReportError.value = ''
  workReportContent.value = ''
  try {
    const res = await reportsApi.workReport(props.currentUserId, reportStartDate.value, reportEndDate.value)
    const data = res.data
    if (typeof data === 'string') {
      workReportContent.value = data
    } else {
      workReportContent.value = data.report || data.content || data.markdown || JSON.stringify(data, null, 2)
    }
  } catch (e) {
    workReportError.value = '生成报告失败'
  }
  workReportLoading.value = false
}

const renderMarkdown = (content) => {
  if (!content) return ''
  return marked(content)
}

// ===== Smart Reply =====
const smartReplyData = ref(null)
const smartReplyLoading = ref(false)
const smartReplyError = ref('')

watch(() => props.smartReplyEvent, (newVal) => {
  if (newVal) {
    smartReplyData.value = newVal
    smartReplyError.value = ''
    activeTab.value = 'smartReply'
  }
})

const useSmartReply = (reply) => {
  if (window.__useSmartReply) {
    window.__useSmartReply(reply)
  }
}

// ===== Daily Digest =====
const dailyDigestContent = ref('')
const dailyDigestLoading = ref(false)
const dailyDigestError = ref('')

const generateDailyDigest = async () => {
  if (!props.currentUserId || dailyDigestLoading.value) return
  dailyDigestLoading.value = true
  dailyDigestError.value = ''
  dailyDigestContent.value = ''
  try {
    const res = await aiApi.dailyDigest(props.currentUserId)
    dailyDigestContent.value = res.data.report || ''
  } catch (e) {
    dailyDigestError.value = '日报生成失败'
  }
  dailyDigestLoading.value = false
}
</script>

<style scoped>
/* ===== Tab bar ===== */
.ai-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ai-user-badge {
  flex-shrink: 0;
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.96);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
}

.ai-tabs {
  display: flex;
  background-color: #ffffff;
  border-bottom: 1px solid #e8eaf0;
  flex-shrink: 0;
}

.ai-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 8px 2px;
  cursor: pointer;
  color: #8a8f99;
  transition: all 0.18s;
  border-bottom: 2px solid transparent;
}

.ai-tab:hover {
  color: #667eea;
  background-color: #faf9ff;
}

.ai-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  background-color: #f5f3ff;
}

.ai-tab-icon {
  font-size: 15px;
  line-height: 1;
}

.ai-tab-label {
  font-size: 11px;
  line-height: 1.2;
  white-space: nowrap;
}

/* ===== Tab content container ===== */
.ai-tab-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tab-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tab-pane-scroll {
  overflow-y: auto;
  padding: 12px;
}

.tab-pane-chat {
  overflow: hidden;
}

/* ===== Context banner (preserved) ===== */
.ai-context-banner {
  padding: 8px 14px;
  background-color: #f0f2f5;
  border-top: 1px solid #e0e0e0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex-shrink: 0;
}

.ai-context-card {
  display: flex;
  gap: 6px;
  flex: 1;
  padding: 6px 10px;
  background-color: #ffffff;
  border-radius: 6px;
}

.ai-context-line {
  width: 3px;
  background-color: #999;
  border-radius: 2px;
  flex-shrink: 0;
}

.ai-context-body {
  font-size: 12px;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ai-context-name {
  color: #576b95;
  font-weight: 500;
}

.ai-context-text {
  color: #666;
}

.ai-context-close {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-context-close:hover {
  color: #333;
}

/* ===== AI message result ===== */
.ai-message-result {
  margin-top: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  font-size: 12px;
}

.ai-message-result pre {
  margin-top: 4px;
  white-space: pre-wrap;
  font-family: 'Monaco', 'Menlo', monospace;
}

/* ===== Quick buttons ===== */
.ai-quick-buttons {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid #e8eaf0;
  background-color: #faf9ff;
  flex-shrink: 0;
  overflow-x: auto;
}

.ai-quick-btn {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid #d9d4f5;
  border-radius: 14px;
  background-color: #ffffff;
  color: #667eea;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.ai-quick-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: transparent;
}

.ai-quick-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== Pane shared ===== */
.pane-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.pane-btn {
  padding: 7px 14px;
  border: 1px solid #dde0e6;
  border-radius: 8px;
  background-color: #ffffff;
  color: #444;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.pane-btn:hover:not(:disabled) {
  background-color: #f5f3ff;
  border-color: #667eea;
  color: #667eea;
}

.pane-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: transparent;
}

.pane-btn.primary:hover:not(:disabled) {
  opacity: 0.9;
  color: #fff;
}

.pane-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.pane-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #dde0e6;
  border-radius: 8px;
  font-size: 13px;
  transition: border-color 0.15s;
}

.pane-input:focus {
  outline: none;
  border-color: #667eea;
}

.pane-loading {
  padding: 16px;
  text-align: center;
  color: #888;
  font-size: 13px;
}

.pane-error {
  padding: 8px 12px;
  margin-bottom: 10px;
  background-color: #fff1f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  color: #cf1322;
  font-size: 12px;
}

.pane-empty {
  padding: 20px 12px;
  text-align: center;
  color: #b0b3bb;
  font-size: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a4a5e;
  margin: 14px 0 8px;
  padding-left: 8px;
  border-left: 3px solid #667eea;
}

.section-title:first-child {
  margin-top: 0;
}

/* ===== Summary list ===== */
.summary-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.summary-item {
  position: relative;
  padding: 10px 10px 10px 12px;
  background-color: #f9f8ff;
  border: 1px solid #ece8fb;
  border-radius: 8px;
}

.summary-content {
  font-size: 12.5px;
  color: #333;
  line-height: 1.5;
  margin-bottom: 6px;
  word-break: break-word;
}

.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.meta-tag {
  font-size: 11px;
  color: #576b95;
  background-color: #eef0ff;
  padding: 2px 7px;
  border-radius: 10px;
}

.meta-time {
  font-size: 11px;
  color: #b0b3bb;
}

.mini-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 3px 9px;
  border: none;
  border-radius: 10px;
  background-color: #667eea;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  transition: opacity 0.15s;
}

.mini-btn:hover {
  opacity: 0.85;
}

.mini-btn.success {
  background-color: #22c55e;
}

.mini-btn.danger {
  background-color: #ef4444;
}

/* ===== Todo list ===== */
.todo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}

.todo-item {
  padding: 10px 12px;
  background-color: #ffffff;
  border: 1px solid #e8eaf0;
  border-radius: 8px;
  transition: all 0.15s;
}

.todo-item.overdue {
  border-color: #ffccc7;
  background-color: #fff6f5;
}

.todo-item.completed {
  background-color: #f7f8fa;
  opacity: 0.7;
}

.todo-item.completed .todo-content {
  text-decoration: line-through;
  color: #999;
}

.todo-content {
  font-size: 13px;
  color: #1f2937;
  line-height: 1.5;
  word-break: break-word;
  margin-bottom: 6px;
}

.todo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background-color: #eef0f5;
  color: #666;
}

.status-badge.pending {
  background-color: #fff7e6;
  color: #d48806;
}

.status-badge.completed {
  background-color: #f6ffed;
  color: #389e0d;
}

.status-badge.deleted {
  background-color: #fff1f0;
  color: #cf1322;
}

.todo-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.todo-actions .mini-btn {
  position: static;
}

/* ===== Email trackers ===== */
.tracker-toolbar {
  margin-bottom: 8px;
}

.tracker-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tracker-card {
  padding: 10px 12px;
  background-color: #f9f8ff;
  border: 1px solid #ece8fb;
  border-radius: 8px;
}

.tracker-subject {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
  word-break: break-word;
}

.tracker-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 4px;
  font-size: 12px;
}

.tracker-label {
  color: #666;
  flex-shrink: 0;
}

.tracker-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tracker-none {
  color: #b0b3bb;
}

.dept-tag {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 10px;
}

.dept-tag.ok {
  background-color: #f6ffed;
  color: #389e0d;
}

.dept-tag.warn {
  background-color: #fff1f0;
  color: #cf1322;
}

/* ===== File summary ===== */
.file-summary-input {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.summary-result {
  margin-top: 4px;
}

.summary-card {
  background-color: #f9f8ff;
  border: 1px solid #ece8fb;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.summary-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.summary-field-label {
  font-size: 11px;
  color: #667eea;
  font-weight: 600;
}

.summary-field-value {
  font-size: 13px;
  color: #333;
  line-height: 1.6;
  word-break: break-word;
}

/* ===== Work report ===== */
.report-date-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.report-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.report-content {
  margin-top: 8px;
  padding: 14px;
  background-color: #f9f8ff;
  border: 1px solid #ece8fb;
  border-radius: 10px;
}

/* ===== Markdown overrides inside scoped panel ===== */
.report-content :deep(h1),
.summary-result :deep(h1) {
  font-size: 18px;
  margin-bottom: 10px;
  border-bottom: 1px solid #ece8fb;
  padding-bottom: 6px;
  color: #1a1a2e;
}

.report-content :deep(h2),
.summary-result :deep(h2) {
  font-size: 16px;
  margin-top: 14px;
  margin-bottom: 8px;
  color: #1a1a2e;
}

.report-content :deep(h3),
.summary-result :deep(h3) {
  font-size: 14px;
  margin-top: 10px;
  margin-bottom: 6px;
  color: #333;
}

.report-content :deep(p),
.summary-result :deep(p) {
  margin-bottom: 8px;
}

.report-content :deep(ul),
.report-content :deep(ol),
.summary-result :deep(ul),
.summary-result :deep(ol) {
  padding-left: 20px;
  margin-bottom: 8px;
}

.report-content :deep(li),
.summary-result :deep(li) {
  margin-bottom: 3px;
}

.report-content :deep(code),
.summary-result :deep(code) {
  background-color: #f0eefb;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
}

.report-content :deep(table),
.summary-result :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 8px;
  font-size: 12px;
}

.report-content :deep(th),
.report-content :deep(td),
.summary-result :deep(th),
.summary-result :deep(td) {
  border: 1px solid #e0d9f5;
  padding: 4px 8px;
  text-align: left;
}

/* ===== Smart Reply ===== */
.smart-reply-hint {
  font-size: 12px;
  color: #888;
  margin-bottom: 12px;
  padding: 8px 12px;
  background-color: #f9f8ff;
  border-radius: var(--radius);
  border: 1px dashed #d9d4f5;
}

.smart-reply-result {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.smart-reply-source {
  display: flex;
  align-items: center;
  gap: 8px;
}

.smart-reply-original {
  padding: 10px 12px;
  background-color: #f0f2f5;
  border-radius: var(--radius);
  font-size: 13px;
  color: #333;
  line-height: 1.5;
  border-left: 3px solid #999;
}

.smart-reply-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.smart-reply-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: #ffffff;
  border: 1px solid #e8eaf0;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
}

.smart-reply-option:hover {
  border-color: #667eea;
  background-color: #f5f3ff;
}

.smart-reply-num {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.smart-reply-text {
  flex: 1;
  font-size: 13px;
  color: #1f2937;
  line-height: 1.5;
}

.smart-reply-use {
  font-size: 11px;
  color: #667eea;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.smart-reply-option:hover .smart-reply-use {
  opacity: 1;
}
</style>
