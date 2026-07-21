import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export const usersApi = {
  getAll: () => api.get('/users'),
  getById: (id) => api.get(`/users/${id}`)
}

export const chatsApi = {
  getContacts: (userId) => api.get(`/chats/contacts/${userId}`),
  getMessages: (userId, contactId) => api.get(`/chats/messages?user_id=${userId}&contact_id=${contactId}`),
  sendMessage: (userId, contactId, content, type = 'text', fileId = null, replyToId = null) =>
    api.post(`/chats/send?user_id=${userId}&contact_id=${contactId}&content=${encodeURIComponent(content)}&message_type=${type}&file_id=${fileId || ''}&reply_to_id=${replyToId || ''}`),
  getGroupMembers: (contactId) => api.get(`/chats/contacts/${contactId}/members`),
}

export const filesApi = {
  getList: (userId) => api.get(`/files/${userId}`),
  getContent: (fileId) => api.get(`/files/content/${fileId}`),
  save: (userId, name, content, type = 'markdown') =>
    api.post(`/files/save?user_id=${userId}&name=${encodeURIComponent(name)}&content=${encodeURIComponent(content)}&file_type=${type}`),
  update: (fileId, content) => api.put(`/files/update/${fileId}`, { content }),
  upload: (userId, formData) => api.post(`/files/upload/${userId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  }),
  download: (fileId) => `/api/files/download/${fileId}`,
  delete: (fileId) => api.delete(`/files/delete/${fileId}`),
  getContent: (fileId) => api.get(`/files/content/${fileId}`),
  getByName: (fileName) => api.get(`/files/by-name/${encodeURIComponent(fileName)}`),
  getExcel: (fileId) => api.get(`/files/excel/${fileId}`),
  saveExcel: (fileId, data) => api.put(`/files/excel/${fileId}`, data)
}

export const aiApi = {
  getTools: () => api.get('/ai/tools'),
  callTool: (userId, toolName, args) => api.post(`/ai/call_tool?user_id=${userId}&tool_name=${toolName}`, args),
  chat: (userId, message) => api.post(`/ai/chat?user_id=${userId}&message=${encodeURIComponent(message)}`, {}, { timeout: 120000 }),
  smartReply: (userId, message, contactId) =>
    api.post(`/ai/smart-reply?user_id=${userId}&message=${encodeURIComponent(message)}${contactId ? `&contact_id=${contactId}` : ''}`, {}, { timeout: 60000 }),
  classifyMessage: (message) =>
    api.post(`/ai/classify-message?message=${encodeURIComponent(message)}`, {}, { timeout: 60000 }),
  dailyDigest: (userId) =>
    api.post(`/ai/daily-digest/${userId}`, {}, { timeout: 120000 }),
  prioritizeTodos: (userId) =>
    api.post(`/ai/prioritize-todos/${userId}`, {}, { timeout: 60000 }),
  meetingMinutes: (userId, contactId) =>
    api.post(`/ai/meeting-minutes?user_id=${userId}&contact_id=${contactId}`, {}, { timeout: 120000 }),
  polishText: (text, style) =>
    api.post(`/ai/polish?text=${encodeURIComponent(text)}${style ? `&style=${encodeURIComponent(style)}` : ''}`, {}, { timeout: 60000 }),
  draftEmail: (scene, recipient, topic, points, original, language) =>
    api.post('/ai/draft-email', { scene, recipient, topic, points, original, language }, { timeout: 60000 }),
  extractInfo: (text, types) =>
    api.post('/ai/extract-info', { text, types }, { timeout: 60000 }),
  getUsage: (userId) => api.get(`/ai/usage/${userId}`)
}

export const favoritesApi = {
  getList: (userId) => api.get(`/favorites/${userId}`),
  add: (userId, messageId) => api.post(`/favorites/add?user_id=${userId}&message_id=${messageId}`),
  remove: (favoriteId) => api.delete(`/favorites/remove/${favoriteId}`)
}

export const todosApi = {
  getChatSummary: (userId) => api.get(`/todos/chat-summary/${userId}`),
  scanMessages: (userId) => api.post(`/todos/scan-messages/${userId}`, {}, { timeout: 120000 }),
  getChatTodos: (userId, status) => api.get(`/todos/chat-todos/${userId}?status=${status || 'pending'}`),
  updateTodo: (todoId, action, deadline) => api.put(`/todos/chat-todos/${todoId}?action=${action}${deadline ? `&deadline=${deadline}` : ''}`),
  convertToTodo: (todoId) => api.post(`/todos/chat-todos/${todoId}/convert`),
  createFromMessage: (userId, messageId) => api.post(`/todos/create-from-message/${userId}/${messageId}`),
  // 候选待办
  scanCandidates: (userId) => api.post(`/todos/scan-candidates/${userId}`, {}, { timeout: 120000 }),
  rescanEmails: (userId) => api.post(`/todos/rescan-emails/${userId}`),
  getCandidates: (userId) => api.get(`/todos/candidates/${userId}`),
  confirmCandidate: (candidateId) => api.post(`/todos/candidates/${candidateId}/confirm`),
  dismissCandidate: (candidateId) => api.post(`/todos/candidates/${candidateId}/dismiss`)
}

export const emailsApi = {
  getList: (userId, folder) => api.get(`/emails/list/${userId}${folder ? `?folder=${folder}` : ''}`),
  getDetail: (emailId) => api.get(`/emails/detail/${emailId}`),
  send: (userId, { to, subject, content, body_type = 'markdown', attachment_file_ids = [] }) =>
    api.post(`/emails/send/${userId}`, { to, subject, content, body_type, attachment_file_ids }, { timeout: 30000 }),
  addToTodo: (userId, emailId) => api.post(`/emails/add-to-todo/${userId}/${emailId}`),
  scan: (userId) => api.post(`/emails/scan/${userId}`, {}, { timeout: 120000 }),
  getTodos: (userId, status) => api.get(`/emails/todos/${userId}${status ? `?status=${status}` : ''}`),
  updateTodo: (todoId, action) => api.put(`/emails/todos/${todoId}?action=${action}`),
  getTrackers: (userId) => api.get(`/emails/trackers/${userId}`),
  track: (emailId) => api.post(`/emails/track/${emailId}`),
  checkTrackers: (userId) => api.post(`/emails/trackers/check/${userId}`, {}, { timeout: 120000 })
}

export const reportsApi = {
  fileSummary: (fileId) => api.post('/reports/file-summary', { file_id: fileId }, { timeout: 120000 }),
  workReport: (userId, startDate, endDate) => api.post(`/reports/work-report/${userId}`, { start_date: startDate, end_date: endDate }, { timeout: 120000 })
}

export const fileCollectionApi = {
  create: (initiatorUserId, groupContactId, fileName, description, deadline, assigneeUserIds) =>
    api.post(`/file-collection/create?initiator_user_id=${initiatorUserId}&group_contact_id=${groupContactId}&file_name=${encodeURIComponent(fileName)}&description=${encodeURIComponent(description)}${deadline ? `&deadline=${deadline}` : ''}&assignee_user_ids=${assigneeUserIds}`),
  detectFromMessage: (messageId) =>
    api.post(`/file-collection/detect-from-message/${messageId}`, {}, { timeout: 120000 }),
  scanProgress: (taskId) =>
    api.post(`/file-collection/scan-progress/${taskId}`, {}, { timeout: 120000 }),
  getTasks: (userId) => api.get(`/file-collection/tasks/${userId}`),
  submitItem: (itemId, fileId) =>
    api.post(`/file-collection/items/${itemId}/submit${fileId ? `?file_id=${fileId}` : ''}`),
  getTaskDetail: (taskId) => api.get(`/file-collection/tasks/${taskId}/detail`)
}

export const formsApi = {
  create: (userId, contactId, formName, requiredMembers, formUrl) =>
    api.post(`/forms/${userId}/create?contact_id=${contactId}&form_name=${encodeURIComponent(formName)}&required_members=${encodeURIComponent(requiredMembers)}${formUrl ? '&form_url=' + encodeURIComponent(formUrl) : ''}`),
  getList: (userId, status) =>
    api.get(`/forms/${userId}${status ? `?status=${status}` : ''}`),
  check: (trackerId) =>
    api.post(`/forms/${trackerId}/check`),
  remind: (trackerId) =>
    api.post(`/forms/${trackerId}/remind`),
  cancel: (trackerId) =>
    api.post(`/forms/${trackerId}/cancel`),
  checkAll: (userId) =>
    api.post(`/forms/check-all/${userId}`),
}

export const onlineFormsApi = {
  create: (data) => api.post('/online-forms/create', data),
  createFromExcel: (data) => api.post('/online-forms/create-from-excel', data),
  get: (formId) => api.get(`/online-forms/${formId}`),
  fill: (formId, memberName, data, memberUserId = null) => api.post(`/online-forms/${formId}/fill`, { member_name: memberName, member_user_id: memberUserId, data }),
  check: (formId) => api.post(`/online-forms/${formId}/check`),
  list: (userId) => api.get(`/online-forms/list/${userId}`),
  close: (formId) => api.post(`/online-forms/${formId}/close`),
  delete: (formId) => api.delete(`/online-forms/${formId}`),
  remind: (formId) => api.post(`/online-forms/${formId}/remind`),
  aiSummary: (formId) => api.post(`/online-forms/${formId}/ai-summary`),
  updateColumns: (formId, columns) => api.put(`/online-forms/${formId}/columns`, { columns }),
  addMembers: (formId, members) => api.post(`/online-forms/${formId}/add-members`, { members }),
  trackers: (userId) => api.get(`/online-forms/trackers/${userId}`),
}