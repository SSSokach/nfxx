<template>
  <div class="ai-panel">
    <!-- Header -->
    <div class="ai-header">
      <div class="ai-header-top">
        <div>
          <div class="ai-title">AI办公助手</div>
          <div class="ai-description">智能办公多面手 · 对话 / 待办</div>
        </div>
        <div class="ai-header-actions">
          <button class="ai-new-chat-btn" v-if="activeTab === 'chat'" @click="newConversation">+ 新对话</button>
          <div class="ai-user-badge">用户 {{ currentUserLabel }}</div>
          <button class="ai-close-btn" @click="emit('close')" title="收起">✕</button>
        </div>
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
            <template v-if="msg.role === 'user'">
              <div
                v-if="msg.context"
                class="ai-message-quote"
                :class="{ email: msg.context.source_type === 'email' }"
              >
                <div class="ai-message-quote-line"></div>
                <div class="ai-message-quote-body">
                  <span class="ai-message-quote-name">{{ msg.context.sender_name }}</span>
                  <span class="ai-message-quote-text">: {{ msg.context.content.substring(0, 80) }}{{ msg.context.content.length > 80 ? '...' : '' }}</span>
                </div>
              </div>
              <div class="ai-message-text">{{ msg.content }}</div>
            </template>
            <template v-else>
              <div class="ai-message-markdown" v-html="renderMarkdown(msg.content)"></div>
            </template>
          </div>
          <div v-if="aiLoading" class="ai-message assistant">处理中...</div>
        </div>

        <!-- Quick prompt bubbles (above input, vertical, only before first message) -->
        <div class="ai-quick-bubbles-vertical" v-if="showQuickBubbles">
          <button
            v-for="btn in quickBubbles"
            :key="btn.label"
            class="ai-quick-bubble-v"
            :disabled="aiLoading"
            @click="fillPrompt(btn.prompt)"
          >{{ btn.label }}</button>
        </div>

        <div class="ai-context-banner" :class="{ email: localContext?.source_type === 'email' }" v-if="localContext">
          <div class="ai-context-card">
            <div class="ai-context-line"></div>
            <div class="ai-context-body">
              <span class="ai-context-name">{{ localContext.sender_name }}</span>
              <span class="ai-context-text">: {{ localContext.content.substring(0, 60) }}{{ localContext.content.length > 60 ? '...' : '' }}</span>
            </div>
          </div>
          <button class="ai-context-close" @click="clearContext">×</button>
        </div>

        <div class="ai-usage-bar" v-if="aiUsage.request_count > 0 || aiUsage.token_count > 0">
          <div class="ai-usage-info">
            今日用量：{{ aiUsage.request_count }}/{{ aiUsage.limits?.request_count || 50 }} 次请求 · {{ aiUsage.token_count }}/{{ aiUsage.limits?.token_count || 50000 }} tokens
          </div>
          <div class="ai-usage-progress">
            <div class="ai-usage-fill" :style="{width: usagePercent + '%'}" :class="usageLevel"></div>
          </div>
          <div class="ai-usage-hint" v-if="usagePercent > 60">⚠️ 用量较高，AI响应已降速</div>
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
      </div>

      <!-- ===== Merged Todo Tab (split into candidate top + confirmed bottom) ===== -->
      <div v-show="activeTab === 'todo'" class="tab-pane tab-pane-todo">
        <div v-if="todoError" class="pane-error">{{ todoError }}</div>

        <!-- Top: Candidate Todos -->
        <div class="todo-col">
          <div class="todo-col-header">
            <span class="todo-col-title">🔍 候选待办</span>
            <div class="todo-scan-group">
              <button
                class="todo-scan-btn"
                :disabled="candidateScanning || emailScanning"
                @click="scanCandidates"
              >{{ candidateScanning ? '扫描中...' : 'AI扫描消息' }}</button>
              <button
                class="todo-scan-btn email"
                :disabled="candidateScanning || emailScanning"
                @click="scanEmails"
              >{{ emailScanning ? '扫描中...' : '扫描邮件' }}</button>
            </div>
          </div>
          <div v-if="(candidateScanning || emailScanning) && candidateTodos.length === 0" class="pane-loading">AI 正在扫描...</div>
          <div class="todo-scroll">
            <div v-if="candidateTodos.length === 0 && !candidateScanning" class="pane-empty">暂无候选待办</div>
            <div
              v-for="c in candidateTodos"
              :key="`cand-${c.id}`"
              class="candidate-item"
            >
              <div class="candidate-content">{{ c.content }}</div>
              <div class="candidate-meta">
                <span class="meta-tag email" v-if="c.source_type === 'email'">✉️ {{ c.source_name }}</span>
                <span class="meta-tag" v-else-if="c.source_type === 'group'">👥 {{ c.source_name }}</span>
                <span class="meta-tag" v-else>💬 {{ c.source_name }}</span>
                <span class="meta-time" v-if="c.deadline">⏰ {{ formatDate(c.deadline) }}</span>
              </div>
              <div class="candidate-actions">
                <button class="mini-btn success" @click="confirmCandidate(c)">确认</button>
                <button class="mini-btn danger" @click="dismissCandidate(c)">忽略</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Divider -->
        <div class="todo-divider"></div>

        <!-- Bottom: Confirmed Todos -->
        <div class="todo-col">
          <div class="todo-col-header">
            <span class="todo-col-title">✅ 待办列表</span>
          </div>
          <div v-if="todoLoading && mergedTodos.length === 0" class="pane-loading">加载中...</div>
          <div class="todo-scroll">
            <div v-if="mergedTodos.length === 0 && !todoLoading" class="pane-empty">暂无待办</div>
            <div
              v-for="todo in mergedTodos"
              :key="todo.uid"
              class="todo-item"
              :class="{ overdue: !todo.completed && isOverdue(todo.deadline), completed: todo.status === 'completed', clickable: todo.status === 'pending' }"
              @click="handleTodoClick(todo)"
            >
              <div class="todo-content">{{ todo.content || todo.title }}</div>
              <div class="todo-meta">
                <span class="meta-tag email" v-if="todo.source_type === 'email'">✉️ 邮件</span>
                <span class="meta-tag" v-else-if="todo.source_type === 'private'">💬 私聊</span>
                <span class="meta-tag" v-else>👥 群聊</span>
                <span class="meta-tag" v-if="todo.source_name">📁 {{ todo.source_name }}</span>
                <span class="meta-time" v-if="todo.deadline">⏰ {{ formatDate(todo.deadline) }}</span>
                <span class="status-badge" :class="todo.status">{{ statusLabel(todo.status) }}</span>
              </div>
              <div class="todo-jump-hint" v-if="todo.status === 'pending'">
                <span v-if="todo.type === 'chat'">🔗 点击跳转到消息</span>
                <span v-else>🔗 点击查看邮件</span>
              </div>
              <div class="todo-actions" v-if="todo.status === 'pending'" @click.stop>
                <button class="mini-btn success" @click="completeTodo(todo)">完成</button>
                <button class="mini-btn danger" @click="deleteTodo(todo)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== Forms Tab ===== -->
      <div v-show="activeTab === 'forms'" class="tab-pane tab-pane-forms">
        <div class="forms-scroll">
          <!-- Create online form -->
          <div class="forms-toolbar">
            <select v-model="formTrackerContactId" class="form-select">
              <option value="">选择群聊</option>
              <option v-for="c in contactsForForms" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <input v-model="formTrackerName" class="form-input" placeholder="表格名称" />
            <input v-model="formTrackerMembers" class="form-input" placeholder="需填写人员(逗号分隔)" />
          </div>
          <div class="forms-columns-row" v-if="formTrackerName">
            <input v-model="formColumnInput" class="form-input" placeholder="自定义列名(逗号分隔)，如: 周报,进度,备注" style="flex:1" />
          </div>
          <div class="forms-actions-row">
            <button class="form-btn" @click="createOnlineForm" :disabled="!formTrackerContactId || !formTrackerName || !formTrackerMembers">📋 创建在线表格</button>
            <button class="form-btn ghost" @click="createFormTracker" :disabled="!formTrackerContactId || !formTrackerName || !formTrackerMembers">仅追踪</button>
            <button class="form-btn secondary" @click="checkAllForms" :disabled="formsChecking">
              {{ formsChecking ? '检测中...' : '🔍 一键检测' }}
            </button>
          </div>

          <div v-if="formTrackers.length === 0" class="pane-empty">暂无表格追踪</div>
          <div v-for="t in formTrackers" :key="t.id" class="form-tracker-item">
            <div class="form-tracker-header">
              <span class="form-tracker-name">{{ t.form_name }}</span>
              <span class="form-progress-badge" :class="t.status">{{ t.progress }} {{ t.status === 'completed' ? '✓' : '' }}</span>
            </div>
            <div class="form-tracker-body">
              <div class="form-members">
                <span class="form-member-label">已填：</span>
                <span v-for="m in t.filled_members" :key="m" class="form-member-tag done">{{ m }}</span>
                <span v-if="t.filled_members.length === 0" class="form-member-empty">无</span>
              </div>
              <div class="form-members" v-if="t.unfilled_members.length > 0">
                <span class="form-member-label">未填：</span>
                <span v-for="m in t.unfilled_members" :key="m" class="form-member-tag pending">{{ m }}</span>
              </div>
              <div class="form-tracker-meta" v-if="t.last_checked">上次检测：{{ t.last_checked }}</div>
            </div>
            <div class="form-tracker-actions" v-if="t.status === 'tracking'">
              <button class="form-btn small" @click="checkForm(t.id)">检测</button>
              <button class="form-btn small info" v-if="t.form_url && t.form_url.includes('online-forms')" @click="openOnlineForm(t.form_url)">查看表格</button>
              <button class="form-btn small warn" @click="remindForm(t.id)" v-if="t.unfilled_members.length > 0">@催办</button>
              <button class="form-btn small danger" @click="cancelForm(t.id)">取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Email Preview Modal -->
    <div class="email-preview-overlay" v-if="emailPreview" @click.self="emailPreview = null">
      <div class="email-preview-card">
        <div class="email-preview-header">
          <div class="email-preview-subject">{{ emailPreview.subject }}</div>
          <button class="email-preview-close" @click="emailPreview = null">×</button>
        </div>
        <div class="email-preview-sender" v-if="emailPreview.sender">发件人：{{ emailPreview.sender }}</div>
        <div class="email-preview-body">{{ emailPreview.content }}</div>
      </div>
    </div>

    <!-- Online Form Modal -->
    <OnlineFormModal
      :visible="onlineFormVisible"
      :formId="onlineFormId"
      @close="onlineFormVisible = false"
      @remind="handleRemindFromModal"
      @updated="loadFormTrackers"
    />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed, onMounted } from 'vue'
import { aiApi, todosApi, emailsApi, formsApi, chatsApi, onlineFormsApi } from '../api'
import OnlineFormModal from './OnlineFormModal.vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true })

const props = defineProps({
  currentUserId: Number,
  contextMessage: { type: Object, default: null },
  todoRefreshKey: { type: Number, default: 0 }
})

const emit = defineEmits(['jump-to-message', 'jump-to-email', 'close'])

// ===== Tab management =====
const activeTab = ref('chat')
const tabs = [
  { key: 'chat', label: 'AI对话', icon: '💬' },
  { key: 'todo', label: '待办', icon: '📋' },
  { key: 'forms', label: '表格追踪', icon: '📊' }
]

const currentUserLabel = computed(() => {
  const names = ['张三', '李四', '王五']
  return names[(props.currentUserId || 1) - 1] || `#${props.currentUserId || 1}`
})

const switchTab = (key) => {
  activeTab.value = key
  if (key === 'todo') {
    loadAllTodos()
    loadCandidates()
  }
  if (key === 'forms') {
    loadFormTrackers()
    loadContactsForForms()
  }
  if (key === 'chat') {
    loadUsage()
  }
}

// ===== AI Usage (token 限速) =====
const aiUsage = ref({ request_count: 0, token_count: 0 })

const usagePercent = computed(() => {
  const reqPct = aiUsage.value.request_count / (aiUsage.value.limits?.request_count || 50) * 100
  const tokenPct = aiUsage.value.token_count / (aiUsage.value.limits?.token_count || 50000) * 100
  return Math.min(100, Math.max(reqPct, tokenPct))
})

const usageLevel = computed(() => {
  if (usagePercent.value > 80) return 'danger'
  if (usagePercent.value > 60) return 'warn'
  return 'normal'
})

const loadUsage = async () => {
  if (!props.currentUserId) return
  try {
    const res = await aiApi.getUsage(props.currentUserId)
    aiUsage.value = res.data.usage || { request_count: 0, token_count: 0 }
    aiUsage.value.limits = res.data.limits
  } catch (e) {}
}

// ===== AI Chat =====
const aiMessages = ref([
  { role: 'assistant', content: '你好！我是你的AI办公助手，有什么可以帮你的？' }
])
const aiInput = ref('')
const aiLoading = ref(false)
const localContext = ref(null)
const aiMessagesContainer = ref(null)
const hasUserSentMessage = ref(false)

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

const showQuickBubbles = computed(() => !hasUserSentMessage.value)

// Quick prompt bubbles - click to fill input (not send)
// 基于 skills.py 的 9 个 skill，展示 AI 实际功能
const quickBubbles = [
  { label: '📄 总结文件内容', prompt: '帮我总结文件内容' },
  { label: '📊 生成工作报告', prompt: '帮我生成今日日报' },
  { label: '✨ 文本润色', prompt: '帮我润色一段文字' },
  { label: '✉️ 撰写邮件', prompt: '帮我写一封邮件' },
  { label: '🔍 提取信息', prompt: '帮我从文本中提取关键信息' }
]

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

watch(() => props.todoRefreshKey, () => {
  loadAllTodos()
})

watch(() => props.currentUserId, () => {
  chatTodos.value = []
  emailTodos.value = []
  candidateTodos.value = []
  loadAllTodos()
  loadCandidates()
})

const clearContext = () => {
  localContext.value = null
}

const fillPrompt = (prompt) => {
  aiInput.value = prompt
  nextTick(() => {
    const input = document.querySelector('.ai-input')
    if (input) input.focus()
  })
}

const newConversation = () => {
  aiMessages.value = [
    { role: 'assistant', content: '你好！我是你的AI办公助手，有什么可以帮你的？' }
  ]
  aiInput.value = ''
  localContext.value = null
  hasUserSentMessage.value = false
  scrollToBottom()
}

const sendAiMessage = async (overrideMsg) => {
  const userMsg = (overrideMsg !== undefined ? overrideMsg : aiInput.value).trim()
  if (!userMsg || aiLoading.value) return

  hasUserSentMessage.value = true

  // 快照引用上下文，便于在消息列表中展示
  const contextSnapshot = localContext.value ? { ...localContext.value } : null

  let prompt = userMsg
  if (localContext.value) {
    const ctx = localContext.value
    const sourceLabel = ctx.source_type === 'email' ? '邮件' : '消息'
    prompt = `${sourceLabel}内容来自${ctx.sender_name}：「${ctx.content}」\n用户问题：${userMsg}`
  }

  aiMessages.value.push({ role: 'user', content: userMsg, context: contextSnapshot })
  aiInput.value = ''
  aiLoading.value = true
  scrollToBottom()

  if (localContext.value) {
    localContext.value = null
  }

  try {
    const res = await aiApi.chat(props.currentUserId, prompt)
    aiMessages.value.push({ role: 'assistant', content: res.data.response })
    if (res.data.usage) {
      aiUsage.value = { ...res.data.usage, limits: res.data.limits }
    }
  } catch (error) {
    aiMessages.value.push({ role: 'assistant', content: '抱歉，我遇到了一个错误。' })
  }
  aiLoading.value = false
  scrollToBottom()
}

// ===== Shared helpers =====
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

// ===== Merged Todos (chat + email) =====
const chatTodos = ref([])
const emailTodos = ref([])
const todoLoading = ref(false)
const todoError = ref('')

const mergedTodos = computed(() => {
  const chatItems = chatTodos.value.map(t => ({
    uid: `chat-${t.id}`,
    id: t.id,
    type: 'chat',
    content: t.content,
    deadline: t.deadline,
    status: t.status,
    source_type: t.source_type || 'group',
    source_name: t.group_name || t.peer_name || '',
    message_id: t.source_id,
    contact_id: t.contact_id
  }))
  const emailItems = emailTodos.value.map(t => ({
    uid: `email-${t.id}`,
    id: t.id,
    type: 'email',
    content: t.content || t.subject,
    deadline: t.deadline,
    status: t.status,
    source_type: 'email',
    source_name: t.subject || '',
    email_id: t.source_id,
    email_subject: t.subject,
    email_sender: t.sender,
    email_content: t.content
  }))
  // Sort: pending first, then by created_at desc
  return [...chatItems, ...emailItems].sort((a, b) => {
    if (a.status === 'pending' && b.status !== 'pending') return -1
    if (a.status !== 'pending' && b.status === 'pending') return 1
    return 0
  })
})

const loadAllTodos = async () => {
  if (!props.currentUserId) return
  todoLoading.value = true
  todoError.value = ''
  try {
    const [chatRes, emailRes] = await Promise.all([
      todosApi.getChatTodos(props.currentUserId, 'pending'),
      emailsApi.getTodos(props.currentUserId)
    ])
    chatTodos.value = chatRes.data || []
    emailTodos.value = emailRes.data || []
  } catch (e) {
    todoError.value = '加载待办失败'
  }
  todoLoading.value = false
}

const completeTodo = async (todo) => {
  todoError.value = ''
  try {
    if (todo.type === 'chat') {
      await todosApi.updateTodo(todo.id, 'complete')
    } else {
      await emailsApi.updateTodo(todo.id, 'complete')
    }
    await loadAllTodos()
  } catch (e) {
    todoError.value = '操作失败'
  }
}

const deleteTodo = async (todo) => {
  todoError.value = ''
  try {
    if (todo.type === 'chat') {
      await todosApi.updateTodo(todo.id, 'delete')
    } else {
      await emailsApi.updateTodo(todo.id, 'delete')
    }
    await loadAllTodos()
  } catch (e) {
    todoError.value = '操作失败'
  }
}

// ===== Todo click → jump to message/email =====
const emailPreview = ref(null)

const handleTodoClick = (todo) => {
  if (todo.status !== 'pending') return
  if (todo.type === 'chat' && todo.contact_id && todo.message_id) {
    emit('jump-to-message', { contact_id: todo.contact_id, message_id: todo.message_id })
  } else if (todo.type === 'email') {
    // 跳转到对应邮件（携带 email_id，由 App.vue 切换视图并加载邮件详情）
    const emailId = todo.source_id || todo.email_id
    if (emailId) {
      emit('jump-to-email', { email_id: Number(emailId) })
    }
  }
}

// ===== Candidate Todos =====
const candidateTodos = ref([])
const candidateScanning = ref(false)

const loadCandidates = async () => {
  if (!props.currentUserId) return
  try {
    const res = await todosApi.getCandidates(props.currentUserId)
    candidateTodos.value = res.data || []
  } catch (e) {
    // silent fail
  }
}

const scanCandidates = async () => {
  if (!props.currentUserId || candidateScanning.value) return
  candidateScanning.value = true
  todoError.value = ''
  try {
    await todosApi.scanCandidates(props.currentUserId)
    await loadCandidates()
  } catch (e) {
    todoError.value = 'AI 扫描失败'
  }
  candidateScanning.value = false
}

// 扫描邮件生成候选待办：先重置扫描记录，再触发扫描
const emailScanning = ref(false)
const scanEmails = async () => {
  if (!props.currentUserId || emailScanning.value) return
  emailScanning.value = true
  todoError.value = ''
  try {
    await todosApi.rescanEmails(props.currentUserId)
    await todosApi.scanCandidates(props.currentUserId)
    await loadCandidates()
  } catch (e) {
    todoError.value = '邮件扫描失败'
  }
  emailScanning.value = false
}

const confirmCandidate = async (c) => {
  todoError.value = ''
  try {
    await todosApi.confirmCandidate(c.id)
    await loadCandidates()
    await loadAllTodos()
  } catch (e) {
    todoError.value = '确认失败'
  }
}

const dismissCandidate = async (c) => {
  todoError.value = ''
  try {
    await todosApi.dismissCandidate(c.id)
    await loadCandidates()
  } catch (e) {
    todoError.value = '操作失败'
  }
}

onMounted(() => {
  loadUsage()
})

// ===== Form Tracker =====
const formTrackers = ref([])
const formTrackerContactId = ref('')
const formTrackerName = ref('')
const formTrackerMembers = ref('')
const formColumnInput = ref('')
const formsChecking = ref(false)
const contactsForForms = ref([])
const onlineFormVisible = ref(false)
const onlineFormId = ref(null)

const loadFormTrackers = async () => {
  if (!props.currentUserId) return
  try {
    const res = await formsApi.getList(props.currentUserId)
    formTrackers.value = res.data || []
  } catch (e) {}
}

const loadContactsForForms = async () => {
  if (!props.currentUserId) return
  try {
    const res = await chatsApi.getContacts(props.currentUserId)
    // 只显示群聊
    contactsForForms.value = (res.data || []).filter(c => c.is_group)
  } catch (e) {}
}

const createFormTracker = async () => {
  if (!formTrackerContactId.value || !formTrackerName.value || !formTrackerMembers.value) return
  try {
    await formsApi.create(props.currentUserId, formTrackerContactId.value, formTrackerName.value, formTrackerMembers.value)
    formTrackerName.value = ''
    formTrackerMembers.value = ''
    formColumnInput.value = ''
    await loadFormTrackers()
  } catch (e) {
    todoError.value = '创建追踪失败'
  }
}

const createOnlineForm = async () => {
  if (!formTrackerContactId.value || !formTrackerName.value || !formTrackerMembers.value) return
  try {
    // 构建列定义：只使用用户自定义列，填写人由系统自动记录
    const customCols = formColumnInput.value
      ? formColumnInput.value.split(',').map(s => s.trim()).filter(Boolean)
      : ['填写内容']
    const columns = customCols.map((label, i) => ({ key: `col_${i}`, label }))
    const members = formTrackerMembers.value.split(',').map(s => s.trim()).filter(Boolean)
    const res = await onlineFormsApi.create({
      creator_id: props.currentUserId,
      contact_id: parseInt(formTrackerContactId.value),
      title: formTrackerName.value,
      columns: columns,
      required_members: members,
    })
    formTrackerName.value = ''
    formTrackerMembers.value = ''
    formColumnInput.value = ''
    await loadFormTrackers()
    // 打开刚创建的表格
    if (res.data.id) {
      onlineFormId.value = res.data.id
      onlineFormVisible.value = true
    }
  } catch (e) {
    todoError.value = '创建在线表格失败'
  }
}

const openOnlineForm = (formUrl) => {
  const formId = parseInt(formUrl.split('/').pop())
  if (formId) {
    onlineFormId.value = formId
    onlineFormVisible.value = true
  }
}

const handleRemindFromModal = (formId) => {
  // 从弹窗触发催办 — 找到对应的 tracker 并调用 remind
  const tracker = formTrackers.value.find(t => t.form_url && t.form_url.includes(`online-forms/${formId}`))
  if (tracker) {
    remindForm(tracker.id)
  }
}

const checkForm = async (id) => {
  try {
    const res = await formsApi.check(id)
    await loadFormTrackers()
  } catch (e) {}
}

const remindForm = async (id) => {
  try {
    const res = await formsApi.remind(id)
    alert(res.data.message)
    await loadFormTrackers()
  } catch (e) {
    todoError.value = '催办失败'
  }
}

const cancelForm = async (id) => {
  try {
    await formsApi.cancel(id)
    await loadFormTrackers()
  } catch (e) {}
}

const checkAllForms = async () => {
  if (!props.currentUserId || formsChecking.value) return
  formsChecking.value = true
  try {
    await formsApi.checkAll(props.currentUserId)
    await loadFormTrackers()
  } catch (e) {}
  formsChecking.value = false
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
  padding: 10px 2px;
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

/* ===== Context banner ===== */
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

.ai-context-banner.email {
  background-color: #fef3c7;
  border-top-color: #fde68a;
}

.ai-context-banner.email .ai-context-line {
  background-color: #d97706;
}

.ai-context-banner.email .ai-context-name {
  color: #b45309;
}

/* ===== AI message markdown ===== */
.ai-message-markdown {
  line-height: 1.7;
  word-break: break-word;
}

.ai-message-markdown :deep(h1),
.ai-message-markdown :deep(h2),
.ai-message-markdown :deep(h3),
.ai-message-markdown :deep(h4) {
  margin: 12px 0 6px;
  font-weight: 600;
  line-height: 1.4;
}

.ai-message-markdown :deep(h1) { font-size: 18px; }
.ai-message-markdown :deep(h2) { font-size: 16px; }
.ai-message-markdown :deep(h3) { font-size: 15px; }
.ai-message-markdown :deep(h4) { font-size: 14px; }

.ai-message-markdown :deep(p) {
  margin: 6px 0;
}

.ai-message-markdown :deep(ul),
.ai-message-markdown :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.ai-message-markdown :deep(li) {
  margin: 3px 0;
}

.ai-message-markdown :deep(strong) {
  font-weight: 600;
}

.ai-message-markdown :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.ai-message-markdown :deep(pre) {
  background: rgba(0, 0, 0, 0.06);
  padding: 10px 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.ai-message-markdown :deep(pre code) {
  background: none;
  padding: 0;
}

.ai-message-markdown :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  padding-left: 12px;
  margin: 8px 0;
  color: #6b7280;
}

.ai-message-markdown :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.ai-message-markdown :deep(th),
.ai-message-markdown :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 6px 10px;
  text-align: left;
}

.ai-message-markdown :deep(th) {
  background: rgba(0, 0, 0, 0.03);
  font-weight: 600;
}

.ai-message-markdown :deep(hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 12px 0;
}

/* ===== Inline quote inside user message bubble ===== */
.ai-message-quote {
  display: flex;
  gap: 6px;
  padding: 6px 8px;
  margin-bottom: 6px;
  background-color: rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
}

.ai-message-quote.email {
  background-color: rgba(254, 243, 199, 0.92);
  color: #92400e;
}

.ai-message-quote-line {
  width: 3px;
  background-color: rgba(255, 255, 255, 0.7);
  border-radius: 2px;
  flex-shrink: 0;
}

.ai-message-quote.email .ai-message-quote-line {
  background-color: #d97706;
}

.ai-message-quote-body {
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ai-message-quote-name {
  font-weight: 600;
}

.ai-message-text {
  white-space: pre-wrap;
}

/* ===== Header actions ===== */
.ai-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.ai-new-chat-btn {
  padding: 5px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 999px;
  background-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.ai-new-chat-btn:hover {
  background-color: rgba(255, 255, 255, 0.25);
}

.ai-close-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.ai-close-btn:hover {
  background: rgba(239, 68, 68, 0.5);
  color: white;
  transform: rotate(90deg);
}

/* ===== Quick bubbles vertical (above input) ===== */
.ai-quick-bubbles-vertical {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 14px;
  background-color: #faf9ff;
  border-top: 1px solid #e8eaf0;
  flex-shrink: 0;
}

.ai-quick-bubble-v {
  padding: 8px 14px;
  border: 1px solid #d9d4f5;
  border-radius: 10px;
  background-color: #ffffff;
  color: #4a4a5e;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.ai-quick-bubble-v:hover:not(:disabled) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: transparent;
}

.ai-quick-bubble-v:disabled {
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

.pane-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
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

.meta-tag {
  font-size: 11px;
  color: #576b95;
  background-color: #eef0ff;
  padding: 2px 7px;
  border-radius: 10px;
}

/* 邮件待办 tag 用琥珀色区分 */
.meta-tag.email {
  background-color: #fef3c7;
  color: #b45309;
}

.meta-time {
  font-size: 11px;
  color: #b0b3bb;
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

.mini-btn {
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

/* ===== Todo tab: split layout (top/bottom) ===== */
.tab-pane-todo {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.todo-col {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.todo-divider {
  height: 1px;
  width: 100%;
  background-color: #e8eaf0;
  flex-shrink: 0;
}

.todo-col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #e8eaf0;
  flex-shrink: 0;
  background-color: #faf9ff;
}

.todo-col-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a4a5e;
}

.todo-scan-btn {
  padding: 4px 10px;
  border: 1px solid #667eea;
  border-radius: 6px;
  background-color: #667eea;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
}

.todo-scan-btn:hover:not(:disabled) {
  opacity: 0.85;
}

.todo-scan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.todo-scan-group {
  display: flex;
  gap: 6px;
}

.todo-scan-btn.email {
  border-color: #3b82f6;
  background-color: #3b82f6;
}

.todo-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* ===== Candidate todo items ===== */
.candidate-item {
  padding: 10px 12px;
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.15s;
}

.candidate-item:hover {
  border-color: #f59e0b;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.12);
}

.candidate-content {
  font-size: 13px;
  color: #1f2937;
  line-height: 1.5;
  word-break: break-word;
  margin-bottom: 6px;
}

.candidate-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
}

.candidate-actions {
  display: flex;
  gap: 6px;
}

/* Override todo-list for compact scroll area */
.todo-scroll .todo-item {
  margin-bottom: 8px;
}

/* ===== AI Usage Bar ===== */
.ai-usage-bar {
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
}
.ai-usage-info {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}
.ai-usage-progress {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}
.ai-usage-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;
}
.ai-usage-fill.normal { background: #3b82f6; }
.ai-usage-fill.warn { background: #f59e0b; }
.ai-usage-fill.danger { background: #ef4444; }
.ai-usage-hint {
  font-size: 11px;
  color: #f59e0b;
  margin-top: 4px;
}

/* ===== Form Tracker ===== */
.tab-pane-forms {
  overflow: hidden;
}
.forms-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
.forms-toolbar {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.forms-columns-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.forms-actions-row {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.form-btn.ghost { background: #e5e7eb; color: #374151; }
.form-btn.info { background: #6366f1; }
.form-select, .form-input {
  padding: 6px 10px;
  border: 1px solid #dde0e6;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}
.form-select { flex: 0 0 120px; }
.form-input { flex: 1; min-width: 80px; }
.form-btn {
  padding: 6px 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.form-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.form-btn.secondary { background: #6366f1; }
.form-btn.small { padding: 3px 10px; font-size: 12px; }
.form-btn.warn { background: #f59e0b; }
.form-btn.danger { background: #ef4444; }
.form-btn:hover:not(:disabled) { opacity: 0.9; }
.form-tracker-item {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}
.form-tracker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.form-tracker-name { font-weight: 600; font-size: 14px; }
.form-progress-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: #dbeafe;
  color: #2563eb;
}
.form-progress-badge.completed { background: #d1fae5; color: #059669; }
.form-progress-badge.cancelled { background: #f3f4f6; color: #9ca3af; }
.form-tracker-body { font-size: 13px; }
.form-members { margin: 4px 0; display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.form-member-label { color: #6b7280; font-size: 12px; }
.form-member-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.form-member-tag.done { background: #d1fae5; color: #059669; }
.form-member-tag.pending { background: #fef3c7; color: #d97706; }
.form-member-empty { color: #9ca3af; font-size: 12px; }
.form-tracker-meta { color: #9ca3af; font-size: 11px; margin-top: 4px; }
.form-tracker-actions { display: flex; gap: 6px; margin-top: 8px; }

/* ===== Todo click + jump styles ===== */
.todo-item.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}
.todo-item.clickable:hover {
  border-left-color: #6366f1;
  background: rgba(99, 102, 241, 0.06);
  transform: translateX(2px);
}
.todo-jump-hint {
  font-size: 11px;
  color: #6366f1;
  margin-top: 4px;
  opacity: 0.7;
  transition: opacity 0.2s;
}
.todo-item.clickable:hover .todo-jump-hint {
  opacity: 1;
}

/* ===== Email preview modal ===== */
.email-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  animation: fadeIn 0.2s ease;
}
.email-preview-card {
  background: #fff;
  border-radius: 12px;
  max-width: 560px;
  width: 90%;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.email-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}
.email-preview-subject {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}
.email-preview-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
  transition: color 0.2s;
}
.email-preview-close:hover { color: #ef4444; }
.email-preview-sender {
  padding: 8px 20px;
  font-size: 13px;
  color: #6b7280;
  border-bottom: 1px solid #f3f4f6;
}
.email-preview-body {
  padding: 16px 20px;
  font-size: 14px;
  color: #374151;
  line-height: 1.7;
  overflow-y: auto;
  white-space: pre-wrap;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
