<script setup>
import { ref, nextTick, watch } from 'vue'
import { useAppStore } from '../stores/app'
import MessageItem from './MessageItem.vue'

const store = useAppStore()
const inputText = ref('')
const showFileInput = ref(false)
const fileName = ref('')
const fileContent = ref('')
const messagesEnd = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesEnd.value) {
      messagesEnd.value.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

watch(() => store.messages.length, scrollToBottom)

const sendText = async () => {
  const text = inputText.value.trim()
  if (!text || !store.currentChat) return
  inputText.value = ''
  await store.sendMessage(text, 'text', '')
  scrollToBottom()
}

const sendFile = async () => {
  const name = fileName.value.trim()
  const content = fileContent.value.trim()
  if (!name || !content || !store.currentChat) return
  await store.sendMessage(content, 'file', name)
  fileName.value = ''
  fileContent.value = ''
  showFileInput.value = false
  scrollToBottom()
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendText()
  }
}
</script>

<template>
  <div class="chat-area">
    <div v-if="store.currentChat" class="chat-header">
      <span class="chat-name">{{ store.currentChat.name }}</span>
      <span class="chat-type">{{ store.currentChat.type === 'group' ? '群聊' : '私聊' }}</span>
    </div>

    <div v-if="!store.currentChat" class="chat-empty">
      <div class="empty-hint">选择一个联系人或群组开始聊天</div>
    </div>

    <template v-else>
      <div class="chat-messages" ref="messagesContainer">
        <MessageItem
          v-for="msg in store.messages"
          :key="msg.id"
          :message="msg"
        />
        <div ref="messagesEnd"></div>
      </div>

      <div class="chat-input-area">
        <div v-if="showFileInput" class="file-input-box">
          <input v-model="fileName" class="file-name-input" placeholder="文件名，如：会议纪要.md" />
          <textarea v-model="fileContent" class="file-content-input" placeholder="输入 Markdown 内容..."></textarea>
          <div class="file-input-actions">
            <button class="btn-cancel" @click="showFileInput = false">取消</button>
            <button class="btn-send" @click="sendFile">发送文件</button>
          </div>
        </div>
        <div v-else class="text-input-box">
          <button class="btn-file" @click="showFileInput = true">📎 文件</button>
          <textarea
            v-model="inputText"
            class="text-input"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            @keydown="handleKeydown"
            rows="1"
          ></textarea>
          <button class="btn-send" @click="sendText">发送</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.chat-name {
  font-size: 16px;
  font-weight: 600;
}

.chat-type {
  font-size: 12px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.chat-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-hint {
  color: #999;
  font-size: 15px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-input-area {
  flex-shrink: 0;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.text-input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
}

.btn-file {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn-file:hover {
  border-color: #4a90d9;
  color: #4a90d9;
}

.text-input {
  flex: 1;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  min-height: 36px;
  max-height: 120px;
}

.text-input:focus {
  border-color: #4a90d9;
}

.btn-send {
  padding: 8px 16px;
  background: #4a90d9;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.btn-send:hover {
  background: #3a7bc8;
}

.file-input-box {
  padding: 12px 16px;
}

.file-name-input {
  width: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 14px;
  outline: none;
  margin-bottom: 8px;
}

.file-name-input:focus {
  border-color: #4a90d9;
}

.file-content-input {
  width: 100%;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: monospace;
  outline: none;
  resize: vertical;
  min-height: 100px;
  max-height: 200px;
}

.file-content-input:focus {
  border-color: #4a90d9;
}

.file-input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn-cancel {
  padding: 6px 16px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
</style>
