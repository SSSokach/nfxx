<script setup>
import { useAppStore } from '../stores/app'

const store = useAppStore()
</script>

<template>
  <div class="contact-list">
    <div v-if="store.contacts.groups.length > 0" class="contact-section">
      <div class="section-title">群聊</div>
      <div
        v-for="group in store.contacts.groups"
        :key="'g' + group.id"
        class="contact-item"
        :class="{ active: store.currentChat?.type === 'group' && store.currentChat?.id === group.id }"
        @click="store.selectChat('group', group.id, group.name)"
      >
        <div class="avatar">{{ group.avatar }}</div>
        <span class="name">{{ group.name }}</span>
      </div>
    </div>

    <div class="contact-section">
      <div class="section-title">联系人</div>
      <div
        v-for="user in store.contacts.users"
        :key="'u' + user.id"
        class="contact-item"
        :class="{ active: store.currentChat?.type === 'user' && store.currentChat?.id === user.id }"
        @click="store.selectChat('user', user.id, user.name)"
      >
        <div class="avatar">{{ user.avatar }}</div>
        <span class="name">{{ user.name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contact-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.contact-section {
  margin-bottom: 8px;
}

.section-title {
  padding: 8px 16px 4px;
  font-size: 12px;
  color: #999;
  font-weight: 500;
}

.contact-item {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.contact-item:hover {
  background: #f5f5f5;
}

.contact-item.active {
  background: #e6f4ff;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: #4a90d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  margin-right: 10px;
  flex-shrink: 0;
}

.name {
  font-size: 14px;
  color: #333;
}
</style>
