<template>
  <div id="app">
    <div class="app-shell">
      <div class="app-main">
        <!-- 消息视图 -->
        <template v-if="viewMode === 'messages'">
          <ContactList
            :refresh-key="refreshKey"
            :view-mode="viewMode"
            @user-change="handleUserChange"
            @contact-select="handleContactSelect"
            @view-change="handleViewChange"
          />
          <div class="chat-area-wrap">
            <ChatArea
              :selected-contact="selectedContact"
              :current-user-id="currentUserId"
              :current-user="currentUser"
              :highlight-message-id="highlightMessageId"
              @message-sent="handleMessageSent"
              @ai-chat="handleAiChat"
              @todo-created="handleTodoCreated"
              @scroll-to-message="handleScrollToMessage"
            />
          </div>
        </template>

        <!-- 邮箱视图 -->
        <template v-else>
          <EmailList
            :current-user-id="currentUserId"
            :refresh-key="emailRefreshKey"
            :view-mode="viewMode"
            @user-change="handleUserChange"
            @email-select="handleEmailSelect"
            @compose-trigger="handleComposeTrigger"
            @ai-chat="handleAiChat"
            @todo-created="handleTodoCreated"
            @view-change="handleViewChange"
          />
          <EmailDetail
            :email="selectedEmailDetail"
            :compose-mode="composeMode"
            :current-user-id="currentUserId"
            @compose-cancel="handleComposeCancel"
            @email-sent="handleEmailSent"
          />
        </template>

        <!-- AI Panel：与视图解耦，开关状态不随 messages/emails 切换而改变 -->
        <transition name="slide-ai">
          <AIPanel
            v-show="aiPanelVisible"
            :current-user-id="currentUserId"
            :context-message="aiContextMessage"
            :todo-refresh-key="todoRefreshKey"
            :width="aiPanelWidth"
            @resize="handleAiPanelResize"
            @jump-to-message="handleJumpToMessage"
            @jump-to-email="handleJumpToEmail"
            @close="aiPanelVisible = false"
          />
        </transition>

        <!-- 展开右侧 AI 面板的按钮（固定在右上角，两个视图都可见） -->
        <button
          v-if="!aiPanelVisible"
          class="ai-toggle-btn"
          title="打开 AI 助手"
          @click="openAIPanel"
        >
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z" fill="currentColor"/>
            <circle cx="19" cy="5" r="1.5" fill="currentColor" opacity="0.6"/>
            <circle cx="5" cy="19" r="1" fill="currentColor" opacity="0.4"/>
          </svg>
          <span class="ai-toggle-btn-label">AI</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import ContactList from './components/ContactList.vue'
import ChatArea from './components/ChatArea.vue'
import EmailList from './components/EmailList.vue'
import EmailDetail from './components/EmailDetail.vue'
import AIPanel from './components/AIPanel.vue'
import { emailsApi, chatsApi } from './api'

const currentUserId = ref(1)
const currentUser = ref({ id: 1, name: '张三' })
const selectedContact = ref(null)
const refreshKey = ref(0)
const emailRefreshKey = ref(0)
const aiContextMessage = ref(null)
const todoRefreshKey = ref(0)
const aiPanelVisible = ref(false)
const highlightMessageId = ref(null)

// ===== AI Panel width (user-resizable, persisted) =====
const AI_PANEL_MIN_WIDTH = 280
const AI_PANEL_MAX_WIDTH = 720
const AI_PANEL_DEFAULT_WIDTH = 360
const AI_PANEL_WIDTH_KEY = 'aiPanelWidth'
const readStoredWidth = () => {
  if (typeof window === 'undefined') return AI_PANEL_DEFAULT_WIDTH
  const raw = window.localStorage.getItem(AI_PANEL_WIDTH_KEY)
  const n = raw ? parseInt(raw, 10) : NaN
  if (isNaN(n)) return AI_PANEL_DEFAULT_WIDTH
  return Math.max(AI_PANEL_MIN_WIDTH, Math.min(AI_PANEL_MAX_WIDTH, n))
}
const aiPanelWidth = ref(readStoredWidth())
const handleAiPanelResize = (width) => {
  const clamped = Math.max(AI_PANEL_MIN_WIDTH, Math.min(AI_PANEL_MAX_WIDTH, width))
  aiPanelWidth.value = clamped
  try { window.localStorage.setItem(AI_PANEL_WIDTH_KEY, String(clamped)) } catch {}
}

// 视图模式：messages / emails
const viewMode = ref('messages')

// 邮箱视图状态
const selectedEmail = ref(null)
const selectedEmailDetail = ref(null)
const composeMode = ref(false)

const handleUserChange = (userId) => {
  currentUserId.value = userId
  const names = ['张三', '李四', '王五']
  currentUser.value = { id: userId, name: names[userId - 1] || '用户' }
  // 重置邮箱选中状态
  selectedEmail.value = null
  selectedEmailDetail.value = null
}

const handleContactSelect = (contact) => {
  selectedContact.value = contact
}

const handleMessageSent = () => {
  refreshKey.value++
}

const handleAiChat = (message) => {
  // 消息和邮件共用同一个 aiContextMessage 通道
  aiContextMessage.value = message
  aiPanelVisible.value = true
}

const handleTodoCreated = () => {
  todoRefreshKey.value++
}

const handleViewChange = (mode) => {
  viewMode.value = mode
  // 切换时清空选中状态
  if (mode === 'emails') {
    selectedContact.value = null
  } else {
    selectedEmail.value = null
    selectedEmailDetail.value = null
    composeMode.value = false
  }
}

// ===== 邮箱视图事件 =====
const handleEmailSelect = async (email) => {
  selectedEmail.value = email
  if (!email) {
    selectedEmailDetail.value = null
    return
  }
  // 选中邮件时退出写邮件模式
  composeMode.value = false
  try {
    const res = await emailsApi.getDetail(email.id)
    selectedEmailDetail.value = res.data
  } catch (e) {
    selectedEmailDetail.value = email
  }
}

const handleComposeTrigger = (isCompose) => {
  composeMode.value = isCompose
  if (isCompose) {
    selectedEmailDetail.value = null
  }
}

const handleComposeCancel = () => {
  composeMode.value = false
  // 切回收件箱视图（如果当前是写邮件 tab）
}

const handleEmailSent = () => {
  // 邮件发送后刷新列表并切回已发送
  emailRefreshKey.value++
  composeMode.value = false
}

const openAIPanel = () => {
  aiPanelVisible.value = true
}

// ===== Jump to message from todo =====
const handleJumpToMessage = async ({ contact_id, message_id }) => {
  // 切换到对应联系人会话
  if (!selectedContact.value || selectedContact.value.id !== contact_id) {
    try {
      const res = await chatsApi.getContacts(currentUserId.value)
      const contacts = res.data || res
      const contact = contacts.find(c => c.id === contact_id)
      if (contact) {
        selectedContact.value = contact
      } else {
        selectedContact.value = { id: contact_id, name: '', is_group: false }
      }
    } catch {
      selectedContact.value = { id: contact_id, name: '', is_group: false }
    }
  }
  // 等待消息列表加载完成（异步请求 + DOM 渲染）
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 600))
  highlightMessageId.value = message_id
}

const handleJumpToEmail = () => {
  // Email preview is handled inside AIPanel itself
}

const handleScrollToMessage = (msgId) => {
  highlightMessageId.value = msgId
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Segoe UI', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif; }

#app {
  height: 100vh;
  overflow: hidden;
  background: #f0f2f5;
}

.app-shell {
  height: 100%;
  display: flex;
}

.app-main {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.chat-area-wrap {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

/* ===== AI Panel slide animation ===== */
.slide-ai-enter-active,
.slide-ai-leave-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease;
}
.slide-ai-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.slide-ai-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

/* ===== 右上角 AI 助手展开按钮 ===== */
.ai-toggle-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  background: #ffffff;
  color: #3b82f6;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.12), 0 1px 3px rgba(0, 0, 0, 0.04);
  z-index: 50;
  transition: all 0.18s ease;
  padding: 0;
}
.ai-toggle-btn:hover {
  background: #3b82f6;
  color: #ffffff;
  border-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}
.ai-toggle-btn:active {
  transform: translateY(0);
}
.ai-toggle-btn svg {
  width: 18px;
  height: 18px;
}
.ai-toggle-btn-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  line-height: 1;
}
</style>
