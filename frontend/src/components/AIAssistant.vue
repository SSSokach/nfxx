<script setup>
import { ref, nextTick } from 'vue'
import { useAppStore } from '../stores/app'
import api from '../api'

const store = useAppStore()
const inputText = ref('')
const loading = ref(false)
const messages = ref([]) // AI 对话消息列表: { role, content, tool_calls }
const chatEnd = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatEnd.value) {
      chatEnd.value.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

const send = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const history = messages.value
      .slice(0, -1)
      .map(m => ({
        role: m.role,
        content: m.content
      }))

    const result = await api.aiChat({
      user_id: store.currentUser.id,
      message: text,
      history
    })

    messages.value.push({
      role: 'assistant',
      content: result.reply,
      tool_calls: result.tool_calls || []
    })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: 'AI 请求失败：' + (e.response?.data?.detail || e.message)
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const handleKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

const quickActions = [
  '帮我看看和{}的最近聊天记录',
  '帮我给技术讨论组发一条消息：明天上午开会',
  '帮我查看接口文档.md的内容'
]

const useQuickAction = (template) => {
  const target = store.contacts.users[0]?.name || '李四'
  inputText.value = template.replace('{}', target)
}
</script>

<template>
  <div class="ai-assistant">
    <div class="ai-header">
      <span class="ai-icon">🤖</span>
      <span class="ai-title">AI 助手</span>
    </div>

    <div class="ai-messages">
      <div v-if="messages.length === 0" class="ai-empty">
        <div class="empty-icon">🤖</div>
        <div class="empty-title">我是你的 AI 办公助手</div>
        <div class="empty-desc">我可以帮你读取聊天记录、发送消息、查看文件内容</div>
        <div class="quick-actions">
          <div class="quick-title">快捷指令：</div>
          <button
            v-for="action in quickActions"
            :key="action"
            class="quick-btn"
            @click="useQuickAction(action)"
          >{{ action }}</button>
        </div>
      </div>

      <template v-for="(msg, i) in messages" :key="i">
        <div class="ai-msg" :class="msg.role">
          <div class="ai-msg-avatar">{{ msg.role === 'user' ? (store.currentUser?.avatar) : '🤖' }}</div>
          <div class="ai-msg-body">
            <div class="ai-msg-content">{{ msg.content }}</div>
            <div v-if="msg.tool_calls && msg.tool_calls.length > 0" class="tool-calls">
              <div class="tool-calls-title">🔧 工具调用 ({{ msg.tool_calls.length }})</div>
              <div v-for="(tc, j) in msg.tool_calls" :key="j" class="tool-call-item">
                <div class="tool-name">{{ tc.name }}</div>
                <div class="tool-args">{{ tc.arguments }}</div>
                <div class="tool-result">{{ tc.result }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-if="loading" class="ai-msg assistant">
        <div class="ai-msg-avatar">🤖</div>
        <div class="ai-msg-body">
          <div class="ai-typing">思考中...</div>
        </div>
      </div>
      <div ref="chatEnd"></div>
    </div>

    <div class="ai-input-area">
      <textarea
        v-model="inputText"
        class="ai-input"
        placeholder="向 AI 助手提问..."
        @keydown="handleKeydown"
        rows="2"
      ></textarea>
      <button class="ai-send-btn" :disabled="loading || !inputText.trim()" @click="send">发送</button>
    </div>
  </div>
</template>

<style scoped>
.ai-assistant {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 56px;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.ai-icon {
  font-size: 20px;
}

.ai-title {
  font-size: 16px;
  font-weight: 600;
}

.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.ai-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 24px 16px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  color: #999;
  margin-bottom: 20px;
}

.quick-actions {
  width: 100%;
  text-align: left;
}

.quick-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.quick-btn {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  margin-bottom: 6px;
  border: 1px solid #e8e8e8;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  color: #666;
}

.quick-btn:hover {
  border-color: #4a90d9;
  color: #4a90d9;
}

.ai-msg {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.ai-msg.user {
  flex-direction: row-reverse;
}

.ai-msg-avatar {
  width: 28px;
  height: 28px;
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

.ai-msg.user .ai-msg-avatar {
  background: #52c41a;
}

.ai-msg-body {
  max-width: 80%;
}

.ai-msg.user .ai-msg-body {
  text-align: right;
}

.ai-msg-content {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-msg.assistant .ai-msg-content {
  background: #f5f5f5;
  color: #333;
}

.ai-msg.user .ai-msg-content {
  background: #4a90d9;
  color: #fff;
}

.tool-calls {
  margin-top: 8px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  overflow: hidden;
}

.tool-calls-title {
  padding: 6px 10px;
  background: #fafafa;
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.tool-call-item {
  padding: 8px 10px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
}

.tool-name {
  font-weight: 600;
  color: #4a90d9;
  margin-bottom: 4px;
}

.tool-args {
  color: #666;
  margin-bottom: 4px;
  word-break: break-all;
}

.tool-result {
  color: #999;
  word-break: break-all;
  white-space: pre-wrap;
}

.ai-typing {
  display: inline-block;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 8px;
  font-size: 13px;
  color: #999;
}

.ai-input-area {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.ai-input {
  flex: 1;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 13px;
  font-family: inherit;
  resize: none;
  outline: none;
  max-height: 100px;
}

.ai-input:focus {
  border-color: #4a90d9;
}

.ai-send-btn {
  padding: 8px 16px;
  background: #4a90d9;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.ai-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
