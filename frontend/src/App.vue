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
          <ChatArea
            :selected-contact="selectedContact"
            :current-user-id="currentUserId"
            :current-user="currentUser"
            @message-sent="handleMessageSent"
            @ai-chat="handleAiChat"
            @todo-created="handleTodoCreated"
          />
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

        <AIPanel :current-user-id="currentUserId" :context-message="aiContextMessage" :todo-refresh-key="todoRefreshKey" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ContactList from './components/ContactList.vue'
import ChatArea from './components/ChatArea.vue'
import EmailList from './components/EmailList.vue'
import EmailDetail from './components/EmailDetail.vue'
import AIPanel from './components/AIPanel.vue'
import { emailsApi } from './api'

const currentUserId = ref(1)
const currentUser = ref({ id: 1, name: '张三' })
const selectedContact = ref(null)
const refreshKey = ref(0)
const emailRefreshKey = ref(0)
const aiContextMessage = ref(null)
const todoRefreshKey = ref(0)

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
</script>
