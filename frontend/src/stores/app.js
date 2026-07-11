import { defineStore } from 'pinia'
import api from '../api'

export const useAppStore = defineStore('app', {
  state: () => ({
    currentUser: null,
    users: [],
    contacts: { users: [], groups: [] },
    currentChat: null, // { type: 'user'|'group', id, name }
    messages: []
  }),
  actions: {
    async loadUsers() {
      this.users = await api.getUsers()
      if (!this.currentUser && this.users.length > 0) {
        this.currentUser = this.users[0]
      }
    },
    async switchUser(userId) {
      const user = this.users.find(u => u.id === userId)
      if (user) {
        this.currentUser = user
        this.currentChat = null
        this.messages = []
        await this.loadContacts()
      }
    },
    async loadContacts() {
      if (!this.currentUser) return
      this.contacts = await api.getContacts(this.currentUser.id)
    },
    async selectChat(type, id, name) {
      this.currentChat = { type, id, name }
      await this.loadMessages()
    },
    async loadMessages() {
      if (!this.currentUser || !this.currentChat) return
      this.messages = await api.getMessages(
        this.currentUser.id,
        this.currentChat.type,
        this.currentChat.id
      )
    },
    async sendMessage(content, msgType = 'text', fileName = '') {
      if (!this.currentUser || !this.currentChat) return
      const msg = await api.sendMessage({
        sender_id: this.currentUser.id,
        receiver_type: this.currentChat.type,
        receiver_id: this.currentChat.id,
        content,
        msg_type: msgType,
        file_name: fileName
      })
      this.messages.push(msg)
      return msg
    },
    async updateFileContent(messageId, content) {
      await api.updateFile(messageId, content)
      const msg = this.messages.find(m => m.id === messageId)
      if (msg) msg.content = content
    }
  }
})
