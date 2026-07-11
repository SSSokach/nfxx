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
  sendMessage: (userId, contactId, content, type = 'text', fileId = null) => 
    api.post(`/chats/send?user_id=${userId}&contact_id=${contactId}&content=${encodeURIComponent(content)}&message_type=${type}&file_id=${fileId || ''}`)
}

export const filesApi = {
  getList: (userId) => api.get(`/files/${userId}`),
  getContent: (fileId) => api.get(`/files/content/${fileId}`),
  save: (userId, name, content, type = 'markdown') => 
    api.post(`/files/save?user_id=${userId}&name=${encodeURIComponent(name)}&content=${encodeURIComponent(content)}&file_type=${type}`),
  update: (fileId, content) => api.put(`/files/update/${fileId}`, { content })
}

export const aiApi = {
  getTools: () => api.get('/ai/tools'),
  callTool: (userId, toolName, args) => api.post(`/ai/call_tool?user_id=${userId}&tool_name=${toolName}`, args),
  chat: (userId, message) => api.post(`/ai/chat?user_id=${userId}&message=${encodeURIComponent(message)}`)
}
