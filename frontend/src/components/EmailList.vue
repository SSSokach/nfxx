<template>
  <div class="sidebar email-sidebar" @click="closeContextMenu">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <div class="sidebar-brand-mark">AI</div>
        <div class="sidebar-brand-text">
          <div class="sidebar-brand-title">AI办公助手</div>
          <div class="sidebar-brand-subtitle">邮件 · 收件箱 / 已发送 / 写邮件</div>
        </div>
      </div>
      <div class="view-toggle-row">
        <button
          class="view-toggle-btn"
          :class="{ active: viewMode === 'messages' }"
          @click="switchView('messages')"
        >💬 消息</button>
        <button
          class="view-toggle-btn"
          :class="{ active: viewMode === 'emails' }"
          @click="switchView('emails')"
        >✉️ 邮箱</button>
      </div>
      <div class="user-switcher">
        <span>当前用户</span>
        <select v-model="currentUserId" @change="handleUserChange">
          <option v-for="user in users" :key="user.id" :value="user.id">{{ user.name }}</option>
        </select>
      </div>
      <div class="sidebar-meta">
        <div class="sidebar-meta-card">
          <span class="sidebar-meta-label">邮件数</span>
          <span class="sidebar-meta-value">{{ emails.length }}</span>
        </div>
        <div class="sidebar-meta-card">
          <span class="sidebar-meta-label">当前身份</span>
          <span class="sidebar-meta-value">{{ currentUserName }}</span>
        </div>
      </div>
    </div>

    <!-- 邮件夹切换 -->
    <div class="email-folders">
      <div
        v-for="f in folders"
        :key="f.key"
        class="email-folder-tab"
        :class="{ active: activeFolder === f.key }"
        @click="switchFolder(f.key)"
      >
        <span class="email-folder-icon">{{ f.icon }}</span>
        <span class="email-folder-label">{{ f.label }}</span>
        <span class="email-folder-count" v-if="f.key !== 'compose'">{{ folderCount(f.key) }}</span>
      </div>
    </div>

    <!-- 邮件列表 -->
    <div class="contacts-list email-list" v-if="activeFolder !== 'compose'">
      <div v-if="loading" class="pane-empty">加载中...</div>
      <div v-else-if="emails.length === 0" class="pane-empty">暂无邮件</div>
      <div
        v-for="email in emails"
        :key="email.id"
        class="contact-item email-item"
        :class="{ active: selectedEmailId === email.id }"
        @click="selectEmail(email)"
        @contextmenu.prevent="showContextMenu($event, email)"
      >
        <div class="avatar">{{ folderIcon(email) }}</div>
        <div class="contact-info">
          <div class="contact-name">
            {{ email.subject }}
            <span v-if="email.body_type === 'markdown'" class="md-badge">M</span>
            <span v-if="email.has_attachments" class="att-badge">📎</span>
          </div>
          <div class="contact-last-message">
            <span class="email-sender">{{ email.sender }}</span>
            · <span class="email-preview">{{ preview(email.content) }}</span>
          </div>
        </div>
        <div class="contact-time">{{ formatTime(email.sent_at) }}</div>
      </div>
    </div>

    <!-- 写邮件入口提示 -->
    <div class="compose-hint" v-else>
      <div class="compose-hint-icon">✍️</div>
      <div class="compose-hint-title">写新邮件</div>
      <div class="compose-hint-desc">在右侧编辑邮件内容，支持 Markdown 与附件</div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      @click.stop
    >
      <div class="context-menu-item" @click="handleAiChat">
        <span class="menu-icon">🤖</span><span>AI对话</span>
      </div>
      <div class="context-menu-item" @click="handleAddTodo">
        <span class="menu-icon">📋</span><span>加入待办</span>
      </div>
    </div>

    <!-- Toast -->
    <transition name="toast">
      <div class="toast" v-if="toast.visible">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { usersApi, emailsApi } from '../api'

const emit = defineEmits(['user-change', 'email-select', 'compose-trigger', 'ai-chat', 'todo-created', 'view-change'])

const props = defineProps({
  currentUserId: { type: Number, default: 1 },
  refreshKey: { type: Number, default: 0 },
  viewMode: { type: String, default: 'emails' },
  externalSelectedId: { type: Number, default: null }
})

const users = ref([])
const currentUserId = ref(props.currentUserId)
const emails = ref([])
const loading = ref(false)
const activeFolder = ref('inbox')
const selectedEmailId = ref(null)
const contextMenu = ref({ visible: false, x: 0, y: 0, email: null })
const toast = ref({ visible: false, message: '' })

const folders = [
  { key: 'inbox', label: '收件箱', icon: '📥' },
  { key: 'sent', label: '已发送', icon: '📤' },
  { key: 'compose', label: '写邮件', icon: '✍️' }
]

const currentUserName = computed(() => {
  const u = users.value.find(item => item.id === Number(currentUserId.value))
  return u ? u.name : '未选择'
})

const showToast = (msg) => {
  toast.value = { visible: true, message: msg }
  setTimeout(() => { toast.value.visible = false }, 2000)
}

const loadUsers = async () => {
  const res = await usersApi.getAll()
  users.value = res.data
}

const loadEmails = async () => {
  loading.value = true
  try {
    const res = await emailsApi.getList(currentUserId.value, activeFolder.value)
    emails.value = res.data || []
    // 自动选第一封
    if (emails.value.length > 0 && activeFolder.value !== 'compose') {
      if (!selectedEmailId.value || !emails.value.find(e => e.id === selectedEmailId.value)) {
        selectEmail(emails.value[0])
      }
    } else if (emails.value.length === 0) {
      selectedEmailId.value = null
      emit('email-select', null)
    }
  } catch (e) {
    showToast('加载邮件失败')
  }
  loading.value = false
}

const switchFolder = (folder) => {
  activeFolder.value = folder
  selectedEmailId.value = null
  if (folder === 'compose') {
    emit('compose-trigger', true)
    emit('email-select', null)
  } else {
    emit('compose-trigger', false)
    loadEmails()
  }
}

const selectEmail = (email) => {
  selectedEmailId.value = email.id
  emit('email-select', email)
}

const handleUserChange = () => {
  selectedEmailId.value = null
  emit('user-change', currentUserId.value)
  if (activeFolder.value !== 'compose') loadEmails()
}

const switchView = (mode) => {
  if (mode !== props.viewMode) emit('view-change', mode)
}

const folderCount = (folder) => {
  if (folder === activeFolder.value) return emails.value.length
  return ''
}

const folderIcon = (email) => {
  if (email.is_reply) return '↩'
  if (email.folder === 'sent') return '↗'
  return '✉'
}

const preview = (content) => {
  if (!content) return ''
  const text = content.replace(/[#*`>-]/g, '').replace(/\s+/g, ' ').trim()
  return text.length > 40 ? text.slice(0, 40) + '...' : text
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  }
  return `${date.getMonth() + 1}-${date.getDate()}`
}

// ===== Context menu =====
const showContextMenu = (event, email) => {
  contextMenu.value = { visible: true, x: event.clientX, y: event.clientY, email }
}

const closeContextMenu = () => {
  contextMenu.value.visible = false
}

const handleAiChat = async () => {
  const email = contextMenu.value.email
  if (!email) return
  closeContextMenu()
  // 拉取邮件详情以获取附件
  try {
    const res = await emailsApi.getDetail(email.id)
    const detail = res.data
    const attachmentsText = (detail.attachments || [])
      .map(a => `【附件：${a.name}】\n${a.content}`)
      .join('\n\n')
    emit('ai-chat', {
      sender_name: `邮件：${detail.subject}`,
      content: attachmentsText ? `${detail.content}\n\n${attachmentsText}` : detail.content,
      source_type: 'email',
      source_id: detail.id
    })
    showToast('已发送到AI助手')
  } catch (e) {
    showToast('加载邮件详情失败')
  }
}

const handleAddTodo = async () => {
  const email = contextMenu.value.email
  if (!email) return
  closeContextMenu()
  try {
    await emailsApi.addToTodo(currentUserId.value, email.id)
    showToast('已加入待办列表')
    emit('todo-created')
  } catch (e) {
    showToast('加入待办失败')
  }
}

onMounted(() => {
  loadUsers()
  loadEmails()
})

watch(() => props.currentUserId, (v) => { currentUserId.value = v })
watch(() => props.refreshKey, () => {
  if (activeFolder.value !== 'compose') loadEmails()
})

// 外部选中邮件 ID 变化时（如从待办跳转），自动选中并加载该邮件
watch(() => props.externalSelectedId, async (newId) => {
  if (newId == null) return
  // 确保在收件箱或已发送视图（非写邮件）
  if (activeFolder.value === 'compose') {
    activeFolder.value = 'inbox'
  }
  await loadEmails()
  // 在列表中查找该邮件并选中
  const target = emails.value.find(e => e.id === newId)
  if (target) {
    selectEmail(target)
  } else {
    // 列表中没有，直接通知父组件选中（详情已由父组件加载）
    selectedEmailId.value = newId
  }
})
</script>

<style scoped>
.email-sidebar {
  position: relative;
}

.view-toggle-row {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  padding: 4px;
  background: rgba(232, 238, 247, 0.7);
  border-radius: 12px;
}

.view-toggle-btn {
  flex: 1;
  padding: 8px 10px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.18s ease;
}

.view-toggle-btn:hover:not(.active) {
  color: #667eea;
  background: rgba(255, 255, 255, 0.6);
}

.view-toggle-btn.active {
  background: #ffffff;
  color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.16);
}

.email-folders {
  display: flex;
  gap: 4px;
  padding: 10px 12px 0;
  border-bottom: 1px solid rgba(226, 232, 245, 0.9);
}

.email-folder-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 6px;
  cursor: pointer;
  font-size: 13px;
  color: #6b7280;
  border-bottom: 2px solid transparent;
  transition: all 0.18s;
}

.email-folder-tab:hover {
  color: #667eea;
}

.email-folder-tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
  font-weight: 600;
}

.email-folder-icon {
  font-size: 14px;
}

.email-folder-label {
  font-size: 12px;
}

.email-folder-count {
  background: rgba(102, 126, 234, 0.12);
  color: #667eea;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 700;
}

.email-list {
  padding-top: 8px;
}

.email-item .contact-name {
  display: flex;
  align-items: center;
  gap: 4px;
}

.md-badge {
  font-size: 9px;
  padding: 1px 4px;
  background: #f3e8ff;
  color: #9333ea;
  border-radius: 3px;
  font-weight: 700;
}

.att-badge {
  font-size: 11px;
}

.email-sender {
  color: #667eea;
  font-weight: 500;
}

.email-preview {
  color: #77839b;
}

.compose-hint {
  padding: 40px 20px;
  text-align: center;
  color: #6b7280;
}

.compose-hint-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.compose-hint-title {
  font-size: 14px;
  font-weight: 600;
  color: #4a4a5e;
  margin-bottom: 4px;
}

.compose-hint-desc {
  font-size: 12px;
  color: #97a2b6;
  line-height: 1.5;
}

/* ===== Context menu ===== */
.context-menu {
  position: fixed;
  background: white;
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.12);
  padding: 6px 0;
  z-index: 2000;
  min-width: 140px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background-color: #f0f4ff;
  color: #1890ff;
}

.menu-icon {
  font-size: 15px;
}

.toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(0,0,0,0.75);
  color: white;
  padding: 10px 24px;
  border-radius: 20px;
  font-size: 14px;
  z-index: 3000;
}

.toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }
</style>
