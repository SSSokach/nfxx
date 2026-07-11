<script setup>
import { ref, onMounted, computed } from 'vue'
import { marked } from 'marked'
import { useAppStore } from '../stores/app'

const props = defineProps({
  message: Object
})

const emit = defineEmits(['close'])

const store = useAppStore()
const content = ref('')
const mode = ref('preview') // 'edit' | 'preview'
const saving = ref(false)

const renderedContent = computed(() => marked(content.value))

onMounted(() => {
  content.value = props.message.content
})

const save = async () => {
  saving.value = true
  try {
    await store.updateFileContent(props.message.id, content.value)
    emit('close')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="md-overlay" @click.self="emit('close')">
    <div class="md-editor">
      <div class="md-header">
        <div class="md-title">{{ message.file_name }}</div>
        <button class="md-close" @click="emit('close')">×</button>
      </div>
      <div class="md-toolbar">
        <button :class="{ active: mode === 'edit' }" @click="mode = 'edit'">编辑</button>
        <button :class="{ active: mode === 'preview' }" @click="mode = 'preview'">预览</button>
      </div>
      <div class="md-body">
        <textarea
          v-show="mode === 'edit'"
          v-model="content"
          class="md-textarea"
          placeholder="输入 Markdown 内容..."
        ></textarea>
        <div v-show="mode === 'preview'" class="md-preview" v-html="renderedContent"></div>
      </div>
      <div class="md-footer">
        <button class="md-btn-cancel" @click="emit('close')">取消</button>
        <button class="md-btn-save" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.md-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.md-editor {
  width: 720px;
  max-width: 90vw;
  height: 540px;
  max-height: 80vh;
  background: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.md-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
}

.md-title {
  font-size: 15px;
  font-weight: 600;
}

.md-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
  line-height: 1;
}

.md-toolbar {
  display: flex;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid #e8e8e8;
}

.md-toolbar button {
  padding: 4px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.md-toolbar button.active {
  background: #4a90d9;
  color: #fff;
  border-color: #4a90d9;
}

.md-body {
  flex: 1;
  overflow: hidden;
  display: flex;
}

.md-textarea {
  flex: 1;
  border: none;
  outline: none;
  padding: 16px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  width: 100%;
}

.md-preview {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  line-height: 1.7;
}

.md-preview :deep(h1) { font-size: 22px; margin: 12px 0 8px; }
.md-preview :deep(h2) { font-size: 18px; margin: 10px 0 6px; }
.md-preview :deep(h3) { font-size: 15px; margin: 8px 0 4px; }
.md-preview :deep(p) { margin: 6px 0; }
.md-preview :deep(code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 13px;
}
.md-preview :deep(pre) {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
.md-preview :deep(pre code) {
  background: none;
  padding: 0;
}
.md-preview :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.md-preview :deep(th),
.md-preview :deep(td) {
  border: 1px solid #e8e8e8;
  padding: 6px 10px;
  text-align: left;
}
.md-preview :deep(th) {
  background: #fafafa;
}

.md-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
}

.md-footer button {
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  border: 1px solid #d9d9d9;
}

.md-btn-cancel {
  background: #fff;
}

.md-btn-save {
  background: #4a90d9;
  color: #fff;
  border-color: #4a90d9;
}

.md-btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
