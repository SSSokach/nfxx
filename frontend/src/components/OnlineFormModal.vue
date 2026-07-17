<template>
  <div v-if="visible" class="ofm-overlay" @click.self="close">
    <div class="ofm-modal">
      <!-- Header -->
      <div class="ofm-header">
        <h3>{{ form?.title || '在线表格' }}</h3>
        <button class="ofm-close" @click="close">&times;</button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="ofm-loading">加载中...</div>

      <!-- Content -->
      <template v-else-if="form">
        <!-- Progress bar -->
        <div class="ofm-progress-bar">
          <div class="ofm-progress-info">
            <span>填写进度：{{ form.progress }}</span>
            <span class="ofm-progress-pct">{{ Math.round(form.filled_count / form.total_count * 100) }}%</span>
          </div>
          <div class="ofm-progress-track">
            <div class="ofm-progress-fill" :style="{width: (form.filled_count / form.total_count * 100) + '%'}"></div>
          </div>
        </div>

        <!-- Table -->
        <div class="ofm-table-wrap">
          <table class="ofm-table">
            <thead>
              <tr>
                <th>填写人</th>
                <th v-for="col in form.columns" :key="col.key">{{ col.label }}</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in form.rows" :key="row.id" :class="{filled: row.filled}">
                <td class="ofm-member">{{ row.member_name }}</td>
                <td v-for="col in form.columns" :key="col.key">
                  {{ row.data[col.key] || '-' }}
                </td>
                <td>
                  <span class="ofm-status" :class="row.filled ? 'done' : 'pending'">
                    {{ row.filled ? '✓ 已填' : '待填' }}
                  </span>
                </td>
                <td>
                  <button v-if="!row.filled || editingRow === row.member_name" class="ofm-btn small" @click="startEdit(row)">
                    {{ editingRow === row.member_name ? '保存' : '填写' }}
                  </button>
                  <button v-if="row.filled && editingRow !== row.member_name" class="ofm-btn small ghost" @click="startEdit(row)">修改</button>
                </td>
              </tr>
              <!-- Edit row -->
              <tr v-if="editingRow" class="ofm-edit-row">
                <td class="ofm-member">{{ editingRow }}</td>
                <td v-for="col in form.columns" :key="col.key">
                  <input class="ofm-input" v-model="editData[col.key]" :placeholder="col.label" />
                </td>
                <td></td>
                <td>
                  <button class="ofm-btn small" @click="submitFill" :disabled="filling">{{ filling ? '保存中' : '保存' }}</button>
                  <button class="ofm-btn small ghost" @click="cancelEdit">取消</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Actions -->
        <div class="ofm-actions">
          <button class="ofm-btn" @click="refreshForm">🔄 刷新检测</button>
          <button class="ofm-btn warn" @click="$emit('remind', formId)" v-if="form.filled_count < form.total_count">@催办未填写</button>
          <button class="ofm-btn danger" @click="closeForm" v-if="form.status === 'active'">关闭表格</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { onlineFormsApi } from '../api'

const props = defineProps({
  visible: Boolean,
  formId: Number,
})
const emit = defineEmits(['close', 'remind', 'updated'])

const form = ref(null)
const loading = ref(false)
const editingRow = ref(null)
const editData = ref({})
const filling = ref(false)

const loadForm = async () => {
  if (!props.formId) return
  loading.value = true
  try {
    const res = await onlineFormsApi.get(props.formId)
    form.value = res.data
  } catch (e) {
    form.value = null
  }
  loading.value = false
}

watch(() => [props.visible, props.formId], ([v]) => {
  if (v && props.formId) loadForm()
})

const close = () => {
  emit('close')
}

const startEdit = (row) => {
  editingRow.value = row.member_name
  editData.value = { ...row.data }
  // 如果之前有 editingRow 且点了保存，走 submitFill
  if (row.filled && editingRow.value === row.member_name) {
    // 点的是"修改"按钮，进入编辑
  }
}

const cancelEdit = () => {
  editingRow.value = null
  editData.value = {}
}

const submitFill = async () => {
  if (!editingRow.value) return
  filling.value = true
  try {
    await onlineFormsApi.fill(props.formId, editingRow.value, editData.value)
    editingRow.value = null
    editData.value = {}
    await loadForm()
    emit('updated')
  } catch (e) {}
  filling.value = false
}

const refreshForm = async () => {
  await onlineFormsApi.check(props.formId)
  await loadForm()
  emit('updated')
}

const closeForm = async () => {
  await onlineFormsApi.close(props.formId)
  await loadForm()
  emit('updated')
}
</script>

<style scoped>
.ofm-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.ofm-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  overflow-y: auto;
  padding: 24px;
}
.ofm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.ofm-header h3 { margin: 0; font-size: 18px; }
.ofm-close {
  background: none; border: none; font-size: 24px;
  cursor: pointer; color: #6b7280; line-height: 1;
}
.ofm-close:hover { color: #111; }
.ofm-loading { text-align: center; padding: 40px; color: #9ca3af; }

.ofm-progress-bar { margin-bottom: 16px; }
.ofm-progress-info {
  display: flex; justify-content: space-between;
  font-size: 13px; color: #6b7280; margin-bottom: 6px;
}
.ofm-progress-pct { font-weight: 600; }
.ofm-progress-track {
  height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden;
}
.ofm-progress-fill {
  height: 100%; background: #3b82f6; border-radius: 3px; transition: width 0.3s;
}

.ofm-table-wrap { overflow-x: auto; }
.ofm-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.ofm-table th, .ofm-table td {
  border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left;
}
.ofm-table th {
  background: #f9fafb; font-weight: 600; color: #374151; white-space: nowrap;
}
.ofm-table tr.filled { background: #f0fdf4; }
.ofm-member { font-weight: 500; white-space: nowrap; }
.ofm-status {
  padding: 2px 8px; border-radius: 4px; font-size: 12px;
}
.ofm-status.done { background: #d1fae5; color: #059669; }
.ofm-status.pending { background: #fef3c7; color: #d97706; }

.ofm-edit-row { background: #eff6ff; }
.ofm-input {
  width: 100%; padding: 4px 8px; border: 1px solid #d1d5db;
  border-radius: 4px; font-size: 13px; outline: none;
}
.ofm-input:focus { border-color: #3b82f6; }

.ofm-btn {
  padding: 6px 14px; border: none; border-radius: 6px;
  font-size: 13px; cursor: pointer; background: #3b82f6; color: white;
}
.ofm-btn.small { padding: 3px 10px; font-size: 12px; }
.ofm-btn.ghost { background: #f3f4f6; color: #374151; }
.ofm-btn.warn { background: #f59e0b; }
.ofm-btn.danger { background: #ef4444; }
.ofm-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ofm-btn:hover:not(:disabled) { opacity: 0.9; }

.ofm-actions {
  display: flex; gap: 8px; margin-top: 16px;
  padding-top: 16px; border-top: 1px solid #e5e7eb;
}
</style>
