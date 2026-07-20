<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <div class="sidebar-brand-mark">AI</div>
        <div class="sidebar-brand-text">
          <div class="sidebar-brand-title">AI办公助手</div>
          <div class="sidebar-brand-subtitle">聊天、文件与智能协作面板</div>
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
          <span class="sidebar-meta-label">会话数</span>
          <span class="sidebar-meta-value">{{ contacts.length }}</span>
        </div>
        <div class="sidebar-meta-card">
          <span class="sidebar-meta-label">当前身份</span>
          <span class="sidebar-meta-value">{{ currentUserName }}</span>
        </div>
      </div>
    </div>
    <div class="contacts-heading">
      <span class="contacts-heading-title">最近会话</span>
      <span class="contacts-heading-count">{{ contacts.length }}</span>
    </div>
    <div class="contacts-list">
      <div
        v-for="contact in contacts"
        :key="contact.id"
        class="contact-item"
        :class="{ active: selectedContactId === contact.id }"
        @click="selectContact(contact)"
      >
        <div class="avatar">{{ contact.is_group ? '👥' : contact.name.charAt(0) }}</div>
        <div class="contact-info">
          <div class="contact-name">{{ contact.name }} {{ contact.is_group ? '(群)' : '' }}</div>
          <div class="contact-last-message">{{ contact.last_message }}</div>
        </div>
        <div class="contact-time">{{ formatTime(contact.last_time) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { usersApi, chatsApi } from '../api'

const emit = defineEmits(['user-change', 'contact-select', 'view-change'])

const props = defineProps({
  refreshKey: { type: Number, default: 0 },
  viewMode: { type: String, default: 'messages' }
})

const users = ref([])
const contacts = ref([])
const currentUserId = ref(1)
const selectedContactId = ref(null)
const currentUserName = computed(() => {
  const user = users.value.find(item => item.id === Number(currentUserId.value))
  return user ? user.name : '未选择'
})

const loadUsers = async () => {
  const res = await usersApi.getAll()
  users.value = res.data
}

const loadContacts = async () => {
  const res = await chatsApi.getContacts(currentUserId.value)
  contacts.value = res.data
  if (contacts.value.length > 0 && !selectedContactId.value) {
    selectContact(contacts.value[0])
  }
}

const selectContact = (contact) => {
  selectedContactId.value = contact.id
  emit('contact-select', contact)
}

const handleUserChange = () => {
  selectedContactId.value = null
  emit('user-change', currentUserId.value)
  loadContacts()
}

const switchView = (mode) => {
  if (mode !== props.viewMode) emit('view-change', mode)
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

onMounted(() => {
  loadUsers()
  loadContacts()
})

watch(currentUserId, loadContacts)
watch(() => props.refreshKey, () => {
  loadContacts()
})
</script>

<style scoped>
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
</style>
