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

      <!-- ===== Merged Todo Tab ===== -->
      <div v-show="activeTab === 'todo'" class="tab-pane tab-pane-scroll">
        <div class="pane-toolbar">
          <button class="pane-btn" :disabled="todoLoading" @click="loadAllTodos">刷新</button>
        </div>

        <div v-if="todoError" class="pane-error">{{ todoError }}</div>
        <div v-if="todoLoading && mergedTodos.length === 0" class="pane-loading">加载中...</div>

        <div class="section-title">待办列表</div>
        <div v-if="mergedTodos.length === 0 && !todoLoading" class="pane-empty">暂无待办</div>
        <div class="todo-list">
          <div
            v-for="todo in mergedTodos"
            :key="todo.uid"
            class="todo-item"
            :class="{ overdue: !todo.completed && isOverdue(todo.deadline), completed: todo.status === 'completed' }"
          >
            <div class="todo-content">{{ todo.content || todo.title }}</div>
            <div class="todo-meta">
              <span class="meta-tag" v-if="todo.source_type === 'email'">✉️ 邮件</span>
              <span class="meta-tag" v-else-if="todo.source_type === 'private'">💬 私聊</span>
              <span class="meta-tag" v-else>👥 群聊</span>
              <span class="meta-tag" v-if="todo.source_name">📁 {{ todo.source_name }}</span>
              <span class="meta-time" v-if="todo.deadline">⏰ {{ formatDate(todo.deadline) }}</span>
              <span class="status-badge" :class="todo.status">{{ statusLabel(todo.status) }}</span>
            </div>
            <div class="todo-actions" v-if="todo.status === 'pending'">
              <button class="mini-btn success" @click="completeTodo(todo)">完成</button>
              <button class="mini-btn danger" @click="deleteTodo(todo)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { aiApi, todosApi, emailsApi } from '../api'

const props = defineProps({
  currentUserId: Number,
  contextMessage: { type: Object, default: null }
})

// ===== Tab management =====
const activeTab = ref('chat')
const tabs = [
  { key: 'chat', label: 'AI对话', icon: '💬' },
  { key: 'todo', label: '待办', icon: '📋' }
]

const currentUserLabel = computed(() => {
  const names = ['张三', '李四', '王五']
  return names[(props.currentUserId || 1) - 1] || `#${props.currentUserId || 1}`
})

const switchTab = (key) => {
  activeTab.value = key
  if (key === 'todo' && mergedTodos.value.length === 0) {
    loadAllTodos()
  }
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

const showQuickBubbles = computed(() => !hasUserSentMessage.value)

// Quick prompt bubbles - click to fill input (not send)
const quickBubbles = [
  { label: '📄 总结文件内容', prompt: '请帮我总结文件内容' },
  { label: '📊 生成工作报告', prompt: '帮我总结一下我本周的主要工作内容' },
  { label: '📋 查看待办列表', prompt: '查看我的待办列表' },
  { label: '👥 查看联系人', prompt: '查看联系人列表' },
  { label: '💬 查看最近消息', prompt: '查看最近消息' }
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

  let prompt = userMsg
  if (localContext.value) {
    const ctx = localContext.value
    prompt = `消息内容来自${ctx.sender_name}：「${ctx.content}」\n用户问题：${userMsg}`
  }

  aiMessages.value.push({ role: 'user', content: userMsg })
  aiInput.value = ''
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
    source_name: t.group_name || t.peer_name || ''
  }))
  const emailItems = emailTodos.value.map(t => ({
    uid: `email-${t.id}`,
    id: t.id,
    type: 'email',
    content: t.content || t.subject,
    deadline: t.deadline,
    status: t.status,
    source_type: 'email',
    source_name: t.subject || ''
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
</style>
