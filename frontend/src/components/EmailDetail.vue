<template>
  <div class="chat-area email-detail-area">
    <!-- 写邮件模式 -->
    <div v-if="composeMode" class="compose-pane">
      <div class="chat-header compose-header">
        <div class="avatar">✍️</div>
        <div>
          <div class="contact-name">写新邮件</div>
          <div class="contact-status">支持 Markdown 内容与附件</div>
        </div>
        <div class="compose-header-actions">
          <button class="compose-btn ghost" @click="cancelCompose">取消</button>
          <button class="compose-btn primary" :disabled="sending || !form.to || !form.subject" @click="sendEmail">
            {{ sending ? '发送中...' : '发送' }}
          </button>
        </div>
      </div>

      <div class="compose-form">
        <div class="compose-field">
          <label>收件人</label>
          <div class="recipient-picker">
            <input
              type="text"
              v-model="form.to"
              placeholder="点击下拉选择或手动输入"
              @focus="showRecipientDropdown = true"
              @blur="hideRecipientDropdown"
              @input="filterRecipients"
            />
            <button type="button" class="recipient-toggle" @click="showRecipientDropdown = !showRecipientDropdown">▼</button>
            <div class="recipient-dropdown" v-if="showRecipientDropdown && filteredRecipients.length">
              <div
                v-for="user in filteredRecipients"
                :key="user.id"
                class="recipient-option"
                @mousedown.prevent="selectRecipient(user)"
              >
                <span class="recipient-name">{{ user.name }}</span>
                <span class="recipient-email">{{ user.email || user.name + '@company.com' }}</span>
              </div>
              <div v-if="filteredRecipients.length === 0" class="recipient-empty">无匹配联系人</div>
            </div>
          </div>
        </div>
        <div class="compose-field">
          <label>主题</label>
          <input type="text" v-model="form.subject" placeholder="邮件主题" />
        </div>
        <div class="compose-field">
          <label>内容类型</label>
          <div class="body-type-row">
            <button class="body-type-btn" :class="{ active: form.body_type === 'markdown' }" @click="form.body_type = 'markdown'">Markdown</button>
            <button class="body-type-btn" :class="{ active: form.body_type === 'text' }" @click="form.body_type = 'text'">纯文本</button>
            <span class="body-type-hint" v-if="form.body_type === 'markdown'">支持 # 标题、列表、代码块等</span>
          </div>
        </div>
        <div class="compose-field compose-body-field">
          <label>正文</label>
          <div class="compose-body-wrap">
            <textarea
              class="compose-body"
              v-model="form.content"
              :placeholder="form.body_type === 'markdown' ? '# 邮件标题\n\n正文内容...' : '请输入邮件正文...'"
            ></textarea>
            <div class="compose-preview" v-if="form.body_type === 'markdown' && form.content">
              <div class="compose-preview-title">预览</div>
              <div class="markdown-content" v-html="renderMarkdown(form.content)"></div>
            </div>
          </div>
        </div>

        <!-- 附件 -->
        <div class="compose-field">
          <label>附件</label>
          <div class="attach-row">
            <button class="attach-btn" @click="showFilePicker = true">📎 添加附件</button>
            <span class="attach-count" v-if="form.attachment_file_ids.length">{{ form.attachment_file_ids.length }} 个附件</span>
          </div>
          <div class="attach-list" v-if="selectedAttachments.length">
            <div v-for="f in selectedAttachments" :key="f.id" class="attach-item">
              <span class="attach-icon">📄</span>
              <span class="attach-name">{{ f.name }}</span>
              <span class="attach-type">{{ f.file_type }}</span>
              <button class="attach-remove" @click="removeAttachment(f.id)">×</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 邮件详情模式 -->
    <div v-else-if="email" class="detail-pane">
      <div class="chat-header detail-header">
        <div class="avatar">{{ email.is_reply ? '↩' : (email.folder === 'sent' ? '↗' : '✉') }}</div>
        <div style="flex:1; min-width:0;">
          <div class="contact-name">{{ email.subject }}</div>
          <div class="detail-meta-row">
            <span class="detail-meta-item"><strong>发件人：</strong>{{ email.sender }}</span>
            <span class="detail-meta-item" v-if="email.sender_dept"><strong>部门：</strong>{{ email.sender_dept }}</span>
          </div>
          <div class="detail-meta-row">
            <span class="detail-meta-item" v-if="email.recipients"><strong>收件人：</strong>{{ email.recipients }}</span>
            <span class="detail-meta-item"><strong>时间：</strong>{{ formatTime(email.sent_at) }}</span>
          </div>
        </div>
        <div class="detail-actions">
          <button class="compose-btn ghost" @click="replyEmail" v-if="email.folder === 'inbox'">回复</button>
          <button class="compose-btn ghost" @click="forwardEmail">转发</button>
        </div>
      </div>

      <div class="detail-body">
        <div v-if="email.body_type === 'markdown'" class="markdown-content detail-markdown" v-html="renderMarkdown(email.content)"></div>
        <pre v-else class="detail-text">{{ email.content }}</pre>

        <div v-if="email.attachments && email.attachments.length" class="detail-attachments">
          <div class="detail-attachments-title">附件 ({{ email.attachments.length }})</div>
          <div
            v-for="att in email.attachments"
            :key="att.id"
            class="attach-item attach-clickable"
            @click="previewAttachment(att)"
          >
            <span class="attach-icon">📄</span>
            <span class="attach-name">{{ att.name }}</span>
            <span class="attach-type">{{ att.file_type }}</span>
            <span class="attach-size">{{ formatSize(att.size) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-pane">
      <div class="empty-icon">📭</div>
      <div class="empty-text">请从左侧选择一封邮件查看详情</div>
    </div>

    <!-- 附件预览弹窗 -->
    <div class="file-preview-modal" v-if="previewAttachmentData" @click.self="previewAttachmentData = null">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">{{ previewAttachmentData.name }}</div>
          <button class="file-preview-close" @click="previewAttachmentData = null">×</button>
        </div>
        <div class="file-preview-body">
          <div class="markdown-content" v-html="renderMarkdown(previewAttachmentData.content)"></div>
        </div>
      </div>
    </div>

    <!-- 文件选择器 -->
    <div class="file-preview-modal" v-if="showFilePicker" @click.self="showFilePicker = false">
      <div class="file-preview-content" style="max-width: 560px;">
        <div class="file-preview-header">
          <div class="file-preview-title">选择附件</div>
          <button class="file-preview-close" @click="showFilePicker = false">×</button>
        </div>
        <div class="file-preview-body">
          <div v-if="fileList.length === 0" class="pane-empty">没有可选文件</div>
          <div
            v-for="f in fileList"
            :key="f.id"
            class="file-pick-item"
            :class="{ selected: form.attachment_file_ids.includes(f.id) }"
            @click="toggleAttachment(f)"
          >
            <span class="attach-icon">📄</span>
            <span class="attach-name">{{ f.name }}</span>
            <span class="attach-type">{{ f.file_type }}</span>
            <span class="check-mark" v-if="form.attachment_file_ids.includes(f.id)">✓</span>
          </div>
        </div>
        <div class="file-preview-actions">
          <button class="file-action-btn secondary" @click="showFilePicker = false">完成</button>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <transition name="toast">
      <div class="toast" v-if="toast.visible">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { emailsApi, filesApi, usersApi } from '../api'
import { marked } from 'marked'

marked.setOptions({ breaks: true })

const props = defineProps({
  email: { type: Object, default: null },
  composeMode: { type: Boolean, default: false },
  currentUserId: { type: Number, default: 1 }
})

const emit = defineEmits(['compose-cancel', 'email-sent'])

const form = ref({
  to: '',
  subject: '',
  content: '',
  body_type: 'markdown',
  attachment_file_ids: []
})

const sending = ref(false)
const fileList = ref([])
const showFilePicker = ref(false)
const previewAttachmentData = ref(null)
const toast = ref({ visible: false, message: '' })

// ===== 收件人下拉选择 =====
const userList = ref([])
const showRecipientDropdown = ref(false)
const recipientFilter = ref('')
const filteredRecipients = computed(() => {
  const keyword = (recipientFilter.value || form.value.to || '').trim().toLowerCase()
  const candidates = userList.value.filter(u => u.id !== props.currentUserId)
  if (!keyword) return candidates
  return candidates.filter(u =>
    (u.name || '').toLowerCase().includes(keyword) ||
    (u.email || '').toLowerCase().includes(keyword)
  )
})

const loadUserList = async () => {
  try {
    const res = await usersApi.getAll()
    userList.value = (res.data || res).filter(u => u.id !== props.currentUserId)
  } catch (e) {
    userList.value = []
  }
}

const selectRecipient = (user) => {
  const email = user.email || `${user.name}@company.com`
  form.value.to = `${user.name} <${email}>`
  showRecipientDropdown.value = false
  recipientFilter.value = ''
}

const filterRecipients = () => {
  recipientFilter.value = form.value.to
  showRecipientDropdown.value = true
}

const hideRecipientDropdown = () => {
  // 延迟关闭，让 mousedown 选择能先触发
  setTimeout(() => { showRecipientDropdown.value = false }, 200)
}

const selectedAttachments = computed(() =>
  fileList.value.filter(f => form.value.attachment_file_ids.includes(f.id))
)

const showToast = (msg) => {
  toast.value = { visible: true, message: msg }
  setTimeout(() => { toast.value.visible = false }, 2000)
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text)
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const d = new Date(timeStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const loadFileList = async () => {
  try {
    const res = await filesApi.getList(props.currentUserId)
    fileList.value = res.data || []
  } catch (e) {}
}

const toggleAttachment = (f) => {
  const idx = form.value.attachment_file_ids.indexOf(f.id)
  if (idx >= 0) {
    form.value.attachment_file_ids.splice(idx, 1)
  } else {
    form.value.attachment_file_ids.push(f.id)
  }
}

const removeAttachment = (id) => {
  const idx = form.value.attachment_file_ids.indexOf(id)
  if (idx >= 0) form.value.attachment_file_ids.splice(idx, 1)
}

const previewAttachment = (att) => {
  previewAttachmentData.value = att
}

const cancelCompose = () => {
  form.value = { to: '', subject: '', content: '', body_type: 'markdown', attachment_file_ids: [] }
  emit('compose-cancel')
}

const sendEmail = async () => {
  if (!form.value.to || !form.value.subject || sending.value) return
  sending.value = true
  try {
    await emailsApi.send(props.currentUserId, form.value)
    showToast('邮件已发送')
    cancelCompose()
    emit('email-sent')
  } catch (e) {
    showToast('发送失败')
  }
  sending.value = false
}

const replyEmail = () => {
  if (!props.email) return
  emit('compose-cancel') // 通知父组件切换到 compose
  // 父组件需要将 composeMode 设为 true 后才能填充表单
  setTimeout(() => {
    form.value = {
      to: props.email.sender,
      subject: `Re: ${props.email.subject}`,
      content: `\n\n--- 原邮件 ---\n${props.email.content}`,
      body_type: props.email.body_type || 'markdown',
      attachment_file_ids: []
    }
  }, 50)
}

const forwardEmail = () => {
  if (!props.email) return
  emit('compose-cancel')
  setTimeout(() => {
    form.value = {
      to: '',
      subject: `Fwd: ${props.email.subject}`,
      content: `\n\n--- 转发邮件 ---\n发件人：${props.email.sender}\n主题：${props.email.subject}\n\n${props.email.content}`,
      body_type: props.email.body_type || 'markdown',
      attachment_file_ids: (props.email.attachment_file_ids || []).slice()
    }
  }, 50)
}

watch(() => props.composeMode, (v) => {
  if (v) {
    loadFileList()
    loadUserList()
    if (!form.value.subject && !form.value.to && !form.value.content) {
      // 新邮件，不预填
    }
  }
})

watch(() => showFilePicker.value, (v) => {
  if (v) loadFileList()
})
</script>

<style scoped>
.compose-pane, .detail-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.compose-header, .detail-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.compose-header-actions, .detail-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.compose-btn {
  padding: 8px 16px;
  border: 1px solid rgba(216, 223, 236, 1);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background-color: #ffffff;
  color: #334155;
  transition: all 0.15s ease;
}

.compose-btn:hover:not(:disabled) {
  border-color: #4d7fff;
  color: #4d7fff;
}

.compose-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.compose-btn.primary {
  background: linear-gradient(135deg, #478cff 0%, #2e67ee 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 10px 22px rgba(57, 113, 245, 0.18);
}

.compose-btn.primary:hover:not(:disabled) {
  opacity: 0.94;
  transform: translateY(-1px);
}

.compose-form {
  flex: 1;
  overflow-y: auto;
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.compose-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.compose-field > label {
  font-size: 12px;
  font-weight: 600;
  color: #5d6982;
}

.compose-field input[type="text"] {
  padding: 11px 14px;
  border: 1px solid rgba(210, 220, 235, 1);
  border-radius: 12px;
  font-size: 14px;
  background: #ffffff;
  outline: none;
  transition: all 0.18s ease;
}

.compose-field input[type="text"]:focus {
  border-color: #4d7fff;
  box-shadow: 0 0 0 4px rgba(77, 127, 255, 0.12);
}

/* ===== 收件人下拉选择 ===== */
.recipient-picker {
  position: relative;
}
.recipient-picker input {
  width: 100%;
  padding-right: 36px !important;
}
.recipient-toggle {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 10px;
  color: #94a3b8;
  padding: 4px;
}
.recipient-toggle:hover {
  color: #4d7fff;
}
.recipient-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 240px;
  overflow-y: auto;
  background: #ffffff;
  border: 1px solid rgba(210, 220, 235, 1);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  z-index: 100;
}
.recipient-option {
  padding: 10px 14px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(240, 242, 245, 1);
  transition: background 0.15s ease;
}
.recipient-option:last-child {
  border-bottom: none;
}
.recipient-option:hover {
  background: rgba(77, 127, 255, 0.06);
}
.recipient-name {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
}
.recipient-email {
  font-size: 11px;
  color: #94a3b8;
}
.recipient-empty {
  padding: 12px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

.body-type-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.body-type-btn {
  padding: 6px 14px;
  border: 1px solid rgba(210, 220, 235, 1);
  border-radius: 10px;
  background: #ffffff;
  font-size: 12px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.15s;
}

.body-type-btn.active {
  background: #667eea;
  color: white;
  border-color: transparent;
}

.body-type-hint {
  font-size: 11px;
  color: #97a2b6;
}

.compose-body-field {
  flex: 1;
  min-height: 0;
}

.compose-body-wrap {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 300px;
}

.compose-body {
  flex: 1;
  padding: 14px 16px;
  border: 1px solid rgba(210, 220, 235, 1);
  border-radius: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.7;
  resize: none;
  background: #fbfcff;
  outline: none;
  transition: all 0.18s ease;
  min-height: 300px;
}

.compose-body:focus {
  border-color: #4d7fff;
  box-shadow: 0 0 0 4px rgba(77, 127, 255, 0.12);
}

.compose-preview {
  flex: 1;
  padding: 14px 16px;
  border: 1px solid rgba(226, 232, 245, 0.9);
  border-radius: 12px;
  background: #fafbff;
  overflow-y: auto;
}

.compose-preview-title {
  font-size: 11px;
  font-weight: 600;
  color: #97a2b6;
  margin-bottom: 8px;
}

.attach-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.attach-btn {
  padding: 8px 14px;
  border: 1px dashed rgba(102, 126, 234, 0.5);
  border-radius: 10px;
  background: #f5f3ff;
  color: #667eea;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.attach-btn:hover {
  background: #ece8ff;
  border-color: #667eea;
}

.attach-count {
  font-size: 12px;
  color: #97a2b6;
}

.attach-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attach-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e8eaf0;
  border-radius: 8px;
  font-size: 13px;
}

.attach-clickable {
  cursor: pointer;
  transition: all 0.15s;
}

.attach-clickable:hover {
  background: #f0f4ff;
  border-color: #667eea;
}

.attach-icon {
  font-size: 14px;
}

.attach-name {
  flex: 1;
  color: #1f2937;
  font-weight: 500;
}

.attach-type {
  font-size: 11px;
  padding: 1px 6px;
  background: #eef0f5;
  color: #6b7280;
  border-radius: 4px;
}

.attach-size {
  font-size: 11px;
  color: #97a2b6;
}

.attach-remove {
  border: none;
  background: none;
  font-size: 16px;
  cursor: pointer;
  color: #97a2b6;
  padding: 0 4px;
}

.attach-remove:hover {
  color: #ef4444;
}

/* ===== Detail view ===== */
.detail-meta-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.detail-meta-item {
  font-size: 12px;
  color: #6b7280;
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 22px 26px;
}

.detail-markdown {
  background: #ffffff;
  padding: 18px 22px;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 245, 0.9);
  box-shadow: 0 10px 22px rgba(148, 160, 186, 0.08);
}

.detail-text {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
  background: #ffffff;
  padding: 18px 22px;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 245, 0.9);
}

.detail-attachments {
  margin-top: 22px;
}

.detail-attachments-title {
  font-size: 13px;
  font-weight: 600;
  color: #4a4a5e;
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 3px solid #667eea;
}

/* ===== Empty state ===== */
.empty-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #97a2b6;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
}

/* ===== File picker ===== */
.file-pick-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 1px solid #e8eaf0;
  border-radius: 10px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.file-pick-item:hover {
  background: #f0f4ff;
  border-color: #667eea;
}

.file-pick-item.selected {
  background: #f5f3ff;
  border-color: #667eea;
}

.file-pick-item .attach-name {
  flex: 1;
}

.check-mark {
  color: #667eea;
  font-weight: 700;
  font-size: 16px;
}

/* ===== Toast ===== */
.toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(0,0,0,0.75);
  color: white;
  padding: 10px 24px;
  border-radius: 20px;
  font-size: 14px;
  z-index: 3000;
}

.toast-enter-active, .toast-leave-active { transition: opacity 0.3s; }
.toast-enter-from, .toast-leave-to { opacity: 0; }
</style>
