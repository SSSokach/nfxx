<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'
import ContactList from './components/ContactList.vue'
import ChatArea from './components/ChatArea.vue'
import AIAssistant from './components/AIAssistant.vue'
import UserSwitcher from './components/UserSwitcher.vue'

const store = useAppStore()

onMounted(async () => {
  await store.loadUsers()
  await store.loadContacts()
})
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-title">AI 办公助手 Demo</div>
      <UserSwitcher />
    </header>
    <main class="app-main">
      <aside class="panel panel-left">
        <ContactList />
      </aside>
      <section class="panel panel-center">
        <ChatArea />
      </section>
      <aside class="panel panel-right">
        <AIAssistant />
      </aside>
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  color: #1a1a1a;
  background: #f5f5f5;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-left {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
}

.panel-center {
  flex: 1;
  background: #f5f5f5;
}

.panel-right {
  width: 380px;
  background: #fff;
  border-left: 1px solid #e8e8e8;
}
</style>
