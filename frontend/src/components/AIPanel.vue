<template>
  <div class="ai-panel">
    <div class="ai-header">
      <div class="ai-title">🤖 AI办公助手</div>
      <div class="ai-description">帮你处理日常办公事务</div>
    </div>
    <div class="ai-messages">
      <div v-for="(msg, index) in aiMessages" :key="index" class="ai-message" :class="msg.role">
        <template v-if="msg.role === 'user'">
          <strong>你:</strong> {{ msg.content }}
        </template>
        <template v-else>
          <strong>助手:</strong> {{ msg.content }}
          <div v-if="msg.result" style="margin-top: 8px; padding: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; font-size: 12px;">
            <strong>执行结果:</strong>
            <pre style="margin-top: 4px; white-space: pre-wrap;">{{ JSON.stringify(msg.result, null, 2) }}</pre>
          </div>
        </template>
      </div>
    </div>
    <div class="ai-input-area">
      <input 
        class="ai-input" 
        v-model="aiInput" 
        placeholder="请输入指令..."
        @keydown.enter.exact.prevent="sendAiMessage"
      />
      <button class="ai-send-btn" @click="sendAiMessage">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { aiApi } from '../api'

const props = defineProps({
  currentUserId: Number
})

const aiMessages = ref([
  { role: 'assistant', content: '你好！我是你的AI办公助手。我可以帮你：\n- 读取聊天记录\n- 发送消息给联系人\n- 获取文件内容\n- 查看文件列表\n- 查看联系人列表\n\n请告诉我你想做什么。' }
])
const aiInput = ref('')

const sendAiMessage = async () => {
  if (!aiInput.value.trim()) return
  
  aiMessages.value.push({ role: 'user', content: aiInput.value.trim() })
  aiInput.value = ''
  
  try {
    const res = await aiApi.chat(props.currentUserId, aiInput.value.trim())
    aiMessages.value.push({ role: 'assistant', content: res.data.response, result: res.data.result })
  } catch (error) {
    aiMessages.value.push({ role: 'assistant', content: '抱歉，我遇到了一个错误。' })
  }
}
</script>
