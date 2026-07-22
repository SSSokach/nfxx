<template>
  <div class="form-filler" v-if="visible">
    <div class="filler-overlay" @click="close"></div>
    <div class="filler-modal">
      <div class="filler-header">
        <div>
          <h3>{{ form.title || '在线表格' }}</h3>
          <div class="progress-info">
            <div class="progress-bar-wrap">
              <div class="progress-bar" :style="{ width: progress.percent + '%' }"></div>
            </div>
            <span class="progress-text">{{ progress.filled }}/{{ progress.total }} 已填 ({{ progress.percent }}%)</span>
          </div>
        </div>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="filler-body">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="col in columns" :key="col.key">
                {{ col.label }}
                <span v-if="col.required" class="required-mark">*</span>
              </th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td v-for="col in columns" :key="col.key">
                <template v-if="col.type === 'name'">
                  {{ row.data[col.key] || row.member_name }}
                </template>
                <template v-else-if="editingRowId === row.id">
                  <input v-if="col.type === 'text'"
                         v-model="editData[col.key]" class="cell-input" />
                  <input v-else-if="col.type === 'number'"
                         v-model="editData[col.key]" type="number" class="cell-input" />
                  <input v-else-if="col.type === 'date'"
                         v-model="editData[col.key]" type="date" class="cell-input" />
                  <select v-else-if="col.type === 'select'"
                          v-model="editData[col.key]" class="cell-input">
                    <option value="">请选择</option>
                    <option v-for="opt in col.options" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </template>
                <template v-else>
                  {{ row.data[col.key] || '-' }}
                </template>
              </td>
              <td>
                <span :class="['status-badge', row.filled ? 'done' : 'pending']">
                  {{ row.filled ? '✓ 已填' : '待填' }}
                </span>
              </td>
              <td>
                <button v-if="editingRowId !== row.id" @click="startEdit(row)" class="row-btn">
                  {{ row.filled ? '修改' : '填写' }}
                </button>
                <template v-else>
                  <button @click="saveEdit(row)" class="row-btn save">保存</button>
                  <button @click="cancelEdit" class="row-btn cancel">取消</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="filler-footer">
        <button @click="refresh" class="btn-refresh">🔄 刷新检测</button>
        <button @click="close" class="btn-close">关闭</button>
      </div>
    </div>
  </div>
</template>

<script>
import { onlineFormsApi } from '../api'

export default {
  name: 'FormFiller',
  props: {
    visible: { type: Boolean, default: false },
    formId: { type: Number, default: null },
  },
  emits: ['close', 'refresh'],
  data() {
    return {
      form: {},
      columns: [],
      rows: [],
      editingRowId: null,
      editData: {},
    }
  },
  computed: {
    progress() {
      const total = this.rows.length
      const filled = this.rows.filter(r => r.filled).length
      return { total, filled, percent: total ? Math.round(filled / total * 100) : 0 }
    },
  },
  watch: {
    formId(v) {
      if (v && this.visible) this.load()
    },
    visible(v) {
      if (v && this.formId) this.load()
    },
  },
  methods: {
    async load() {
      try {
        const res = await onlineFormsApi.get(this.formId)
        this.form = res.data
        this.columns = res.data.columns || []
        this.rows = res.data.rows || []
      } catch (e) {
        alert('加载失败: ' + (e.response?.data?.detail || e.message))
      }
    },
    startEdit(row) {
      this.editingRowId = row.id
      this.editData = { ...row.data }
      // 确保 name 列不可改
    },
    cancelEdit() {
      this.editingRowId = null
      this.editData = {}
    },
    async saveEdit(row) {
      try {
        await onlineFormsApi.fill(this.formId, row.member_name, this.editData, row.member_user_id)
        await this.load()
        this.cancelEdit()
        this.$emit('refresh')
      } catch (e) {
        alert('保存失败: ' + (e.response?.data?.detail || e.message))
      }
    },
    async refresh() {
      try {
        await onlineFormsApi.check(this.formId);
        await this.load();
        this.$emit('refresh');
      } catch (e) {
        alert('刷新失败');
      }
    },
    close() {
      this.$emit('close');
    },
  },
}
</script>

<style scoped>
.form-filler { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; }
.filler-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.4); }
.filler-modal { position: relative; background: #fff; border-radius: 16px; width: 95%; max-width: 900px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.filler-header { padding: 18px 24px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: flex-start; }
.filler-header h3 { margin: 0 0 8px 0; font-size: 17px; }
.progress-info { display: flex; align-items: center; gap: 10px; }
.progress-bar-wrap { width: 180px; height: 8px; background: #e2e6f2; border-radius: 99px; overflow: hidden; }
.progress-bar { height: 100%; background: linear-gradient(90deg, #4b8cff, #2ab06f); transition: width 0.3s; }
.progress-text { font-size: 11px; color: #666; }
.close-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #999; }
.filler-body { padding: 16px 24px; overflow: auto; flex: 1; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #f0f4ff; padding: 10px 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #d0dbf0; position: sticky; top: 0; }
.required-mark { color: #ef4444; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid #f0f2f8; color: #444; }
.status-badge { padding: 2px 8px; border-radius: 99px; font-size: 11px; font-weight: 600; }
.status-badge.done { background: #d1fae5; color: #065f46; }
.status-badge.pending { background: #fef3c7; color: #92400e; }
.cell-input { width: 100%; padding: 5px 8px; border: 1px solid #4b8cff; border-radius: 4px; font-size: 12px; }
.row-btn { padding: 4px 10px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fc; cursor: pointer; font-size: 11px; margin-right: 4px; }
.row-btn.save { background: #667eea; color: #fff; border-color: #667eea; }
.row-btn.cancel { background: #fee; color: #c33; }
.filler-footer { padding: 14px 24px; border-top: 1px solid #eee; display: flex; justify-content: flex-end; gap: 10px; }
.btn-refresh, .btn-close { padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; border: 1px solid #ddd; }
.btn-refresh { background: #f8f9fc; }
.btn-close { background: #f5f5f5; }
</style>
