<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { exportReport, listAuditLogs, summarizeReport } from '../api/reports.js'
import { downloadBlob, formatAmount, formatDateTime } from '../utils/format.js'

const AUDIT_PAGE_SIZE = 20
const reviewLabels = {
  DRAFT: '草稿',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  WITHDRAWN: '已撤回',
}
const executionLabels = {
  UNPUBLISHED: '未发布',
  REGISTRATION_OPEN: '报名中',
  REGISTRATION_CLOSED: '报名截止',
  IN_PROGRESS: '进行中',
  ENDED: '已结束',
  CANCELLED: '已取消',
}

const auth = useAuthStore()
const isManager = computed(() => Boolean(auth.user?.system_roles?.includes('R03')))
const isAdmin = computed(() => Boolean(auth.user?.system_roles?.includes('R04')))
const leaderClubs = computed(() => auth.user?.club_authorizations || [])
const canViewReport = computed(() => isManager.value || leaderClubs.value.length > 0)

const summary = ref(null)
const filters = reactive({ club_id: '', date_from: '', date_to: '' })
const loading = ref(false)
const error = ref('')
const message = ref('')

const auditLogs = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditLoading = ref(false)
const auditFilters = reactive({
  actor_user_id: '',
  action: '',
  resource_type: '',
  date_from: '',
  date_to: '',
})

const auditPageCount = computed(() => Math.max(1, Math.ceil(auditTotal.value / AUDIT_PAGE_SIZE)))

function showError(reason) {
  error.value = reason?.message || '操作失败，请稍后重试'
}

function reportParams() {
  const params = {}
  if (filters.club_id !== '' && filters.club_id !== null) params.club_id = Number(filters.club_id)
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  return params
}

async function loadSummary() {
  if (!canViewReport.value) return
  loading.value = true
  error.value = ''
  try {
    const response = await summarizeReport(reportParams())
    summary.value = response.data.data
  } catch (reason) {
    showError(reason)
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  if (!canViewReport.value) return
  error.value = ''
  message.value = ''
  try {
    const response = await exportReport({ ...reportParams(), format: 'csv' })
    downloadBlob(response.data, 'finance-records.csv')
    message.value = 'CSV 报表已开始下载'
  } catch (reason) {
    showError(reason)
  }
}

function auditParams() {
  const params = { page: auditPage.value, page_size: AUDIT_PAGE_SIZE }
  if (auditFilters.actor_user_id !== '') params.actor_user_id = Number(auditFilters.actor_user_id)
  if (auditFilters.action) params.action = auditFilters.action
  if (auditFilters.resource_type) params.resource_type = auditFilters.resource_type
  if (auditFilters.date_from) params.date_from = auditFilters.date_from
  if (auditFilters.date_to) params.date_to = auditFilters.date_to
  return params
}

async function loadAudit() {
  if (!isAdmin.value) return
  auditLoading.value = true
  error.value = ''
  try {
    const response = await listAuditLogs(auditParams())
    auditLogs.value = response.data.data.items
    auditTotal.value = response.data.data.total
  } catch (reason) {
    showError(reason)
  } finally {
    auditLoading.value = false
  }
}

function applyAuditFilters() {
  auditPage.value = 1
  loadAudit()
}

function changeAuditPage(offset) {
  const next = auditPage.value + offset
  if (next < 1 || next > auditPageCount.value) return
  auditPage.value = next
  loadAudit()
}

function detailText(detail) {
  if (detail === null || detail === undefined) return '—'
  if (typeof detail === 'string') return detail
  return JSON.stringify(detail)
}

onMounted(() => {
  if (canViewReport.value) loadSummary()
  if (isAdmin.value) loadAudit()
})
</script>

<template>
  <section class="card">
    <h2>统计与审计（M07）</h2>
    <p class="muted">
      FR-21～FR-22：综合统计覆盖社团、成员、活动、报名与经费；CSV 导出仅包含经费明细。审计日志仅 R04 可查询。
    </p>

    <p v-if="error" class="message error">{{ error }}</p>
    <p v-if="message" class="message ok">{{ message }}</p>

    <template v-if="canViewReport">
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
          开始日期
          <input v-model="filters.date_from" type="date" />
        </label>
        <label>
          结束日期
          <input v-model="filters.date_to" type="date" />
        </label>
        <button class="btn primary" :disabled="loading" @click="loadSummary">查询统计</button>
        <button class="btn" :disabled="loading" @click="exportCsv">导出经费 CSV</button>
      </div>

      <div v-if="summary" class="stat-grid">
        <div class="stat"><span>社团数</span><strong>{{ summary.club_count }}</strong></div>
        <div class="stat"><span>有效成员</span><strong>{{ summary.member_count }}</strong></div>
        <div class="stat"><span>活动数</span><strong>{{ summary.activity_count }}</strong></div>
        <div class="stat"><span>有效报名</span><strong>{{ summary.registration_count }}</strong></div>
        <div class="stat"><span>经费收入</span><strong>{{ formatAmount(summary.finance_income_total) }}</strong></div>
        <div class="stat"><span>经费支出</span><strong>{{ formatAmount(summary.finance_expense_total) }}</strong></div>
        <div class="stat"><span>结余</span><strong>{{ formatAmount(summary.finance_balance) }}</strong></div>
        <div class="stat"><span>作废记录</span><strong>{{ summary.finance_voided_count }}</strong></div>
      </div>

      <div v-if="summary" class="distribution">
        <div>
          <h4>活动审核状态</h4>
          <table class="data-table">
            <tbody>
              <tr v-for="(count, key) in summary.activity_by_review_status" :key="key">
                <td>{{ reviewLabels[key] || key }}</td>
                <td>{{ count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <h4>活动执行状态</h4>
          <table class="data-table">
            <tbody>
              <tr v-for="(count, key) in summary.activity_by_execution_status" :key="key">
                <td>{{ executionLabels[key] || key }}</td>
                <td>{{ count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <p class="muted">
        日期口径：活动按开始时间、经费按发生日期、报名按所属活动开始时间；成员数为当前有效成员。
      </p>
    </template>

    <template v-if="isAdmin">
      <h3 class="section-title">审计日志（R04）</h3>
      <div class="filters">
        <label>
          操作人 ID
          <input v-model="auditFilters.actor_user_id" type="number" min="1" placeholder="用户 ID" />
        </label>
        <label>
          动作
          <input v-model="auditFilters.action" maxlength="100" placeholder="例如 FINANCE_RECORD_VOIDED" />
        </label>
        <label>
          资源类型
          <input v-model="auditFilters.resource_type" maxlength="100" placeholder="例如 finance_record" />
        </label>
        <label>
          开始日期
          <input v-model="auditFilters.date_from" type="date" />
        </label>
        <label>
          结束日期
          <input v-model="auditFilters.date_to" type="date" />
        </label>
        <button class="btn primary" :disabled="auditLoading" @click="applyAuditFilters">查询</button>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>动作</th>
            <th>资源</th>
            <th>资源 ID</th>
            <th>详情</th>
            <th>IP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in auditLogs" :key="row.id">
            <td>{{ formatDateTime(row.created_at) }}</td>
            <td>{{ row.actor_username || row.actor_user_id || '—' }}</td>
            <td>{{ row.action }}</td>
            <td>{{ row.resource_type }}</td>
            <td>{{ row.resource_id || '—' }}</td>
            <td class="detail">{{ detailText(row.detail) }}</td>
            <td>{{ row.ip_address || '—' }}</td>
          </tr>
          <tr v-if="!auditLogs.length">
            <td colspan="7" class="muted">暂无审计记录。</td>
          </tr>
        </tbody>
      </table>

      <div class="pager">
        <button class="btn" :disabled="auditPage <= 1 || auditLoading" @click="changeAuditPage(-1)">
          上一页
        </button>
        <span class="muted">
          第 {{ auditPage }} / {{ auditPageCount }} 页，共 {{ auditTotal }} 条
        </span>
        <button
          class="btn"
          :disabled="auditPage >= auditPageCount || auditLoading"
          @click="changeAuditPage(1)"
        >
          下一页
        </button>
      </div>
    </template>

    <p v-if="!canViewReport && !isAdmin" class="muted">
      当前账号没有统计或审计权限。统计需要 R02（本社团）或 R03；审计需要 R04。
    </p>
  </section>
</template>

<style scoped>
.distribution {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.distribution h4 {
  margin: 0 0 0.35rem;
  font-size: 0.95rem;
}
.section-title {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
  font-size: 1.05rem;
}
.detail {
  max-width: 320px;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.8rem;
}
</style>
