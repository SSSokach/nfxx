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
              <button
                v-if="selectedContact && selectedContact.is_group && isExcelFile(message.file_name)"
                class="file-collect-btn"
                :class="{ detected: message.file_collected }"
                @click.stop="detectFileCollection(message)"
                :disabled="message.detecting"
              >{{ message.detecting ? '检测中...' : (message.file_collected ? '已生成待办 ✓' : '📋 生成待办') }}</button>
            </template>
            <template v-else>
              {{ message.content }}
            </template>
          </div>
          <div class="message-time">{{ formatTime(message.created_at) }}</div>
          <!-- Todo creation prompt (below the last received message) - disabled per user request -->
          <!-- <div class="todo-prompt-inline" v-if="isTodoPromptFor(message)">
            <span class="todo-prompt-label">是否创建待办：</span>
            <span class="todo-prompt-content">{{ getTodoTitle(message) }}</span>
            <button class="todo-prompt-btn create" @click.stop="createTodoFromMessage(message)">创建</button>
            <button class="todo-prompt-btn dismiss" @click.stop="dismissTodoPrompt(message)">忽略</button>
          </div> -->
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

    <!-- Smart reply panel (above input, shown when user clicks the smart reply button) -->
    <div class="smart-reply-panel" v-if="!multiSelectMode && smartReplyVisible">
      <div class="smart-reply-panel-header">
        <span class="smart-reply-panel-title">智能回复候选</span>
        <button class="smart-reply-panel-close" @click="smartReplyVisible = false">×</button>
      </div>
      <div class="smart-reply-list">
        <div class="smart-reply-loading" v-if="smartReplyLoading">AI 正在生成回复...</div>
        <div class="smart-reply-empty" v-else-if="smartReplies.length === 0">暂无回复建议</div>
        <button
          v-for="(reply, idx) in smartReplies"
          :key="idx"
          class="smart-reply-item"
          @click="useSmartReply(reply)"
        >{{ reply }}</button>
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
      <button class="smart-reply-trigger" @click="toggleSmartReply" :class="{ active: smartReplyVisible }" title="智能回复">💡</button>
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
    <div class="file-preview-modal" v-if="previewFileData" @click.self="closePreview">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">{{ previewFileData.name }}</div>
          <button class="file-preview-close" @click="closePreview">×</button>
        </div>
        <div class="file-preview-body">
          <!-- Excel 表格预览 -->
          <template v-if="excelPreview">
            <div v-if="excelLoading" class="excel-loading">加载Excel数据中...</div>
            <div v-else-if="excelData && excelData.sheets">
              <div class="excel-sheet-tabs" v-if="excelData.sheets.length > 1">
                <button
                  v-for="(sheet, idx) in excelData.sheets"
                  :key="idx"
                  class="excel-tab-btn"
                  :class="{ active: activeSheet === idx }"
                  @click="activeSheet = idx"
                >{{ sheet.name }}</button>
              </div>
              <div class="excel-table-wrapper" v-if="excelData.sheets[activeSheet]">
                <table class="excel-table">
                  <tbody>
                    <tr v-for="(row, rIdx) in excelData.sheets[activeSheet].rows" :key="rIdx" :class="{ 'header-row': rIdx === 0 }">
                      <td class="row-num">{{ rIdx + 1 }}</td>
                      <td
                        v-for="(cell, cIdx) in row"
                        :key="cIdx"
                        :class="{ 'header-cell': rIdx === 0, 'editable-cell': rIdx > 0, 'cell-modified': isCellModified(rIdx, cIdx) }"
                        :contenteditable="rIdx > 0"
                        @blur="onCellEdit($event, rIdx, cIdx)"
                        @keydown.enter.prevent="onCellEnter($event)"
                      >{{ cell }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-if="excelChanges.length > 0" class="excel-unsaved-hint">
                {{ excelChanges.length }} 处修改未保存，关闭时自动保存
              </div>
            </div>
            <div v-else class="excel-loading">无法读取Excel文件</div>
          </template>
          <!-- 普通文件预览 -->
          <template v-else>
            <div class="markdown-content" v-html="renderMarkdown(previewFileData.content)"></div>
          </template>
        </div>
        <div class="file-preview-actions">
          <button v-if="!excelPreview" class="file-action-btn secondary" @click="editFile(previewFileData)">编辑</button>
          <button v-if="excelPreview && excelChanges.length > 0" class="file-action-btn primary" @click="saveExcelChanges">保存</button>
          <button class="file-action-btn secondary" @click="downloadFile(previewFileData)">下载</button>
          <button class="file-action-btn danger" @click="deleteFile(previewFileData)">删除</button>
          <button class="file-action-btn secondary" @click="closePreview">关闭</button>
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
import { ref, watch, nextTick, computed } from 'vue';
import { chatsApi, filesApi, favoritesApi, todosApi, fileCollectionApi, aiApi } from '../api';
import { marked } from 'marked';

const props = defineProps({
  selectedContact: Object,
  currentUserId: Number,
  currentUser: Object
});

const emit = defineEmits(['message-sent', 'ai-chat', 'todo-created']);

const messages = ref([]);
const inputMessage = ref('');
const messagesContainer = ref(null);
const showFileUpload = ref(false);
const uploadFileName = ref('');
const uploadFileContent = ref('');
const previewFileData = ref(null);
const excelPreview = ref(false);
const excelLoading = ref(false);
const excelData = ref(null);
const activeSheet = ref(0);
const editingFile = ref(null);
const excelChanges = ref([]); // [{row, col, value}]
const excelSaving = ref(false);
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
  const fileData = res.data;
  // 检查是否为Excel文件
  if (fileData.name && (fileData.name.endsWith('.xlsx') || fileData.name.endsWith('.xls'))) {
    excelPreview.value = true;
    excelLoading.value = true;
    excelData.value = null;
    activeSheet.value = 0;
    excelChanges.value = [];
    previewFileData.value = fileData;
    try {
      const excelRes = await filesApi.getExcel(fileId);
      excelData.value = excelRes.data;
    } catch (e) {
      excelData.value = null;
    }
    excelLoading.value = false;
  } else {
    excelPreview.value = false;
    previewFileData.value = fileData;
  }
};

// ===== 文件收集检测 =====
const isExcelFile = (fileName) => {
  return fileName && fileName.match(/\.(xlsx|xls)$/i);
};

const detectFileCollection = async (message) => {
  if (message.detecting) return;
  message.detecting = true;
  try {
    const res = await fileCollectionApi.detectFromMessage(message.id);
    if (res.data.detected) {
      message.file_collected = true;
      showToast(`已检测到文件收集请求：${res.data.total}人待填写，已生成${res.data.todos_created}个待办`);
      emit('todo-created');
    } else if (res.data.reason && res.data.reason.includes('已创建过')) {
      // 已经创建过收集任务，标记为已收集
      message.file_collected = true;
      showToast('该文件已生成过待办');
    } else {
      showToast(res.data.reason || '未检测到文件收集请求');
    }
  } catch (e) {
    showToast('检测失败');
  }
  message.detecting = false;
};

// ===== Excel 在线编辑 =====
const isCellModified = (row, col) => {
  return excelChanges.value.some(c => c.row === row && c.col === col);
};

const onCellEdit = (event, row, col) => {
  const newValue = event.target.textContent.trim();
  const sheet = excelData.value?.sheets?.[activeSheet.value];
  if (!sheet) return;
  const oldValue = sheet.rows[row]?.[col] ?? '';

  if (newValue === oldValue) {
    // 恢复原值，移除变更
    excelChanges.value = excelChanges.value.filter(c => !(c.row === row && c.col === col));
    return;
  }

  // 更新本地数据
  sheet.rows[row][col] = newValue;

  // 记录变更
  const existing = excelChanges.value.findIndex(c => c.row === row && c.col === col);
  if (existing >= 0) {
    excelChanges.value[existing].value = newValue;
  } else {
    excelChanges.value.push({ row, col, value: newValue });
  }
};

const onCellEnter = (event) => {
  // 按回车后，光标移到下一个单元格
  event.target.blur();
};

const saveExcelChanges = async () => {
  if (excelChanges.value.length === 0 || !previewFileData.value) return;

  excelSaving.value = true;
  try {
    await filesApi.saveExcel(previewFileData.value.id, {
      sheet_index: activeSheet.value,
      changes: excelChanges.value,
      user_id: props.currentUserId,
    });
    excelChanges.value = [];
    emit('todo-created');
  } catch (e) {
    // ignore
  }
  excelSaving.value = false;
};

const closePreview = async () => {
  // 如果有未保存的 Excel 修改，先保存
  if (excelPreview.value && excelChanges.value.length > 0) {
    await saveExcelChanges();
  }
  // 重置状态
  excelPreview.value = false;
  excelChanges.value = [];
  previewFileData.value = null;
};

const uploadFile = async () => {
  if (!uploadFileName.value.trim() || !uploadFileContent.value.trim()) return;
  const res = await filesApi.save(props.currentUserId, uploadFileName.value.trim(), uploadFileContent.value.trim());
  const msgRes = await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, res.data.name, 'file', res.data.id);
  // 如果是群聊中的Excel文件，自动检测文件收集请求
  if (props.selectedContact.is_group && res.data.name.match(/\.(xlsx|xls)$/i)) {
    try {
      await fileCollectionApi.detectFromMessage(msgRes.data.id);
      emit('todo-created');
    } catch (e) {
      // 检测失败不阻塞
    }
  }
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
      const msgRes = await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, res.data.name, 'file', res.data.id);
      // 如果是群聊中的Excel文件，自动检测文件收集请求
      if (props.selectedContact.is_group && res.data.name.match(/\.(xlsx|xls)$/i)) {
        try {
          await fileCollectionApi.detectFromMessage(msgRes.data.id);
          emit('todo-created');
        } catch (e) {
          // 检测失败不阻塞
        }
      }
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

// === Smart reply (button-triggered, AI-powered) ===
const smartReplies = ref([]);
const smartReplyVisible = ref(false);
const smartReplyLoading = ref(false);

const toggleSmartReply = async () => {
  if (smartReplyVisible.value) {
    smartReplyVisible.value = false;
    return;
  }
  // 获取对方最后一条消息
  const lastMsg = lastReceivedMsg.value;
  if (!lastMsg) {
    showToast('没有可回复的消息');
    return;
  }
  smartReplyVisible.value = true;
  smartReplyLoading.value = true;
  smartReplies.value = [];
  try {
    const res = await aiApi.smartReply(props.currentUserId, lastMsg.content, props.selectedContact?.id);
    smartReplies.value = res.data.replies || [];
    if (smartReplies.value.length === 0) {
      showToast('未生成回复建议');
    }
  } catch (e) {
    showToast('生成回复失败');
    smartReplies.value = [];
  }
  smartReplyLoading.value = false;
};

const useSmartReply = (reply) => {
  inputMessage.value = reply;
  smartReplyVisible.value = false;
  nextTick(() => {
    const input = document.querySelector('.chat-input');
    if (input) input.focus();
  });
};

// === Todo creation prompt (inline below message) ===
const dismissedTodoMsgs = ref(new Set());
const createdTodoMsgs = ref(new Set());

// Find the last message from the other party
const lastReceivedMsg = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (!messages.value[i].is_self) return messages.value[i];
  }
  return null;
});

const isTodoPromptFor = (message) => {
  const last = lastReceivedMsg.value;
  if (!last || last.id !== message.id) return false;
  if (dismissedTodoMsgs.value.has(message.id)) return false;
  if (createdTodoMsgs.value.has(message.id)) return false;
  return true;
};

const getTodoTitle = (message) => {
  const content = message.content || '';
  return content.length > 30 ? content.substring(0, 30) + '...' : content;
};

const createTodoFromMessage = async (message) => {
  try {
    await todosApi.createFromMessage(props.currentUserId, message.id);
    showToast('待办已创建');
    createdTodoMsgs.value.add(message.id);
    emit('todo-created');
  } catch (e) {
    showToast('创建待办失败');
  }
};

const dismissTodoPrompt = (message) => {
  dismissedTodoMsgs.value.add(message.id);
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
  dismissedTodoMsgs.value = new Set();
  createdTodoMsgs.value = new Set();
  smartReplyVisible.value = false;
  loadMessages();
}, { immediate: true });
watch(() => props.currentUserId, loadMessages);

// 暴露给父组件：通过文件名预览Excel
const previewExcelByName = async (fileName) => {
  // 先通过API获取文件列表，找到匹配的文件
  try {
    const res = await filesApi.getByName(fileName);
    if (res.data && res.data.id) {
      await previewFile(res.data.id);
    }
  } catch (e) {
    // 如果API不支持，尝试从消息中查找
    for (const msg of messages.value) {
      if (msg.file_name && msg.file_name === fileName) {
        await previewFile(msg.file_id);
        return;
      }
    }
  }
};

defineExpose({ previewExcelByName });
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

/* ===== Inline todo prompt (below message) ===== */
.todo-prompt-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 6px 10px;
  background-color: #f5f3ff;
  border: 1px solid #d9d4f5;
  border-radius: 8px;
  max-width: 400px;
}

.todo-prompt-label {
  font-size: 12px;
  color: #667eea;
  font-weight: 500;
  white-space: nowrap;
}

.todo-prompt-content {
  flex: 1;
  font-size: 12px;
  color: #4a4a5e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-prompt-btn {
  padding: 3px 10px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.todo-prompt-btn.create {
  background-color: #667eea;
  color: #fff;
}

.todo-prompt-btn.create:hover {
  opacity: 0.85;
}

.todo-prompt-btn.dismiss {
  background-color: #eef0f5;
  color: #666;
}

.todo-prompt-btn.dismiss:hover {
  background-color: #e0e0e0;
}

/* ===== Smart reply panel + trigger button ===== */
.smart-reply-panel {
  flex-shrink: 0;
  border-top: 1px solid #e8eaf0;
  background-color: #faf9ff;
  padding: 10px 14px;
}

.smart-reply-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.smart-reply-panel-title {
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
}

.smart-reply-panel-close {
  border: none;
  background: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
  line-height: 1;
}

.smart-reply-panel-close:hover {
  color: #333;
}

.smart-reply-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.smart-reply-item {
  padding: 8px 14px;
  border: 1px solid #d9d4f5;
  border-radius: 8px;
  background-color: #fff;
  color: #333;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.smart-reply-item:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: transparent;
}

.smart-reply-trigger {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background-color: #f0f4ff;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.smart-reply-trigger:hover {
  background-color: #e0e7ff;
}

.smart-reply-trigger.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* ===== Excel Preview ===== */
.excel-loading {
  text-align: center;
  padding: 40px;
  color: #9ca3af;
  font-size: 14px;
}

.excel-sheet-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  border-bottom: 2px solid #e8eaf0;
  padding-bottom: 4px;
}

.excel-tab-btn {
  padding: 4px 12px;
  border: 1px solid #e8eaf0;
  border-radius: 4px 4px 0 0;
  background: #f9fafb;
  color: #6b7280;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.excel-tab-btn.active {
  background: #667eea;
  color: #fff;
  border-color: #667eea;
}

.excel-table-wrapper {
  overflow: auto;
  max-height: 500px;
  border: 1px solid #e8eaf0;
  border-radius: 6px;
}

.excel-table {
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
  white-space: nowrap;
}

.excel-table td {
  border: 1px solid #e8eaf0;
  padding: 4px 10px;
  min-width: 80px;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.excel-table .row-num {
  background: #f3f4f6;
  color: #9ca3af;
  text-align: center;
  min-width: 40px;
  font-size: 11px;
  user-select: none;
}

.excel-table .header-row .header-cell {
  background: #667eea;
  color: #fff;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.excel-table tr:nth-child(even):not(.header-row) td {
  background: #fafbfc;
}

.excel-table tr:hover:not(.header-row) td {
  background: #f0f7ff;
}

.excel-table .editable-cell {
  cursor: text;
}

.excel-table .editable-cell:focus {
  outline: 2px solid #667eea;
  outline-offset: -2px;
  background: #fff !important;
}

.excel-table .cell-modified {
  background: #fef9c3 !important;
  color: #92400e;
}

.excel-unsaved-hint {
  margin-top: 8px;
  padding: 6px 12px;
  background: #fef9c3;
  border: 1px solid #fde68a;
  border-radius: 6px;
  font-size: 12px;
  color: #92400e;
}

.file-action-btn.primary {
  background: #667eea;
  color: #fff;
  border-color: #667eea;
}

.file-action-btn.primary:hover {
  background: #5568d3;
}

/* ===== File Collection Button ===== */
.file-collect-btn {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 10px;
  border: 1px solid #667eea;
  border-radius: 4px;
  background: #fff;
  color: #667eea;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.file-collect-btn:hover:not(:disabled) {
  background: #667eea;
  color: #fff;
}

.file-collect-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.file-collect-btn.detected {
  background: #f0fdf4;
  border-color: #16a34a;
  color: #16a34a;
  cursor: default;
}
</style>
