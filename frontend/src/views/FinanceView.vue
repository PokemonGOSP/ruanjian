<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import {
  createFinanceRecord,
  listFinanceRecords,
  summarizeFinance,
  updateFinanceRecord,
  voidFinanceRecord,
} from '../api/finance.js'
import { formatAmount, formatDate, todayInput } from '../utils/format.js'

const PAGE_SIZE = 20
const typeLabels = { INCOME: '收入', EXPENSE: '支出' }
const statusLabels = { ACTIVE: '有效', VOIDED: '已作废' }

const auth = useAuthStore()
const leaderClubs = computed(() => auth.user?.club_authorizations || [])
const isManager = computed(() => Boolean(auth.user?.system_roles?.includes('R03')))
const canManage = computed(() => leaderClubs.value.length > 0)
const canView = computed(() => isManager.value || canManage.value)
const managedClubIds = computed(() => new Set(leaderClubs.value.map((club) => club.club_id)))

const records = ref([])
const total = ref(0)
const page = ref(1)
const summary = ref(null)
const loading = ref(false)
const error = ref('')
const message = ref('')

const filters = reactive({
  club_id: '',
  record_type: '',
  status: '',
  date_from: '',
  date_to: '',
})
const form = reactive({
  club_id: '',
  activity_id: '',
  record_type: 'EXPENSE',
  amount: '',
  occurred_on: todayInput(),
  description: '',
  voucher_reference: '',
})
const editingId = ref(null)

watch(
  leaderClubs,
  (clubs) => {
    if (clubs.length && !form.club_id) form.club_id = clubs[0].club_id
  },
  { immediate: true },
)

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function filterParams(withPaging = true) {
  const params = {}
  if (filters.club_id !== '' && filters.club_id !== null) params.club_id = Number(filters.club_id)
  if (filters.record_type) params.record_type = filters.record_type
  if (filters.status) params.status = filters.status
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  if (withPaging) {
    params.page = page.value
    params.page_size = PAGE_SIZE
  }
  return params
}

function showError(reason) {
  error.value = reason?.message || '操作失败，请稍后重试'
}

async function load() {
  if (!canView.value) return
  loading.value = true
  error.value = ''
  try {
    const [listResponse, summaryResponse] = await Promise.all([
      listFinanceRecords(filterParams(true)),
      summarizeFinance(filterParams(false)),
    ])
    records.value = listResponse.data.data.items
    total.value = listResponse.data.data.total
    summary.value = summaryResponse.data.data
  } catch (reason) {
    showError(reason)
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  load()
}

function changePage(offset) {
  const next = page.value + offset
  if (next < 1 || next > pageCount.value) return
  page.value = next
  load()
}

function canEditRow(row) {
  return canManage.value && managedClubIds.value.has(row.club_id) && row.status === 'ACTIVE'
}

function resetForm() {
  editingId.value = null
  form.activity_id = ''
  form.record_type = 'EXPENSE'
  form.amount = ''
  form.occurred_on = todayInput()
  form.description = ''
  form.voucher_reference = ''
  form.club_id = leaderClubs.value[0]?.club_id ?? ''
}

function startEdit(row) {
  message.value = ''
  error.value = ''
  editingId.value = row.id
  form.club_id = row.club_id
  form.activity_id = row.activity_id ?? ''
  form.record_type = row.record_type
  form.amount = row.amount
  form.occurred_on = formatDate(row.occurred_on)
  form.description = row.description
  form.voucher_reference = row.voucher_reference || ''
}

async function submit() {
  error.value = ''
  message.value = ''
  if (!editingId.value && !form.club_id) {
    error.value = '请选择社团'
    return
  }
  if (!form.description.trim()) {
    error.value = '请填写收支说明'
    return
  }
  if (!form.amount || Number(form.amount) <= 0) {
    error.value = '金额必须大于 0'
    return
  }
  if (!form.occurred_on) {
    error.value = '请选择发生日期'
    return
  }
  const payload = {
    record_type: form.record_type,
    amount: String(form.amount),
    occurred_on: `${form.occurred_on}T00:00:00`,
    description: form.description.trim(),
    activity_id: form.activity_id ? Number(form.activity_id) : null,
    voucher_reference: form.voucher_reference.trim() || null,
  }
  try {
    if (editingId.value) {
      await updateFinanceRecord(editingId.value, payload)
      message.value = '经费记录已更新'
    } else {
      await createFinanceRecord({ club_id: Number(form.club_id), ...payload })
      message.value = '经费记录已登记'
    }
    resetForm()
    await load()
  } catch (reason) {
    showError(reason)
  }
}

async function voidRow(row) {
  const reason = window.prompt(`作废经费记录 #${row.id}，请输入作废原因：`)
  if (reason === null) return
  if (!reason.trim()) {
    error.value = '作废原因不能为空'
    return
  }
  error.value = ''
  message.value = ''
  try {
    await voidFinanceRecord(row.id, reason.trim())
    message.value = '经费记录已作废，原记录保留'
    await load()
  } catch (reasonValue) {
    showError(reasonValue)
  }
}

onMounted(() => {
  if (canView.value) load()
})
</script>

<template>
  <section class="card">
    <h2>经费记录（M05）</h2>
    <p class="muted">
      FR-17～FR-18：登记、修改、作废和查询收入/支出记录。仅记账，不包含审批、报销或支付。
      <span v-if="isManager">当前身份为 R03，可查询全部社团，但登记与修改仅限 R02。</span>
    </p>

    <p v-if="!canView" class="muted">当前账号没有经费查询权限。经费查询需要 R02（本社团）或 R03。</p>

    <template v-else>
      <div v-if="summary" class="stat-grid">
      <div class="stat"><span>收入合计</span><strong>{{ formatAmount(summary.income_total) }}</strong></div>
      <div class="stat"><span>支出合计</span><strong>{{ formatAmount(summary.expense_total) }}</strong></div>
      <div class="stat"><span>结余</span><strong>{{ formatAmount(summary.balance) }}</strong></div>
      <div class="stat"><span>有效记录</span><strong>{{ summary.active_record_count }}</strong></div>
      <div class="stat"><span>已作废记录</span><strong>{{ summary.voided_record_count }}</strong></div>
    </div>

    <div class="filters">
      <label>
        社团
        <input
          v-if="isManager"
          v-model="filters.club_id"
          type="number"
          min="1"
          placeholder="社团 ID（留空=全部）"
        />
        <select v-else v-model="filters.club_id">
          <option value="">我的全部社团</option>
          <option v-for="club in leaderClubs" :key="club.club_id" :value="club.club_id">
            {{ club.club_name }}
          </option>
        </select>
      </label>
      <label>
        类型
        <select v-model="filters.record_type">
          <option value="">全部</option>
          <option value="INCOME">收入</option>
          <option value="EXPENSE">支出</option>
        </select>
      </label>
      <label>
        状态
        <select v-model="filters.status">
          <option value="">全部</option>
          <option value="ACTIVE">有效</option>
          <option value="VOIDED">已作废</option>
        </select>
      </label>
      <label>
        开始日期
        <input v-model="filters.date_from" type="date" />
      </label>
      <label>
        结束日期
        <input v-model="filters.date_to" type="date" />
      </label>
      <button class="btn primary" :disabled="loading" @click="applyFilters">查询</button>
    </div>

    <p v-if="error" class="message error">{{ error }}</p>
    <p v-if="message" class="message ok">{{ message }}</p>

    <div v-if="canManage" class="form-panel">
      <h3>{{ editingId ? `编辑记录 #${editingId}` : '登记经费记录' }}</h3>
      <div class="form-grid">
        <label v-if="!editingId">
          社团
          <select v-model="form.club_id">
            <option v-for="club in leaderClubs" :key="club.club_id" :value="club.club_id">
              {{ club.club_name }}
            </option>
          </select>
        </label>
        <label>
          类型
          <select v-model="form.record_type">
            <option value="INCOME">收入</option>
            <option value="EXPENSE">支出</option>
          </select>
        </label>
        <label>
          金额
          <input v-model="form.amount" type="number" min="0.01" step="0.01" placeholder="0.00" />
        </label>
        <label>
          发生日期
          <input v-model="form.occurred_on" type="date" />
        </label>
        <label>
          关联活动 ID（可选）
          <input v-model="form.activity_id" type="number" min="1" placeholder="活动 ID" />
        </label>
        <label class="wide">
          说明
          <input v-model="form.description" maxlength="500" placeholder="例如：社团会费收入" />
        </label>
        <label class="wide">
          凭证附件信息（可选）
          <input v-model="form.voucher_reference" maxlength="255" placeholder="课程原型中的附件说明或编号" />
        </label>
        <div class="form-actions">
          <button class="btn primary" :disabled="loading" @click="submit">
            {{ editingId ? '保存修改' : '登记记录' }}
          </button>
          <button v-if="editingId" class="btn" @click="resetForm">取消编辑</button>
        </div>
      </div>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>社团</th>
          <th>活动</th>
          <th>类型</th>
          <th>金额</th>
          <th>发生日期</th>
          <th>说明</th>
          <th>凭证</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in records" :key="row.id">
          <td>{{ row.id }}</td>
          <td>{{ row.club_name }}</td>
          <td>{{ row.activity_title || (row.activity_id ? `#${row.activity_id}` : '—') }}</td>
          <td>{{ typeLabels[row.record_type] || row.record_type }}</td>
          <td>{{ formatAmount(row.amount) }}</td>
          <td>{{ formatDate(row.occurred_on) }}</td>
          <td>{{ row.description }}</td>
          <td>{{ row.voucher_reference || '—' }}</td>
          <td>
            <span class="badge" :class="row.status === 'ACTIVE' ? 'ok' : 'danger'">
              {{ statusLabels[row.status] || row.status }}
            </span>
            <div v-if="row.void_reason" class="muted">原因：{{ row.void_reason }}</div>
          </td>
          <td>
            <template v-if="canEditRow(row)">
              <button class="btn" @click="startEdit(row)">编辑</button>
              <button class="btn danger" @click="voidRow(row)">作废</button>
            </template>
            <span v-else class="muted">—</span>
          </td>
        </tr>
        <tr v-if="!records.length">
          <td colspan="10" class="muted">暂无符合条件的经费记录。</td>
        </tr>
      </tbody>
    </table>

    <div class="pager">
      <button class="btn" :disabled="page <= 1 || loading" @click="changePage(-1)">上一页</button>
      <span class="muted">第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 条</span>
      <button class="btn" :disabled="page >= pageCount || loading" @click="changePage(1)">下一页</button>
    </div>
    </template>
  </section>
</template>

<style scoped>
.form-panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
  background: #fbfdff;
}
.form-panel h3 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
}
.wide {
  flex: 1 1 260px;
}
.form-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
</style>
