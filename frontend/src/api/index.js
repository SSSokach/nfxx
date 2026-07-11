import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

export default {
  getUsers() {
    return api.get('/users').then(r => r.data)
  },
  getContacts(userId) {
    return api.get(`/users/${userId}/contacts`).then(r => r.data)
  },
  getMessages(userId, peerType, peerId) {
    return api.get('/messages', { params: { user_id: userId, peer_type: peerType, peer_id: peerId } }).then(r => r.data)
  },
  sendMessage(data) {
    return api.post('/messages', data).then(r => r.data)
  },
  getFile(messageId) {
    return api.get(`/files/${messageId}`).then(r => r.data)
  },
  updateFile(messageId, content) {
    return api.put(`/files/${messageId}`, { content }).then(r => r.data)
  },
  aiChat(data) {
    return api.post('/ai/chat', data).then(r => r.data)
  }
}
