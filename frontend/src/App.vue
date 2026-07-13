<template>
  <div id="app">
    <ContactList 
      :refresh-key="refreshKey"
      @user-change="handleUserChange" 
      @contact-select="handleContactSelect" 
    />
    <ChatArea 
      :selected-contact="selectedContact" 
      :current-user-id="currentUserId"
      :current-user="currentUser"
      @message-sent="handleMessageSent"
      @ai-chat="handleAiChat"
    />
    <AIPanel :current-user-id="currentUserId" :context-message="aiContextMessage" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ContactList from './components/ContactList.vue'
import ChatArea from './components/ChatArea.vue'
import AIPanel from './components/AIPanel.vue'

const currentUserId = ref(1)
const currentUser = ref({ id: 1, name: '张三' })
const selectedContact = ref(null)
const refreshKey = ref(0)
const aiContextMessage = ref(null)

const handleUserChange = (userId) => {
  currentUserId.value = userId
  const names = ['张三', '李四', '王五']
  currentUser.value = { id: userId, name: names[userId - 1] || '用户' }
}

const handleContactSelect = (contact) => {
  selectedContact.value = contact
}

const handleMessageSent = () => {
  refreshKey.value++
}

const handleAiChat = (message) => {
  aiContextMessage.value = message
}
</script>
