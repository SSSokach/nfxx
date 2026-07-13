<template>
  <div class="chat-area" @click="closeContextMenu">
    <div class="chat-header" v-if="selectedContact">
      <div class="avatar">{{ selectedContact.is_group ? '👥' : selectedContact.name.charAt(0) }}</div>
      <div>
        <div class="contact-name">{{ selectedContact.name }}</div>
        <div class="contact-status">{{ selectedContact.is_group ? '群聊' : '在线' }}</div>
      </div>
    </div>

    <div class="messages-container" ref="messagesContainer">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message"
        :class="{ self: message.is_self, selected: multiSelectMode && selectedMessages.includes(message.id) }"
        @contextmenu.prevent="showContextMenu($event, message)"
        @click="multiSelectMode ? toggleSelect(message.id) : null"
      >
        <div class="message-checkbox" v-if="multiSelectMode">
          <div class="checkbox-inner" :class="{ checked: selectedMessages.includes(message.id) }">
            <span v-if="selectedMessages.includes(message.id)">✓</span>
          </div>
        </div>
        <div class="message-avatar">{{ message.is_self ? currentUser.name.charAt(0) : message.sender_name.charAt(0) }}</div>
        <div class="message-body">
          <div class="message-sender" v-if="!message.is_self">{{ message.sender_name }}</div>
          <div class="reply-quote-card" v-if="message.reply_to" :class="{ self: message.is_self }">
            <div class="reply-quote-line"></div>
            <div class="reply-quote-content">
              <span class="reply-quote-name">{{ message.reply_to.sender_name }}</span>
              <span class="reply-quote-text">: {{ message.reply_to.content }}</span>
            </div>
          </div>
          <div class="message-content" :class="{ file: message.message_type === 'file' }">
            <template v-if="message.message_type === 'file'">
              <a href="#" class="file-link" @click.prevent="previewFile(message.file_id)">📎 {{ message.file_name }}</a>
            </template>
            <template v-else>
              {{ message.content }}
            </template>
          </div>
          <div class="message-time">{{ formatTime(message.created_at) }}</div>
        </div>
      </div>
    </div>

    <!-- Reply preview bar (above input) -->
    <div class="reply-preview" v-if="replyTo">
      <div class="reply-preview-line"></div>
      <div class="reply-preview-content">
        <span class="reply-label">回复 {{ replyTo.sender_name }}</span>
        <span class="reply-text">{{ replyTo.content.substring(0, 50) }}{{ replyTo.content.length > 50 ? '...' : '' }}</span>
      </div>
      <button class="reply-close" @click="cancelReply">×</button>
    </div>

    <!-- Multi-select toolbar -->
    <div class="multi-select-bar" v-if="multiSelectMode">
      <span class="multi-select-count">已选 {{ selectedMessages.length }} 条</span>
      <div class="multi-select-actions">
        <button class="ms-btn" @click="batchCopy" :disabled="selectedMessages.length === 0">
          <span>📋</span> 复制
        </button>
        <button class="ms-btn" @click="batchForward" :disabled="selectedMessages.length === 0">
          <span>➡️</span> 转发
        </button>
        <button class="ms-btn" @click="batchAiChat" :disabled="selectedMessages.length === 0">
          <span>🤖</span> AI助手
        </button>
        <button class="ms-btn ms-cancel" @click="exitMultiSelect">退出</button>
      </div>
    </div>

    <!-- Normal input area -->
    <div class="chat-input-area" v-if="!multiSelectMode">
      <button class="upload-btn" @click="showFileUpload = true">📁</button>
      <textarea
        class="chat-input"
        v-model="inputMessage"
        placeholder="输入消息..."
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <button class="send-btn" :disabled="!inputMessage.trim()" @click="sendMessage">发送</button>
    </div>

    <!-- Right-click context menu -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      @click.stop
    >
      <div class="context-menu-item" @click="handleCopy">
        <span class="menu-icon">📋</span><span>复制</span>
      </div>
      <div class="context-menu-item" @click="handleReply">
        <span class="menu-icon">↩️</span><span>回复</span>
      </div>
      <div class="context-menu-item" @click="handleForward">
        <span class="menu-icon">➡️</span><span>转发</span>
      </div>
      <div class="context-menu-item" @click="handleFavorite">
        <span class="menu-icon">⭐</span><span>收藏</span>
      </div>
      <div class="context-menu-item" @click="handleAiChat">
        <span class="menu-icon">🤖</span><span>AI对话</span>
      </div>
      <div class="context-menu-divider"></div>
      <div class="context-menu-item" @click="enterMultiSelect">
        <span class="menu-icon">☑️</span><span>多选</span>
      </div>
    </div>

    <!-- Forward dialog -->
    <div class="file-preview-modal" v-if="forwardDialog.visible" @click.self="forwardDialog.visible = false">
      <div class="file-preview-content" style="max-width: 400px;">
        <div class="file-preview-header">
          <div class="file-preview-title">转发给...</div>
          <button class="file-preview-close" @click="forwardDialog.visible = false">×</button>
        </div>
        <div class="file-preview-body">
          <div v-for="contact in forwardContacts" :key="contact.id" class="forward-contact-item" @click="doForward(contact)">
            <div class="avatar" style="width: 36px; height: 36px; font-size: 16px;">
              {{ contact.is_group ? '👥' : contact.name.charAt(0) }}
            </div>
            <span>{{ contact.name }} {{ contact.is_group ? '(群)' : '' }}</span>
          </div>
          <div v-if="forwardContacts.length === 0" style="text-align: center; color: #999; padding: 20px;">
            没有可转发的联系人
          </div>
        </div>
      </div>
    </div>

    <!-- File upload modal -->
    <div class="file-preview-modal" v-if="showFileUpload" @click.self="showFileUpload = false">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">上传文件</div>
          <button class="file-preview-close" @click="showFileUpload = false">×</button>
        </div>
        <div class="file-preview-body">
          <!-- Tab switch: local file vs manual input -->
          <div class="upload-tabs">
            <button class="upload-tab" :class="{ active: uploadMode === 'local' }" @click="uploadMode = 'local'">选择本地文件</button>
            <button class="upload-tab" :class="{ active: uploadMode === 'manual' }" @click="uploadMode = 'manual'">手动输入</button>
          </div>

          <!-- Local file upload -->
          <div v-if="uploadMode === 'local'" class="upload-local-area">
            <div
              class="upload-dropzone"
              @click="$refs.fileInput.click()"
              @dragover.prevent="dragOver = true"
              @dragleave.prevent="dragOver = false"
              @drop.prevent="handleFileDrop"
              :class="{ dragover: dragOver }"
            >
              <div class="upload-icon">📎</div>
              <div class="upload-hint">点击选择文件或拖拽文件到此处</div>
              <div class="upload-sub-hint">支持 Markdown、文本、代码、JSON 等格式</div>
              <input type="file" ref="fileInput" style="display:none" @change="handleFileSelect" />
            </div>
            <div v-if="selectedFile" class="upload-file-info">
              <span class="upload-file-name">📄 {{ selectedFile.name }}</span>
              <span class="upload-file-size">{{ formatFileSize(selectedFile.size) }}</span>
              <button class="upload-file-remove" @click="selectedFile = null">×</button>
            </div>
            <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress-bar">
              <div class="upload-progress-fill" :style="{ width: uploadProgress + '%' }"></div>
            </div>
          </div>

          <!-- Manual input -->
          <div v-if="uploadMode === 'manual'">
            <div style="margin-bottom: 12px;">
              <label>文件名:</label>
              <input type="text" v-model="uploadFileName" placeholder="请输入文件名（如 report.md）" style="width: 100%; padding: 8px; margin-top: 4px; border-radius: 6px; border: 1px solid #ddd;" />
            </div>
            <textarea class="file-editor" v-model="uploadFileContent" placeholder="输入内容..."></textarea>
          </div>
        </div>
        <div class="file-preview-actions">
          <button class="file-action-btn secondary" @click="showFileUpload = false">取消</button>
          <button
            class="file-action-btn primary"
            @click="uploadMode === 'local' ? uploadLocalFile() : uploadFile()"
            :disabled="uploadMode === 'local' ? !selectedFile : (!uploadFileName.trim() || !uploadFileContent.trim())"
          >
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- File preview modal -->
    <div class="file-preview-modal" v-if="previewFileData" @click.self="previewFileData = null">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">{{ previewFileData.name }}</div>
          <button class="file-preview-close" @click="previewFileData = null">×</button>
        </div>
        <div class="file-preview-body">
          <div class="markdown-content" v-html="renderMarkdown(previewFileData.content)"></div>
        </div>
        <div class="file-preview-actions">
          <button class="file-action-btn secondary" @click="editFile(previewFileData)">编辑</button>
          <button class="file-action-btn secondary" @click="downloadFile(previewFileData)">下载</button>
          <button class="file-action-btn danger" @click="deleteFile(previewFileData)">删除</button>
          <button class="file-action-btn secondary" @click="previewFileData = null">关闭</button>
        </div>
      </div>
    </div>

    <!-- File edit modal -->
    <div class="file-preview-modal" v-if="editingFile" @click.self="editingFile = null">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">编辑文件</div>
          <button class="file-preview-close" @click="editingFile = null">×</button>
        </div>
        <div class="file-preview-body">
          <textarea class="file-editor" v-model="editingFileContent">{{ editingFileContent }}</textarea>
        </div>
        <div class="file-preview-actions">
          <button class="file-action-btn secondary" @click="cancelEdit">取消</button>
          <button class="file-action-btn primary" @click="saveFile">保存</button>
        </div>
      </div>
    </div>

    <!-- Toast notification -->
    <transition name="toast">
      <div class="toast" v-if="toast.visible">{{ toast.message }}</div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { chatsApi, filesApi, favoritesApi } from '../api';
import { marked } from 'marked';

const props = defineProps({
  selectedContact: Object,
  currentUserId: Number,
  currentUser: Object
});

const emit = defineEmits(['message-sent', 'ai-chat']);

const messages = ref([]);
const inputMessage = ref('');
const messagesContainer = ref(null);
const showFileUpload = ref(false);
const uploadFileName = ref('');
const uploadFileContent = ref('');
const previewFileData = ref(null);
const editingFile = ref(null);
const editingFileContent = ref('');
const uploadMode = ref('local');
const selectedFile = ref(null);
const uploading = ref(false);
const uploadProgress = ref(0);
const dragOver = ref(false);

// Right-click context menu state
const contextMenu = ref({ visible: false, x: 0, y: 0, message: null });
// Reply state
const replyTo = ref(null);
// Forward dialog state
const forwardDialog = ref({ visible: false });
const forwardContacts = ref([]);
// Batch forward flag
const isBatchForward = ref(false);
// Toast notification
const toast = ref({ visible: false, message: '' });
// Multi-select state
const multiSelectMode = ref(false);
const selectedMessages = ref([]);

const showToast = (msg) => {
  toast.value = { visible: true, message: msg };
  setTimeout(() => { toast.value.visible = false; }, 2000);
};

const loadMessages = async () => {
  if (!props.selectedContact) return;
  const res = await chatsApi.getMessages(props.currentUserId, props.selectedContact.id);
  messages.value = res.data;
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

const sendMessage = async () => {
  if (!inputMessage.value.trim() || !props.selectedContact) return;
  let content = inputMessage.value.trim();
  let replyId = null;
  if (replyTo.value) {
    replyId = replyTo.value.id;
    replyTo.value = null;
  }
  await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, content, 'text', null, replyId);
  inputMessage.value = '';
  loadMessages();
  emit('message-sent');
};

const previewFile = async (fileId) => {
  const res = await filesApi.getContent(fileId);
  previewFileData.value = res.data;
};

const uploadFile = async () => {
  if (!uploadFileName.value.trim() || !uploadFileContent.value.trim()) return;
  const res = await filesApi.save(props.currentUserId, uploadFileName.value.trim(), uploadFileContent.value.trim());
  await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, res.data.name, 'file', res.data.id);
  showFileUpload.value = false;
  uploadFileName.value = '';
  uploadFileContent.value = '';
  loadMessages();
};

const handleFileSelect = (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

const handleFileDrop = (event) => {
  dragOver.value = false;
  const file = event.dataTransfer.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const uploadLocalFile = async () => {
  if (!selectedFile.value || uploading.value) return;
  uploading.value = true;
  uploadProgress.value = 0;

  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    const res = await filesApi.upload(props.currentUserId, formData);
    uploadProgress.value = 100;
    if (props.selectedContact) {
      await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, res.data.name, 'file', res.data.id);
    }
    showToast(`已上传 ${res.data.name}`);
    showFileUpload.value = false;
    selectedFile.value = null;
    uploadProgress.value = 0;
    loadMessages();
  } catch (e) {
    showToast('上传失败');
  }
  uploading.value = false;
};

const downloadFile = (file) => {
  const url = filesApi.download(file.id);
  const a = document.createElement('a');
  a.href = url;
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const deleteFile = async (file) => {
  if (!confirm(`确定删除文件「${file.name}」吗？`)) return;
  try {
    await filesApi.delete(file.id);
    showToast('文件已删除');
    previewFileData.value = null;
    loadMessages();
  } catch (e) {
    showToast('删除失败');
  }
};

const editFile = (file) => {
  editingFile.value = file;
  editingFileContent.value = file.content;
  previewFileData.value = null;
};

const cancelEdit = () => {
  editingFile.value = null;
  editingFileContent.value = '';
};

const saveFile = async () => {
  if (!editingFile.value) return;
  await filesApi.update(editingFile.value.id, editingFileContent.value);
  previewFileData.value = { ...editingFile.value, content: editingFileContent.value };
  editingFile.value = null;
  editingFileContent.value = '';
};

const formatTime = (timeStr) => {
  if (!timeStr) return '';
  const date = new Date(timeStr);
  return `${date.getMonth() + 1}-${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};

const renderMarkdown = (content) => {
  return marked(content);
};

// === Context menu handlers ===

const showContextMenu = (event, message) => {
  if (multiSelectMode.value) return;
  contextMenu.value = { visible: true, x: event.clientX, y: event.clientY, message: message };
};

const closeContextMenu = () => {
  contextMenu.value.visible = false;
};

const handleCopy = () => {
  const msg = contextMenu.value.message;
  if (!msg) return;
  navigator.clipboard.writeText(msg.content).then(() => {
    showToast('已复制到剪贴板');
  }).catch(() => { showToast('复制失败'); });
  closeContextMenu();
};

const handleReply = () => {
  const msg = contextMenu.value.message;
  if (!msg) return;
  replyTo.value = { ...msg };
  closeContextMenu();
  nextTick(() => {
    const input = document.querySelector('.chat-input');
    if (input) input.focus();
  });
};

const cancelReply = () => { replyTo.value = null; };

const handleForward = async () => {
  const msg = contextMenu.value.message;
  if (!msg) return;
  closeContextMenu();
  isBatchForward.value = false;
  const res = await chatsApi.getContacts(props.currentUserId);
  forwardContacts.value = res.data;
  forwardDialog.value = { visible: true };
};

const doForward = async (contact) => {
  if (isBatchForward.value) {
    // Batch forward: send all selected messages
    const selected = messages.value.filter(m => selectedMessages.value.includes(m.id));
    for (const msg of selected) {
      await chatsApi.sendMessage(props.currentUserId, contact.id, msg.content);
    }
    forwardDialog.value.visible = false;
    showToast(`已转发 ${selected.length} 条消息给 ${contact.name}`);
    exitMultiSelect();
  } else {
    const msg = contextMenu.value.message;
    if (!msg) return;
    await chatsApi.sendMessage(props.currentUserId, contact.id, msg.content);
    forwardDialog.value.visible = false;
    showToast(`已转发给 ${contact.name}`);
  }
  emit('message-sent');
};

const handleFavorite = async () => {
  const msg = contextMenu.value.message;
  if (!msg) return;
  try {
    await favoritesApi.add(props.currentUserId, msg.id);
    showToast('已收藏');
  } catch (e) { showToast('收藏失败'); }
  closeContextMenu();
};

const handleAiChat = () => {
  const msg = contextMenu.value.message;
  if (!msg) return;
  emit('ai-chat', { ...msg });
  closeContextMenu();
  showToast('已发送到AI助手');
};

// === Multi-select handlers ===

const enterMultiSelect = () => {
  multiSelectMode.value = true;
  selectedMessages.value = [];
  // Pre-select the right-clicked message
  if (contextMenu.value.message) {
    selectedMessages.value.push(contextMenu.value.message.id);
  }
  closeContextMenu();
};

const exitMultiSelect = () => {
  multiSelectMode.value = false;
  selectedMessages.value = [];
};

const toggleSelect = (messageId) => {
  const idx = selectedMessages.value.indexOf(messageId);
  if (idx >= 0) {
    selectedMessages.value.splice(idx, 1);
  } else {
    selectedMessages.value.push(messageId);
  }
};

const batchCopy = () => {
  const selected = messages.value.filter(m => selectedMessages.value.includes(m.id));
  const text = selected.map(m => `${m.sender_name}: ${m.content}`).join('\n');
  navigator.clipboard.writeText(text).then(() => {
    showToast(`已复制 ${selected.length} 条消息`);
  }).catch(() => { showToast('复制失败'); });
};

const batchForward = async () => {
  if (selectedMessages.value.length === 0) return;
  isBatchForward.value = true;
  const res = await chatsApi.getContacts(props.currentUserId);
  forwardContacts.value = res.data;
  forwardDialog.value = { visible: true };
};

const batchAiChat = () => {
  if (selectedMessages.value.length === 0) return;
  const selected = messages.value.filter(m => selectedMessages.value.includes(m.id));
  const combined = selected.map(m => `${m.sender_name}: ${m.content}`).join('\n');
  emit('ai-chat', {
    sender_name: `${selected.length}条选中消息`,
    content: combined
  });
  exitMultiSelect();
  showToast('已发送到AI助手');
};

watch(() => props.selectedContact, () => {
  if (multiSelectMode.value) exitMultiSelect();
  loadMessages();
}, { immediate: true });
watch(() => props.currentUserId, loadMessages);
</script>

<style scoped>
.context-menu {
  position: fixed;
  background: white;
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.12);
  padding: 6px 0;
  z-index: 2000;
  min-width: 130px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: background 0.15s;
}

.context-menu-item:hover {
  background-color: #f0f4ff;
  color: #1890ff;
}

.context-menu-divider {
  height: 1px;
  background-color: #eee;
  margin: 4px 0;
}

.menu-icon {
  font-size: 15px;
}

.reply-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.reply-preview-line {
  width: 3px;
  height: 24px;
  background-color: #1890ff;
  border-radius: 2px;
  flex-shrink: 0;
}

.reply-preview-content {
  flex: 1;
  overflow: hidden;
}

.reply-label {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
  display: block;
}

.reply-text {
  font-size: 13px;
  color: #666;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reply-close {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  padding: 0 4px;
  flex-shrink: 0;
}

.reply-close:hover { color: #333; }

.multi-select-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background-color: #e8eaf6;
  border-top: 1px solid #c5cae9;
}

.multi-select-count {
  font-size: 14px;
  color: #667eea;
  font-weight: 500;
}

.multi-select-actions {
  display: flex;
  gap: 8px;
}

.ms-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  background-color: white;
  color: #333;
  transition: all 0.15s;
}

.ms-btn:hover:not(:disabled) {
  background-color: #667eea;
  color: white;
}

.ms-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ms-cancel {
  background-color: #ffcdd2;
  color: #c62828;
}

.ms-cancel:hover {
  background-color: #ef5350 !important;
  color: white !important;
}

.message-checkbox {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.checkbox-inner {
  width: 20px;
  height: 20px;
  border: 2px solid #ccc;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: white;
  transition: all 0.15s;
}

.checkbox-inner.checked {
  background-color: #667eea;
  border-color: #667eea;
}

.message.selected .message-content {
  box-shadow: 0 0 0 2px #667eea;
}

.forward-contact-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;
  font-size: 14px;
  color: #333;
}

.forward-contact-item:hover {
  background-color: #f0f4ff;
}

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

.reply-quote-card {
  display: flex;
  gap: 6px;
  padding: 6px 10px;
  background-color: #f0f2f5;
  border-radius: 8px;
  margin-bottom: 4px;
  max-width: 100%;
  cursor: pointer;
  transition: background 0.15s;
}

.reply-quote-card:hover {
  background-color: #e8ebee;
}

.reply-quote-card.self {
  background-color: rgba(0,0,0,0.25);
}

.reply-quote-card.self:hover {
  background-color: rgba(0,0,0,0.3);
}

.reply-quote-line {
  width: 3px;
  background-color: #888;
  border-radius: 2px;
  flex-shrink: 0;
}

.reply-quote-card.self .reply-quote-line {
  background-color: rgba(255,255,255,0.6);
}

.reply-quote-content {
  font-size: 12px;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.reply-quote-name {
  color: #576b95;
  font-weight: 500;
}

.reply-quote-card.self .reply-quote-name {
  color: #ffffff;
}

.reply-quote-text {
  color: #555;
}

.reply-quote-card.self .reply-quote-text {
  color: #ffffff;
}

/* Upload styles */
.upload-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}

.upload-tab {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid #dde0e6;
  background-color: white;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  color: #666;
}

.upload-tab.active {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-color: transparent;
}

.upload-dropzone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background-color: #f8fafc;
}

.upload-dropzone:hover {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.upload-dropzone.dragover {
  border-color: #3b82f6;
  background-color: #dbeafe;
}

.upload-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.upload-hint {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-sub-hint {
  font-size: 12px;
  color: #999;
}

.upload-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background-color: #f0f4ff;
  border-radius: 8px;
  margin-top: 12px;
}

.upload-file-name {
  flex: 1;
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.upload-file-size {
  font-size: 12px;
  color: #888;
}

.upload-file-remove {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  padding: 0 4px;
}

.upload-file-remove:hover {
  color: #ef4444;
}

.upload-progress-bar {
  height: 4px;
  background-color: #e0e0e0;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.upload-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transition: width 0.3s;
}

.file-action-btn.danger {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.file-action-btn.danger:hover {
  background-color: #fee2e2;
}
</style>
