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
          <div ref="chatAreaWrapRef" class="chat-area-wrap">
            <ChatArea
              ref="chatAreaRef"
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
            :jump-to-email-id="jumpToEmailId"
            @user-change="handleUserChange"
            @email-select="handleEmailSelect"
            @compose-trigger="handleComposeTrigger"
            @ai-chat="handleAiChat"
            @todo-created="handleTodoCreated"
            @view-change="handleViewChange"
            @jump-completed="handleJumpCompleted"
          />
          <div ref="emailDetailWrapRef" class="chat-area-wrap">
            <EmailDetail
              :email="selectedEmailDetail"
              :compose-mode="composeMode"
              :current-user-id="currentUserId"
              @compose-cancel="handleComposeCancel"
              @email-sent="handleEmailSent"
            />
          </div>
        </template>

        <!-- AI Panel（独立于视图，切换视图不影响） -->
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
            @message-sent="handleAiMessageSent"
            @close="aiPanelVisible = false"
          />
        </transition>

        <!-- Floating AI button (draggable + edge-hide, independent of view) -->
        <div
          v-if="!aiPanelVisible"
          ref="aiFabRef"
          class="ai-fab"
          :class="{ 'edge-hidden': isEdgeHidden, 'dragging': isDragging }"
          :style="fabStyle"
          @mousedown="onFabMouseDown"
        >
          <div class="ai-fab-pulse" v-if="!isDragging && !isEdgeHidden"></div>
          <svg class="ai-fab-svg" v-if="!isEdgeHidden" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z" fill="currentColor"/>
            <circle cx="19" cy="5" r="1.5" fill="currentColor" opacity="0.6"/>
            <circle cx="5" cy="19" r="1" fill="currentColor" opacity="0.4"/>
          </svg>
          <span class="ai-fab-label" v-if="!isEdgeHidden">AI</span>
          <span class="ai-fab-edge-label" v-if="isEdgeHidden">AI</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
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
const jumpToEmailId = ref(null)

// ===== Floating AI button: draggable + edge-hide =====
const aiFabRef = ref(null)
const chatAreaWrapRef = ref(null)
const emailDetailWrapRef = ref(null)
const fabPos = ref({ x: typeof window !== 'undefined' ? window.innerWidth - 96 : 800, y: typeof window !== 'undefined' ? window.innerHeight - 96 : 600 })
const isDragging = ref(false)
const isEdgeHidden = ref(false)
const dragState = ref({ startX: 0, startY: 0, originX: 0, originY: 0, moved: false })

const FAB_SIZE = 64
const EDGE_THRESHOLD = 50      // 距离边框小于此值视为贴边
const EDGE_HIDE_OFFSET = 36     // 贴边隐藏时露出的宽度

// 获取聊天框边界（浮动球只在聊天框范围内活动和贴边）
const getChatBounds = () => {
  if (chatAreaWrapRef.value) {
    return chatAreaWrapRef.value.getBoundingClientRect()
  }
  if (emailDetailWrapRef.value) {
    return emailDetailWrapRef.value.getBoundingClientRect()
  }
  // fallback: 整个窗口
  return { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight, width: window.innerWidth, height: window.innerHeight }
}

const initFabPos = () => {
  const b = getChatBounds()
  fabPos.value = {
    x: b.right - FAB_SIZE - 32,
    y: b.bottom - FAB_SIZE - 32
  }
}

const onFabMouseDown = (e) => {
  if (e.button !== 0) return
  e.preventDefault()  // 阻止默认行为，防止拖动时选中文本
  isDragging.value = true
  isEdgeHidden.value = false
  dragState.value = {
    startX: e.clientX,
    startY: e.clientY,
    originX: fabPos.value.x,
    originY: fabPos.value.y,
    moved: false
  }
  document.addEventListener('mousemove', onFabMouseMove)
  document.addEventListener('mouseup', onFabMouseUp)
}

const onFabMouseMove = (e) => {
  const dx = e.clientX - dragState.value.startX
  const dy = e.clientY - dragState.value.startY
  if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragState.value.moved = true
  const b = getChatBounds()
  let nx = dragState.value.originX + dx
  let ny = dragState.value.originY + dy
  // 约束在聊天框范围内
  nx = Math.max(b.left, Math.min(b.right - FAB_SIZE, nx))
  ny = Math.max(b.top, Math.min(b.bottom - FAB_SIZE, ny))
  fabPos.value = { x: nx, y: ny }
}

const onFabMouseUp = () => {
  const wasMoved = dragState.value.moved
  isDragging.value = false
  document.removeEventListener('mousemove', onFabMouseMove)
  document.removeEventListener('mouseup', onFabMouseUp)
  if (wasMoved) {
    // 拖动结束，检查贴边
    checkEdgeHide()
  } else {
    // 未移动 = 点击：贴边状态先恢复，否则打开面板
    if (isEdgeHidden.value) {
      isEdgeHidden.value = false
      const b = getChatBounds()
      fabPos.value = { x: b.right - FAB_SIZE - 32, y: b.bottom - FAB_SIZE - 32 }
    } else {
      openAIPanel()
    }
  }
}

const checkEdgeHide = () => {
  const b = getChatBounds()
  const { x, y } = fabPos.value
  // 只检查左右边，不贴上下边
  const distLeft = x - b.left
  const distRight = b.right - FAB_SIZE - x
  const minDist = Math.min(distLeft, distRight)
  if (minDist < EDGE_THRESHOLD) {
    isEdgeHidden.value = true
    // 贴到聊天框左/右内侧边缘
    if (distLeft === minDist) fabPos.value.x = b.left
    else fabPos.value.x = b.right - FAB_SIZE
  } else {
    isEdgeHidden.value = false
  }
}

const onFabClick = () => {
  // 兼容触摸/键盘点击：未拖动时唤起
  if (dragState.value.moved) return
  if (isEdgeHidden.value) {
    isEdgeHidden.value = false
    const b = getChatBounds()
    fabPos.value = { x: b.right - FAB_SIZE - 32, y: b.bottom - FAB_SIZE - 32 }
    return
  }
  openAIPanel()
}

const onResize = () => {
  const b = getChatBounds()
  const { x, y } = fabPos.value
  fabPos.value = {
    x: Math.max(b.left, Math.min(b.right - FAB_SIZE, x)),
    y: Math.max(b.top, Math.min(b.bottom - FAB_SIZE, y))
  }
  if (!isEdgeHidden.value) checkEdgeHide()
}

// 根据贴边状态决定尺寸/位置样式
const fabStyle = computed(() => {
  const b = getChatBounds()
  let w = FAB_SIZE, h = FAB_SIZE, r = '50%'
  if (isEdgeHidden.value) {
    // 贴左右边后收缩为竖条
    w = 14; h = 56; r = '8px'
  }
  return {
    left: fabPos.value.x + 'px',
    top: fabPos.value.y + 'px',
    width: w + 'px',
    height: h + 'px',
    borderRadius: r,
    right: 'auto',
    bottom: 'auto'
  }
})

onMounted(() => {
  initFabPos()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('mousemove', onFabMouseMove)
  document.removeEventListener('mouseup', onFabMouseUp)
})

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

// AI 面板触发的消息发送（如催办）→ 刷新对应会话的消息列表
const chatAreaRef = ref(null)
const handleAiMessageSent = ({ contact_id }) => {
  // 如果当前正在查看的就是被催办的会话，立即刷新消息列表
  if (selectedContact.value && selectedContact.value.id === contact_id && chatAreaRef.value) {
    chatAreaRef.value.loadMessages()
  }
  // 联系人列表的最后一条消息也需要刷新
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

const handleJumpToEmail = async ({ email_id }) => {
  if (!email_id) return
  // 切换到邮箱视图并清空旧选中状态
  viewMode.value = 'emails'
  selectedContact.value = null
  selectedEmail.value = null
  selectedEmailDetail.value = null
  composeMode.value = false
  // 等待 EmailList 挂载后再设置目标 id，确保 watch 能触发
  await nextTick()
  jumpToEmailId.value = email_id
}

const handleJumpCompleted = () => {
  jumpToEmailId.value = null
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

/* ===== 浮动 AI 按钮（可拖拽 + 贴边隐藏） ===== */
.ai-fab {
  position: fixed;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: none;
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.45), 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 999;
  user-select: none;
  -webkit-user-select: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.3s ease;
  touch-action: none;
}
.ai-fab:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 28px rgba(102, 126, 234, 0.6), 0 2px 10px rgba(0, 0, 0, 0.2);
}
.ai-fab:active {
  transform: scale(0.95);
}
.ai-fab-svg {
  width: 26px;
  height: 26px;
}
.ai-fab-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.ai-fab-pulse {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(102, 126, 234, 0.4);
  animation: aiFabPulse 2s ease-out infinite;
  pointer-events: none;
}
@keyframes aiFabPulse {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.5); opacity: 0; }
}
.ai-fab-edge-label {
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 1px;
  writing-mode: vertical-rl;
  text-orientation: upright;
  line-height: 1;
}
.ai-fab.edge-hidden {
  background: #3b82f6 !important;
  border: none !important;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(59, 130, 246, 0.4);
}
.ai-fab.edge-hidden:hover {
  opacity: 0.85;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.6);
}
</style>
