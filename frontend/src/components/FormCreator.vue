<template>
  <div class="form-creator" v-if="visible">
    <div class="creator-overlay" @click="close"></div>
    <div class="creator-modal">
      <div class="creator-header">
        <h3>📋 创建在线表格</h3>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="creator-body">
        <!-- 模式切换 -->
        <div class="mode-switcher">
          <button :class="['mode-btn', { active: mode === 'manual' }]" @click="switchMode('manual')">
            ✏️ 手动创建
          </button>
          <button :class="['mode-btn', { active: mode === 'excel' }]" @click="switchMode('excel')">
            📊 从 Excel 导入
          </button>
        </div>

        <!-- 基本信息（两种模式共用） -->
        <div class="form-section">
          <label class="section-label">表格标题</label>
          <input v-model="form.title" :placeholder="mode === 'excel' ? '不填则用文件名' : '如：项目周报收集'" class="title-input" />
        </div>

        <div class="form-section">
          <label class="section-label">所在群聊</label>
          <select v-model="form.contactId" class="select-input" @change="onContactChange">
            <option value="">请选择群聊</option>
            <option v-for="c in groupChats" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>

        <div class="form-section">
          <label class="section-label">截止日期（可选）</label>
          <input v-model="form.deadline" type="date" class="title-input" />
        </div>

        <!-- ===== Excel 模式 ===== -->
        <template v-if="mode === 'excel'">
          <div class="form-section">
            <label class="section-label">
              上传 Excel 文件
              <span class="hint">AI 自动识别表头和人员</span>
            </label>
            <div class="excel-upload-area" @click="$refs.excelInput.click()">
              <input ref="excelInput" type="file" accept=".xlsx,.xls" @change="onExcelUpload" style="display:none" />
              <div v-if="!excelFile" class="upload-placeholder">
                <span class="upload-icon">📁</span>
                <span>点击选择 Excel 文件（.xlsx / .xls）</span>
              </div>
              <div v-else class="upload-info">
                <span class="file-icon">📊</span>
                <span class="file-name">{{ excelFile.name }}</span>
                <button class="file-remove" @click.stop="clearExcel">✕</button>
              </div>
            </div>
          </div>

          <!-- Excel 解析结果 -->
          <div v-if="excelParsing" class="form-section">
            <div class="parsing-hint">🔍 AI 正在解析 Excel...</div>
          </div>

          <div v-if="excelResult" class="form-section">
            <label class="section-label">
              解析结果
              <span class="hint success">✓ 识别到 {{ excelResult.required_members.length }} 人</span>
            </label>
            <div class="excel-result">
              <div class="result-row">
                <span class="result-label">列结构：</span>
                <div class="result-cols">
                  <span v-for="col in excelResult.columns" :key="col.key" class="result-col-tag">{{ col.label }}</span>
                </div>
              </div>
              <div class="result-row">
                <span class="result-label">人员名单：</span>
                <div class="result-members">
                  <span v-for="m in excelResult.required_members" :key="m" class="result-member-tag">{{ m }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- ===== 手动模式 ===== -->
        <template v-if="mode === 'manual'">
          <!-- 列定义 -->
          <div class="form-section">
            <label class="section-label">
              列定义
              <span class="hint">姓名列自动添加，其余列请自定义</span>
            </label>
            <div class="columns-list">
              <div v-for="(col, idx) in form.columns" :key="idx" class="col-row">
                <input v-model="col.label" placeholder="列名（如：周报）" class="col-label-input" />
                <select v-model="col.type" class="col-type-select" :disabled="col.type === 'name'">
                  <option value="text">文本</option>
                  <option value="number">数字</option>
                  <option value="date">日期</option>
                  <option value="select">下拉选择</option>
                </select>
                <input v-if="col.type === 'select'"
                       v-model="col.optionsText"
                       placeholder="选项，逗号分隔"
                       class="col-options-input" />
                <label class="col-required">
                  <input type="checkbox" v-model="col.required" :disabled="col.type === 'name'" />
                  <span>必填</span>
                </label>
                <button v-if="col.type !== 'name'" @click="removeColumn(idx)" class="col-remove-btn">✕</button>
              </div>
              <button @click="addColumn" class="add-col-btn">+ 添加列</button>
            </div>
          </div>

          <!-- 待填写人 -->
          <div class="form-section">
            <label class="section-label">
              待填写人
              <span class="hint">{{ form.contactId ? '从群成员选择或手动输入' : '请先选择群聊' }}</span>
            </label>
            <div class="members-picker">
              <div class="members-tags">
                <span v-for="(m, idx) in form.requiredMembers" :key="idx" class="member-tag">
                  {{ m }}
                  <button @click="removeMember(idx)" class="tag-remove">×</button>
                </span>
                <span v-if="form.requiredMembers.length === 0" class="members-empty">暂未选择</span>
              </div>
              <div class="member-input-row">
                <select v-model="selectedMember" @change="addMember" class="member-select" :disabled="!form.contactId">
                  <option value="">+ 选择群成员</option>
                  <option v-for="m in availableMembers" :key="m.id || m" :value="typeof m === 'object' ? m.name : m">
                    {{ typeof m === 'object' ? m.name : m }}
                  </option>
                </select>
                <button v-if="form.contactId && groupMembers.length > 0" @click="addAllMembers" class="add-all-btn">
                  全选
                </button>
                <input v-model="manualMember" @keyup.enter="addManualMember"
                       placeholder="或手动输入姓名" class="member-manual-input" />
              </div>
              <div v-if="form.contactId && groupMembers.length === 0" class="no-members-hint">
                该群聊暂无成员数据
              </div>
            </div>
          </div>

          <!-- 预览 -->
          <div class="form-section" v-if="form.columns.length && form.requiredMembers.length">
            <label class="section-label">预览</label>
            <div class="preview-table">
              <table>
                <thead>
                  <tr>
                    <th v-for="col in previewColumns" :key="col.key">{{ col.label }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="m in form.requiredMembers.slice(0, 3)" :key="m">
                    <td v-for="col in previewColumns" :key="col.key">
                      {{ col.key === 'name' ? m : '' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>

      <div class="creator-footer">
        <button @click="close" class="btn-cancel">取消</button>
        <button @click="submit" :disabled="!canSubmit" class="btn-submit">
          {{ mode === 'excel' ? '📊 从 Excel 创建' : '📋 创建并发送追踪' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { filesApi, onlineFormsApi, chatsApi } from '../api'

export default {
  name: 'FormCreator',
  props: {
    visible: { type: Boolean, default: false },
    groupChats: { type: Array, default: () => [] },
    groupMembers: { type: Array, default: () => [] },
    currentUserId: { type: Number, default: 1 },
  },
  emits: ['close', 'created'],
  data() {
    return {
      mode: 'manual',
      form: this.emptyForm(),
      selectedMember: '',
      manualMember: '',
      excelFile: null,
      excelParsing: false,
      excelResult: null,
      uploadedFileId: null,
      localGroupMembers: [],
    }
  },
  computed: {
    availableMembers() {
      const selected = new Set(this.form.requiredMembers)
      const members = this.localGroupMembers.length > 0 ? this.localGroupMembers : this.groupMembers
      return members.filter(m => {
        const name = typeof m === 'object' ? m.name : m
        return !selected.has(name)
      })
    },
    previewColumns() {
      const cols = [{ key: 'name', label: '姓名', type: 'name' }]
      this.form.columns.forEach((c, i) => {
        cols.push({ key: `col_${i}`, label: c.label || `列${i+1}`, type: c.type })
      })
      return cols
    },
    canSubmit() {
      if (this.mode === 'excel') {
        return this.form.contactId && this.excelResult && this.uploadedFileId
      }
      return this.form.title && this.form.contactId && this.form.requiredMembers.length > 0
    },
  },
  watch: {
    visible(v) {
      if (v) {
        this.form = this.emptyForm()
        this.excelFile = null
        this.excelResult = null
        this.uploadedFileId = null
        this.localGroupMembers = []
      }
    },
  },
  methods: {
    emptyForm() {
      return {
        title: '',
        contactId: '',
        deadline: '',
        columns: [
          { label: '周报内容', type: 'text', required: true, optionsText: '' },
        ],
        requiredMembers: [],
      }
    },
    switchMode(m) {
      this.mode = m
      this.excelFile = null
      this.excelResult = null
      this.uploadedFileId = null
    },
    async onContactChange() {
      // 选择群聊后动态加载该群的真实成员
      if (!this.form.contactId) {
        this.localGroupMembers = []
        return
      }
      try {
        const res = await chatsApi.getGroupMembers(this.form.contactId)
        this.localGroupMembers = res.data || []
      } catch (e) {
        this.localGroupMembers = []
      }
    },
    addColumn() {
      this.form.columns.push({ label: '', type: 'text', required: false, optionsText: '' })
    },
    removeColumn(idx) {
      this.form.columns.splice(idx, 1)
    },
    addMember() {
      if (this.selectedMember && !this.form.requiredMembers.includes(this.selectedMember)) {
        this.form.requiredMembers.push(this.selectedMember)
      }
      this.selectedMember = ''
    },
    addAllMembers() {
      const members = this.localGroupMembers.length > 0 ? this.localGroupMembers : this.groupMembers
      members.forEach(m => {
        const name = typeof m === 'object' ? m.name : m
        if (name && !this.form.requiredMembers.includes(name)) {
          this.form.requiredMembers.push(name)
        }
      })
    },
    addManualMember() {
      const name = this.manualMember.trim()
      if (name && !this.form.requiredMembers.includes(name)) {
        this.form.requiredMembers.push(name)
      }
      this.manualMember = ''
    },
    removeMember(idx) {
      this.form.requiredMembers.splice(idx, 1)
    },
    async onExcelUpload(e) {
      const file = e.target.files[0]
      if (!file) return
      this.excelFile = file
      this.excelParsing = true
      this.excelResult = null
      try {
        // 上传文件
        const formData = new FormData()
        formData.append('file', file)
        const uploadRes = await filesApi.upload(this.currentUserId, formData)
        this.uploadedFileId = uploadRes.data.id || uploadRes.data.file_id
        // 调用 create-from-excel 预览（先不创建，用 GET 解析）
        // 实际上我们直接在 submit 时创建，这里只做预览
        // 用 filesApi.getExcel 读取并模拟解析
        const excelRes = await filesApi.getExcel(this.uploadedFileId)
        const sheets = excelRes.data.sheets || []
        if (sheets.length === 0) {
          alert('Excel 文件无有效数据')
          this.clearExcel()
          return
        }
        const rows = sheets[0].rows || []
        if (rows.length < 2) {
          alert('Excel 至少需要表头 + 1 行数据')
          this.clearExcel()
          return
        }
        const headers = rows[0].map(c => String(c || '').trim()).filter(Boolean)
        // 识别姓名列
        const nameColIdx = headers.findIndex(h =>
          ['姓名', '名字', 'name', 'Name', 'NAME', '员工姓名'].includes(h)
        )
        const nameIdx = nameColIdx >= 0 ? nameColIdx : 0
        const members = []
        for (let i = 1; i < rows.length; i++) {
          const name = String(rows[i][nameIdx] || '').trim()
          if (name) members.push(name)
        }
        const uniqueMembers = [...new Set(members)]
        const columns = headers.map((h, i) => ({
          key: i === nameIdx ? 'name' : `col_${i}`,
          label: h || `列${i+1}`,
          type: i === nameIdx ? 'name' : 'text',
        }))
        this.excelResult = {
          columns,
          required_members: uniqueMembers,
        }
      } catch (e) {
        alert('Excel 解析失败: ' + (e.response?.data?.detail || e.message))
        this.clearExcel()
      }
      this.excelParsing = false
    },
    clearExcel() {
      this.excelFile = null
      this.excelResult = null
      this.uploadedFileId = null
      if (this.$refs.excelInput) this.$refs.excelInput.value = ''
    },
    async submit() {
      if (this.mode === 'excel') {
        // Excel 模式：调用 create-from-excel
        const payload = {
          creator_id: this.currentUserId,
          contact_id: parseInt(this.form.contactId),
          file_id: this.uploadedFileId,
          title: this.form.title || null,
          deadline: this.form.deadline || null,
        }
        this.$emit('created', { type: 'excel', payload })
      } else {
        // 手动模式
        const columns = [
          { key: 'name', label: '姓名', type: 'name', required: true, editable: false },
          ...this.form.columns.map((c, i) => ({
            key: `col_${i}`,
            label: c.label,
            type: c.type,
            required: c.required,
            editable: true,
            options: c.type === 'select' && c.optionsText
              ? c.optionsText.split(',').map(s => s.trim()).filter(Boolean)
              : undefined,
          })),
        ]
        const payload = {
          creator_id: this.currentUserId,
          contact_id: parseInt(this.form.contactId),
          title: this.form.title,
          columns,
          required_members: this.form.requiredMembers,
          deadline: this.form.deadline || null,
          send_message: true,
        }
        this.$emit('created', { type: 'manual', payload })
      }
    },
    close() {
      this.$emit('close')
    },
  },
}
</script>

<style scoped>
.form-creator { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; }
.creator-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.4); }
.creator-modal { position: relative; background: #fff; border-radius: 16px; width: 90%; max-width: 680px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.creator-header { padding: 18px 24px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.creator-header h3 { margin: 0; font-size: 17px; }
.close-btn { background: none; border: none; font-size: 22px; cursor: pointer; color: #999; }
.creator-body { padding: 20px 24px; overflow-y: auto; flex: 1; }

.mode-switcher { display: flex; gap: 8px; margin-bottom: 18px; background: #f0f2f8; border-radius: 10px; padding: 4px; }
.mode-btn { flex: 1; padding: 10px; border: none; background: transparent; border-radius: 8px; cursor: pointer; font-size: 13px; color: #666; transition: all 0.2s; }
.mode-btn.active { background: #fff; color: #333; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }

.form-section { margin-bottom: 18px; }
.section-label { display: block; font-size: 13px; font-weight: 600; color: #333; margin-bottom: 6px; }
.hint { font-size: 11px; font-weight: 400; color: #999; margin-left: 6px; }
.hint.success { color: #10b981; }
.title-input, .select-input { width: 100%; padding: 9px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; }

.excel-upload-area { border: 2px dashed #c8d3f0; border-radius: 12px; padding: 28px; text-align: center; cursor: pointer; transition: all 0.2s; background: #f8faff; }
.excel-upload-area:hover { border-color: #4b8cff; background: #f0f6ff; }
.upload-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #888; font-size: 13px; }
.upload-icon { font-size: 32px; }
.upload-info { display: flex; align-items: center; gap: 8px; justify-content: center; }
.file-icon { font-size: 20px; }
.file-name { font-size: 13px; color: #333; font-weight: 600; }
.file-remove { background: #fee; border: 1px solid #fcc; color: #c33; width: 22px; height: 22px; border-radius: 99px; cursor: pointer; font-size: 12px; }

.parsing-hint { padding: 12px; background: #f0f6ff; border-radius: 8px; color: #4b8cff; font-size: 13px; text-align: center; }

.excel-result { background: #f8faff; border: 1px solid #e2e8f5; border-radius: 10px; padding: 14px; }
.result-row { margin-bottom: 10px; }
.result-row:last-child { margin-bottom: 0; }
.result-label { font-size: 12px; font-weight: 600; color: #555; display: block; margin-bottom: 6px; }
.result-cols { display: flex; flex-wrap: wrap; gap: 6px; }
.result-col-tag { background: #e0e7ff; color: #4338ca; padding: 3px 8px; border-radius: 6px; font-size: 11px; }
.result-members { display: flex; flex-wrap: wrap; gap: 4px; }
.result-member-tag { background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 99px; font-size: 11px; }

.columns-list { display: flex; flex-direction: column; gap: 8px; }
.col-row { display: flex; gap: 8px; align-items: center; }
.col-label-input { flex: 1.5; padding: 7px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 12px; }
.col-type-select { width: 90px; padding: 7px 8px; border: 1px solid #ddd; border-radius: 6px; font-size: 12px; }
.col-options-input { flex: 1.5; padding: 7px 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 11px; }
.col-required { display: flex; align-items: center; gap: 3px; font-size: 11px; color: #666; white-space: nowrap; }
.col-required input { margin: 0; }
.col-remove-btn { background: #fee; border: 1px solid #fcc; color: #c33; width: 24px; height: 24px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.add-col-btn { padding: 7px 14px; background: #f0f4ff; border: 1px dashed #6b8cff; color: #4b8cff; border-radius: 8px; cursor: pointer; font-size: 12px; align-self: flex-start; }

.members-picker { display: flex; flex-direction: column; gap: 8px; }
.members-tags { display: flex; flex-wrap: wrap; gap: 6px; min-height: 32px; padding: 6px; background: #f8f9fc; border: 1px solid #e2e6f2; border-radius: 8px; }
.members-empty { color: #bbb; font-size: 12px; padding: 4px; }
.member-tag { display: inline-flex; align-items: center; gap: 4px; background: #667eea; color: #fff; padding: 3px 10px; border-radius: 99px; font-size: 12px; }
.tag-remove { background: none; border: none; color: #fff; cursor: pointer; font-size: 14px; opacity: 0.8; }
.member-input-row { display: flex; gap: 8px; align-items: center; }
.member-select { flex: 1; padding: 7px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 12px; }
.add-all-btn { padding: 7px 12px; background: #e0e7ff; border: 1px solid #c7d2fe; color: #4338ca; border-radius: 8px; cursor: pointer; font-size: 12px; white-space: nowrap; }
.member-manual-input { flex: 1; padding: 7px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 12px; }
.no-members-hint { font-size: 11px; color: #aaa; padding: 4px; }

.preview-table { overflow-x: auto; border: 1px solid #e2e6f2; border-radius: 8px; }
.preview-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
.preview-table th { background: #f0f4ff; padding: 8px 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 1px solid #e2e6f2; }
.preview-table td { padding: 8px 12px; border-bottom: 1px solid #f0f2f8; color: #666; }

.creator-footer { padding: 14px 24px; border-top: 1px solid #eee; display: flex; justify-content: flex-end; gap: 10px; }
.btn-cancel { padding: 9px 18px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 8px; cursor: pointer; font-size: 13px; }
.btn-submit { padding: 9px 18px; background: linear-gradient(135deg, #667eea, #7c4dca); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
