<template>
  <div class="chat-area">
    <div class="chat-header" v-if="selectedContact">
      <div class="avatar">{{ selectedContact.is_group ? '👥' : selectedContact.name.charAt(0) }}</div>
      <div>
        <div class="contact-name">{{ selectedContact.name }}</div>
        <div class="contact-last-message">{{ selectedContact.is_group ? '群聊' : '在线' }}</div>
      </div>
    </div>
    <div class="messages-container" ref="messagesContainer">
      <div v-for="message in messages" :key="message.id" class="message" :class="{ self: message.is_self }">
        <div class="message-avatar">{{ message.is_self ? currentUser.name.charAt(0) : message.sender_name.charAt(0) }}</div>
        <div>
          <div class="message-content" :class="{ file: message.message_type === 'file' }">
            <template v-if="message.message_type === 'file'">
              <a href="#" class="file-link" @click.prevent="previewFile(message.file_id)">{{ message.file_name }}</a>
            </template>
            <template v-else>
              {{ message.content }}
            </template>
          </div>
          <div class="message-time">{{ formatTime(message.created_at) }}</div>
        </div>
      </div>
    </div>
    <div class="chat-input-area">
      <button class="upload-btn" @click="showFileUpload = true">📁 上传文件</button>
      <textarea 
        class="chat-input" 
        v-model="inputMessage" 
        placeholder="输入消息..."
        @keydown.enter.exact.prevent="sendMessage"
      ></textarea>
      <button class="send-btn" :disabled="!inputMessage.trim()" @click="sendMessage">发送</button>
    </div>

    <div class="file-preview-modal" v-if="showFileUpload" @click.self="showFileUpload = false">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <div class="file-preview-title">上传Markdown文件</div>
          <button class="file-preview-close" @click="showFileUpload = false">×</button>
        </div>
        <div class="file-preview-body">
          <div style="margin-bottom: 12px;">
            <label>文件名:</label>
            <input type="text" v-model="uploadFileName" placeholder="请输入文件名" style="width: 100%; padding: 8px; margin-top: 4px;" />
          </div>
          <textarea 
            class="file-editor" 
            v-model="uploadFileContent" 
            placeholder="输入Markdown内容..."
          ></textarea>
        </div>
        <div class="file-preview-actions">
          <button class="file-action-btn secondary" @click="showFileUpload = false">取消</button>
          <button class="file-action-btn primary" @click="uploadFile">上传</button>
        </div>
      </div>
    </div>

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
          <button class="file-action-btn secondary" @click="previewFileData = null">关闭</button>
        </div>
      </div>
    </div>

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
  </div>
</template>

<script setup>import { ref, watch, nextTick } from 'vue';
import { chatsApi, filesApi } from '../api';
import { marked } from 'marked';
const props = defineProps({
 selectedContact: Object,
 currentUserId: Number,
 currentUser: Object
});
const messages = ref([]);
const inputMessage = ref('');
const messagesContainer = ref(null);
const showFileUpload = ref(false);
const uploadFileName = ref('');
const uploadFileContent = ref('');
const previewFileData = ref(null);
const editingFile = ref(null);
const editingFileContent = ref('');
const loadMessages = async () => {
 if (!props.selectedContact)
 return;
 const res = await chatsApi.getMessages(props.currentUserId, props.selectedContact.id);
 messages.value = res.data;
 nextTick(() => {
 if (messagesContainer.value) {
 messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
 }
 });
};
const sendMessage = async () => {
 if (!inputMessage.value.trim() || !props.selectedContact)
 return;
 await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, inputMessage.value.trim());
 inputMessage.value = '';
 loadMessages();
};
const previewFile = async (fileId) => {
 const res = await filesApi.getContent(fileId);
 previewFileData.value = res.data;
};
const uploadFile = async () => {
 if (!uploadFileName.value.trim() || !uploadFileContent.value.trim())
 return;
 const res = await filesApi.save(props.currentUserId, uploadFileName.value.trim(), uploadFileContent.value.trim());
 await chatsApi.sendMessage(props.currentUserId, props.selectedContact.id, res.data.name, 'file', res.data.id);
 showFileUpload.value = false;
 uploadFileName.value = '';
 uploadFileContent.value = '';
 loadMessages();
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
 if (!editingFile.value)
 return;
 await filesApi.update(editingFile.value.id, editingFileContent.value);
 previewFileData.value = { ...editingFile.value, content: editingFileContent.value };
 editingFile.value = null;
 editingFileContent.value = '';
};
const formatTime = (timeStr) => {
 if (!timeStr)
 return '';
 const date = new Date(timeStr);
 return `${date.getMonth() + 1}-${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};
const renderMarkdown = (content) => {
 return marked(content);
};
watch(() => props.selectedContact, loadMessages, { immediate: true });
watch(() => props.currentUserId, loadMessages);
</script>
