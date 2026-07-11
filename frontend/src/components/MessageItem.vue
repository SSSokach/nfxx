<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/app'
import MarkdownEditor from './MarkdownEditor.vue'

const props = defineProps({
  message: Object
})

const store = useAppStore()
const showEditor = ref(false)

const isMine = (msg) => msg.sender_id === store.currentUser?.id

const openEditor = () => {
  showEditor.value = true
}
</script>

<template>
  <div class="message-item" :class="{ mine: isMine(message) }">
    <div class="avatar">{{ message.sender_name?.[0] || '?' }}</div>
    <div class="message-body">
      <div class="message-meta">
        <span class="sender">{{ message.sender_name }}</span>
        <span class="time">{{ message.created_at?.slice(11, 16) }}</span>
      </div>
      <div v-if="message.msg_type === 'text'" class="message-content text">
        {{ message.content }}
      </div>
      <div v-else class="message-content file" @click="openEditor">
        <span class="file-icon">📄</span>
        <span class="file-name">{{ message.file_name }}</span>
        <span class="file-hint">点击预览/编辑</span>
      </div>
    </div>
    <MarkdownEditor v-if="showEditor" :message="message" @close="showEditor = false" />
  </div>
</template>

<style scoped>
.message-item {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  max-width: 70%;
}

.message-item.mine {
  flex-direction: row-reverse;
  margin-left: auto;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #4a90d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.message-item.mine .avatar {
  background: #52c41a;
}

.message-body {
  display: flex;
  flex-direction: column;
}

.message-item.mine .message-body {
  align-items: flex-end;
}

.message-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 4px;
}

.sender {
  font-size: 12px;
  color: #666;
}

.time {
  font-size: 11px;
  color: #aaa;
}

.message-content {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.message-content.text {
  background: #fff;
  border: 1px solid #e8e8e8;
}

.message-item.mine .message-content.text {
  background: #52c41a;
  color: #fff;
  border-color: #52c41a;
}

.message-content.file {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid #e8e8e8;
  cursor: pointer;
  transition: border-color 0.15s;
}

.message-content.file:hover {
  border-color: #4a90d9;
}

.file-icon {
  font-size: 18px;
}

.file-name {
  font-weight: 500;
  color: #333;
}

.file-hint {
  font-size: 11px;
  color: #999;
}
</style>
