<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="user-switcher">
        <span>当前用户:</span>
        <select v-model="currentUserId" @change="handleUserChange">
          <option v-for="user in users" :key="user.id" :value="user.id">{{ user.name }}</option>
        </select>
      </div>
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
import { ref, onMounted, watch } from 'vue'
import { usersApi, chatsApi } from '../api'

const emit = defineEmits(['user-change', 'contact-select'])

const props = defineProps({
  refreshKey: { type: Number, default: 0 }
})

const users = ref([])
const contacts = ref([])
const currentUserId = ref(1)
const selectedContactId = ref(null)

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
