<script setup>
import { ref } from 'vue'
import { useAppStore } from '../stores/app'

const store = useAppStore()
const open = ref(false)

const toggle = () => {
  open.value = !open.value
}

const select = (userId) => {
  store.switchUser(userId)
  open.value = false
}
</script>

<template>
  <div class="user-switcher">
    <button class="switcher-btn" @click="toggle">
      <div class="current-avatar">{{ store.currentUser?.avatar }}</div>
      <span class="current-name">{{ store.currentUser?.name }}</span>
      <span class="arrow" :class="{ up: open }">▼</span>
    </button>
    <div v-if="open" class="dropdown-menu" @click.self="open = false">
      <div
        v-for="user in store.users"
        :key="user.id"
        class="dropdown-item"
        :class="{ active: user.id === store.currentUser?.id }"
        @click="select(user.id)"
      >
        <div class="avatar">{{ user.avatar }}</div>
        <span>{{ user.name }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-switcher {
  position: relative;
}

.switcher-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.switcher-btn:hover {
  border-color: #4a90d9;
}

.current-avatar {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: #4a90d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.current-name {
  font-weight: 500;
}

.arrow {
  font-size: 10px;
  color: #999;
  transition: transform 0.2s;
}

.arrow.up {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-width: 140px;
  z-index: 100;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.dropdown-item.active {
  background: #e6f4ff;
  color: #4a90d9;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: #4a90d9;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}
</style>
