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
    api.post(`/chats/send?user_id=${userId}&contact_id=${contactId}&content=${encodeURIComponent(content)}&message_type=${type}&file_id=${fileId || ''}&reply_to_id=${replyToId || ''}`)
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
  delete: (fileId) => api.delete(`/files/delete/${fileId}`)
}

export const aiApi = {
  getTools: () => api.get('/ai/tools'),
  callTool: (userId, toolName, args) => api.post(`/ai/call_tool?user_id=${userId}&tool_name=${toolName}`, args),
  chat: (userId, message) => api.post(`/ai/chat?user_id=${userId}&message=${encodeURIComponent(message)}`, {}, { timeout: 120000 })
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
  updateTodo: (todoId, action, deadline) => api.put(`/todos/chat-todos/${todoId}`, { action, deadline }),
  convertToTodo: (todoId) => api.post(`/todos/chat-todos/${todoId}/convert`)
}

export const emailsApi = {
  getList: (userId) => api.get(`/emails/list/${userId}`),
  scan: (userId) => api.post(`/emails/scan/${userId}`, {}, { timeout: 120000 }),
  getTodos: (userId) => api.get(`/emails/todos/${userId}`),
  updateTodo: (todoId, action) => api.put(`/emails/todos/${todoId}`, { action }),
  getTrackers: (userId) => api.get(`/emails/trackers/${userId}`),
  track: (emailId) => api.post(`/emails/track/${emailId}`),
  checkTrackers: (userId) => api.post(`/emails/trackers/check/${userId}`, {}, { timeout: 120000 })
}

export const reportsApi = {
  fileSummary: (fileId) => api.post('/reports/file-summary', { file_id: fileId }, { timeout: 120000 }),
  workReport: (userId, startDate, endDate) => api.post(`/reports/work-report/${userId}`, { start_date: startDate, end_date: endDate }, { timeout: 120000 })
}
