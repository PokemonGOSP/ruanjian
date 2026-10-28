<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import {
  cancelActivity,
  cancelRegistration,
  createActivity,
  endActivity,
  listActivities,
  listRegistrations,
  publishActivity,
  registerActivity,
  reviewActivity,
  submitActivity,
  updateActivity,
  withdrawActivity,
} from '../api/activities.js'

const REVIEW_LABELS = {
  DRAFT: '草稿',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  WITHDRAWN: '已撤回',
}
const EXECUTION_LABELS = {
  UNPUBLISHED: '未发布',
  REGISTRATION_OPEN: '报名中',
  REGISTRATION_CLOSED: '报名截止',
  IN_PROGRESS: '进行中',
  ENDED: '已结束',
  CANCELLED: '已取消',
}
const REVIEW_CLASS = {
  DRAFT: 'draft',
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  WITHDRAWN: 'withdrawn',
}
const EXECUTION_CLASS = {
  UNPUBLISHED: 'draft',
  REGISTRATION_OPEN: 'open',
  REGISTRATION_CLOSED: 'closed',
  IN_PROGRESS: 'progress',
  ENDED: 'ended',
  CANCELLED: 'cancelled',
}

const auth = useAuthStore()
const activities = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const notice = ref('')

const isManager = computed(() => auth.user?.system_roles?.includes('R03'))
const clubOptions = computed(() => auth.user?.club_authorizations ?? [])
const leaderClubIds = computed(() => new Set(clubOptions.value.map((club) => club.club_id)))
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const canCreate = computed(() => clubOptions.value.length > 0)

function blankForm() {
  return {
    club_id: clubOptions.value[0]?.club_id ?? '',
    title: '',
    description: '',
    location: '',
    starts_at: '',
    ends_at: '',
    registration_deadline: '',
    capacity: '',
    budget: '0',
  }
}

const form = reactive(blankForm())
const showForm = ref(false)
const editingId = ref(null)
const formError = ref('')

const reviewTarget = ref(null)
const reviewForm = reactive({ decision: 'APPROVED', comment: '' })
const cancelTarget = ref(null)
const cancelReason = ref('')
const endTarget = ref(null)
const endSummary = ref('')
const detailsTarget = ref(null)
const rosterTarget = ref(null)
const roster = ref([])
const rosterTotal = ref(0)
const rosterPage = ref(1)
const rosterPageSize = 10

function messageOf(err) {
  return err?.message || err?.response?.data?.message || '操作失败，请稍后重试'
}

function reviewLabel(status) {
  return REVIEW_LABELS[status] || status
}

function executionLabel(status) {
  return EXECUTION_LABELS[status] || status
}

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function toInputValue(value) {
  return value ? value.slice(0, 16) : ''
}

function clubName(clubId) {
  return clubOptions.value.find((club) => club.club_id === clubId)?.club_name || `社团 #${clubId}`
}

function isClubLeader(activity) {
  return leaderClubIds.value.has(activity.club_id)
}

function canEdit(activity) {
  return isClubLeader(activity) && ['DRAFT', 'WITHDRAWN'].includes(activity.review_status)
}

function canSubmit(activity) {
  return canEdit(activity)
}

function canWithdraw(activity) {
  return isClubLeader(activity) && activity.review_status === 'PENDING'
}

function canReview(activity) {
  return isManager.value && activity.review_status === 'PENDING'
}

function canPublish(activity) {
  return isClubLeader(activity) && activity.review_status === 'APPROVED'
    && activity.execution_status === 'UNPUBLISHED'
}

function canRegister(activity) {
  return activity.execution_status === 'REGISTRATION_OPEN'
    && activity.my_registration_status !== 'REGISTERED'
}

function canCancelRegistration(activity) {
  return activity.my_registration_status === 'REGISTERED'
    && !['ENDED', 'CANCELLED'].includes(activity.execution_status)
}

function canCancel(activity) {
  return isClubLeader(activity) && activity.review_status === 'APPROVED'
    && !['ENDED', 'CANCELLED'].includes(activity.execution_status)
}

function canEnd(activity) {
  return isClubLeader(activity) && activity.review_status === 'APPROVED'
    && ['REGISTRATION_CLOSED', 'IN_PROGRESS'].includes(activity.execution_status)
}

function canViewRoster(activity) {
  return isClubLeader(activity)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listActivities({ page: page.value, page_size: pageSize })
    activities.value = data.items
    total.value = data.total
    if (!data.items.length && page.value > 1) {
      page.value -= 1
      await load()
    }
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    loading.value = false
  }
}

function goPage(nextPage) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) return
  page.value = nextPage
  load()
}

function openCreate() {
  Object.assign(form, blankForm())
  editingId.value = null
  formError.value = ''
  showForm.value = true
}

function openEdit(activity) {
  Object.assign(form, {
    club_id: activity.club_id,
    title: activity.title,
    description: activity.description,
    location: activity.location,
    starts_at: toInputValue(activity.starts_at),
    ends_at: toInputValue(activity.ends_at),
    registration_deadline: toInputValue(activity.registration_deadline),
    capacity: activity.capacity ?? '',
    budget: String(activity.budget ?? 0),
  })
  editingId.value = activity.id
  formError.value = ''
  showForm.value = true
}

function closeForm() {
  if (busy.value) return
  showForm.value = false
}

async function saveForm() {
  formError.value = ''
  if (!form.title.trim() || !form.description.trim() || !form.location.trim()) {
    formError.value = '请填写活动名称、方案说明和地点'
    return
  }
  if (!form.starts_at || !form.ends_at) {
    formError.value = '请填写活动开始和结束时间'
    return
  }

  const payload = {
    title: form.title.trim(),
    description: form.description.trim(),
    location: form.location.trim(),
    starts_at: form.starts_at,
    ends_at: form.ends_at,
    registration_deadline: form.registration_deadline || null,
    capacity: form.capacity === '' ? null : Number(form.capacity),
    budget: form.budget === '' ? 0 : Number(form.budget),
  }

  busy.value = true
  try {
    if (editingId.value) {
      await updateActivity(editingId.value, payload)
      notice.value = '活动草稿已更新'
    } else {
      await createActivity({ club_id: Number(form.club_id), ...payload })
      notice.value = '活动草稿已创建，可提交审核'
    }
    showForm.value = false
    await load()
  } catch (err) {
    formError.value = messageOf(err)
  } finally {
    busy.value = false
  }
}

async function runAction(action, successMessage) {
  busy.value = true
  error.value = ''
  try {
    await action()
    notice.value = successMessage
    await load()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    busy.value = false
  }
}

function submit(activity) {
  runAction(() => submitActivity(activity.id), '已提交审核')
}

function withdraw(activity) {
  runAction(() => withdrawActivity(activity.id), '已撤回活动申请')
}

function publish(activity) {
  runAction(() => publishActivity(activity.id), '活动已发布，进入报名中')
}

function register(activity) {
  runAction(() => registerActivity(activity.id), '报名成功')
}

function unregister(activity) {
  runAction(() => cancelRegistration(activity.id), '已取消报名')
}

function openReview(activity) {
  reviewTarget.value = activity
  reviewForm.decision = 'APPROVED'
  reviewForm.comment = ''
}

async function confirmReview() {
  if (!reviewTarget.value) return
  busy.value = true
  error.value = ''
  try {
    await reviewActivity(reviewTarget.value.id, reviewForm.decision, reviewForm.comment || null)
    notice.value = reviewForm.decision === 'APPROVED' ? '活动审核已通过' : '活动审核已驳回'
    reviewTarget.value = null
    await load()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    busy.value = false
  }
}

function openCancel(activity) {
  cancelTarget.value = activity
  cancelReason.value = ''
}

async function confirmCancel() {
  if (!cancelTarget.value) return
  if (!cancelReason.value.trim()) {
    error.value = '取消活动必须填写原因'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await cancelActivity(cancelTarget.value.id, cancelReason.value.trim())
    notice.value = '活动已取消，已报名用户会收到站内通知'
    cancelTarget.value = null
    await load()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    busy.value = false
  }
}

function openEnd(activity) {
  endTarget.value = activity
  endSummary.value = activity.summary || ''
}

async function confirmEnd() {
  if (!endTarget.value) return
  busy.value = true
  error.value = ''
  try {
    await endActivity(endTarget.value.id, endSummary.value || null)
    notice.value = '活动已结束并归档'
    endTarget.value = null
    await load()
  } catch (err) {
    error.value = messageOf(err)
  } finally {
    busy.value = false
  }
}

async function openRoster(activity) {
  rosterTarget.value = activity
  rosterPage.value = 1
  roster.value = []
  rosterTotal.value = 0
  await loadRoster()
}

async function loadRoster() {
  if (!rosterTarget.value) return
  try {
    const data = await listRegistrations(rosterTarget.value.id, {
      page: rosterPage.value,
      page_size: rosterPageSize,
    })
    roster.value = data.items
    rosterTotal.value = data.total
  } catch (err) {
    error.value = messageOf(err)
  }
}

function rosterGo(nextPage) {
  rosterPage.value = nextPage
  loadRoster()
}

onMounted(load)
</script>

<template>
  <section class="card activity-page">
    <header class="page-head">
      <div>
        <h2>活动管理</h2>
        <p class="meta">M04 · FR-11～FR-16：申报、审核、发布、报名与取消/归档</p>
      </div>
      <button v-if="canCreate" class="primary" :disabled="busy" @click="openCreate">+ 新建活动</button>
    </header>

    <p v-if="error" class="banner error">{{ error }}</p>
    <p v-if="notice" class="banner notice">{{ notice }}</p>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>活动</th>
            <th>时间</th>
            <th>地点 / 容量 / 预算</th>
            <th>状态</th>
            <th>报名</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="activity in activities" :key="activity.id">
            <td class="activity-cell">
              <strong>{{ activity.title }}</strong>
              <small>{{ clubName(activity.club_id) }} · 创建人 #{{ activity.created_by }}</small>
              <small class="clamp">{{ activity.description }}</small>
            </td>
            <td class="nowrap">
              {{ formatDateTime(activity.starts_at) }}<br />
              <small>至 {{ formatDateTime(activity.ends_at) }}</small><br />
              <small>报名截止：{{ formatDateTime(activity.registration_deadline) }}</small>
            </td>
            <td>
              {{ activity.location }}<br />
              <small>容量：{{ activity.capacity ?? '不限' }}</small><br />
              <small>预算：￥{{ activity.budget }}</small>
            </td>
            <td class="nowrap">
              <span class="badge" :class="REVIEW_CLASS[activity.review_status]">
                {{ reviewLabel(activity.review_status) }}
              </span>
              <span class="badge" :class="EXECUTION_CLASS[activity.execution_status]">
                {{ executionLabel(activity.execution_status) }}
              </span>
              <small v-if="activity.review_comment" class="clamp">意见：{{ activity.review_comment }}</small>
              <small v-if="activity.cancellation_reason" class="clamp">
                取消原因：{{ activity.cancellation_reason }}
              </small>
            </td>
            <td class="nowrap">
              {{ activity.registration_count }}<span v-if="activity.capacity"> / {{ activity.capacity }}</span>
              <br />
              <small v-if="activity.my_registration_status === 'REGISTERED'" class="mine">已报名</small>
              <small v-else-if="activity.my_registration_status === 'CANCELLED'">已取消报名</small>
            </td>
            <td class="actions">
              <button class="link" @click="detailsTarget = activity">详情</button>
              <button v-if="canEdit(activity)" class="link" @click="openEdit(activity)">编辑</button>
              <button v-if="canSubmit(activity)" class="link" @click="submit(activity)">提交审核</button>
              <button v-if="canWithdraw(activity)" class="link" @click="withdraw(activity)">撤回</button>
              <button v-if="canReview(activity)" class="link" @click="openReview(activity)">审核</button>
              <button v-if="canPublish(activity)" class="link" @click="publish(activity)">发布</button>
              <button v-if="canRegister(activity)" class="link" @click="register(activity)">报名</button>
              <button v-if="canCancelRegistration(activity)" class="link" @click="unregister(activity)">
                取消报名
              </button>
              <button v-if="canViewRoster(activity)" class="link" @click="openRoster(activity)">报名名单</button>
              <button v-if="canCancel(activity)" class="link danger" @click="openCancel(activity)">取消活动</button>
              <button v-if="canEnd(activity)" class="link" @click="openEnd(activity)">结束归档</button>
            </td>
          </tr>
          <tr v-if="!activities.length">
            <td colspan="6" class="empty">当前没有可见活动</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pager">
      <span>共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页</span>
      <div>
        <button :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
        <button :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
      </div>
    </footer>

    <div v-if="showForm" class="modal" @click.self="closeForm">
      <form class="modal-card" @submit.prevent="saveForm">
        <h3>{{ editingId ? '编辑活动草稿' : '新建活动申请' }}</h3>
        <div class="grid">
          <label>
            所属社团
            <select v-model="form.club_id" :disabled="Boolean(editingId)">
              <option v-for="club in clubOptions" :key="club.club_id" :value="club.club_id">
                {{ club.club_name }}
              </option>
            </select>
          </label>
          <label>
            活动名称
            <input v-model="form.title" maxlength="200" required />
          </label>
          <label class="full">
            活动方案
            <textarea v-model="form.description" rows="3" maxlength="5000" required></textarea>
          </label>
          <label>
            地点
            <input v-model="form.location" maxlength="255" required />
          </label>
          <label>
            预算（元）
            <input v-model="form.budget" type="number" min="0" step="0.01" />
          </label>
          <label>
            开始时间
            <input v-model="form.starts_at" type="datetime-local" required />
          </label>
          <label>
            结束时间
            <input v-model="form.ends_at" type="datetime-local" required />
          </label>
          <label>
            报名截止
            <input v-model="form.registration_deadline" type="datetime-local" />
          </label>
          <label>
            人数容量（留空不限）
            <input v-model="form.capacity" type="number" min="1" step="1" />
          </label>
        </div>
        <p v-if="formError" class="banner error">{{ formError }}</p>
        <div class="modal-actions">
          <button type="button" :disabled="busy" @click="closeForm">取消</button>
          <button class="primary" type="submit" :disabled="busy">保存草稿</button>
        </div>
      </form>
    </div>

    <div v-if="reviewTarget" class="modal" @click.self="reviewTarget = null">
      <form class="modal-card" @submit.prevent="confirmReview">
        <h3>审核活动：{{ reviewTarget.title }}</h3>
        <p class="meta">{{ reviewTarget.description }}</p>
        <label class="stack">
          审核决定
          <select v-model="reviewForm.decision">
            <option value="APPROVED">通过</option>
            <option value="REJECTED">驳回</option>
          </select>
        </label>
        <label class="stack">
          审核意见（可选）
          <textarea v-model="reviewForm.comment" rows="3" maxlength="2000"></textarea>
        </label>
        <div class="modal-actions">
          <button type="button" :disabled="busy" @click="reviewTarget = null">取消</button>
          <button class="primary" type="submit" :disabled="busy">提交审核结果</button>
        </div>
      </form>
    </div>

    <div v-if="cancelTarget" class="modal" @click.self="cancelTarget = null">
      <form class="modal-card" @submit.prevent="confirmCancel">
        <h3>取消活动：{{ cancelTarget.title }}</h3>
        <p class="meta">取消后不能继续报名，并向已报名用户发送站内通知。</p>
        <label class="stack">
          取消原因（必填）
          <textarea v-model="cancelReason" rows="3" maxlength="2000" required></textarea>
        </label>
        <div class="modal-actions">
          <button type="button" :disabled="busy" @click="cancelTarget = null">返回</button>
          <button class="danger-button" type="submit" :disabled="busy">确认取消活动</button>
        </div>
      </form>
    </div>

    <div v-if="endTarget" class="modal" @click.self="endTarget = null">
      <form class="modal-card" @submit.prevent="confirmEnd">
        <h3>结束活动：{{ endTarget.title }}</h3>
        <label class="stack">
          活动总结（可选）
          <textarea v-model="endSummary" rows="4" maxlength="5000"></textarea>
        </label>
        <div class="modal-actions">
          <button type="button" :disabled="busy" @click="endTarget = null">返回</button>
          <button class="primary" type="submit" :disabled="busy">结束并归档</button>
        </div>
      </form>
    </div>

    <div v-if="detailsTarget" class="modal" @click.self="detailsTarget = null">
      <div class="modal-card">
        <h3>{{ detailsTarget.title }}</h3>
        <dl class="details">
          <dt>社团</dt><dd>{{ clubName(detailsTarget.club_id) }}</dd>
          <dt>方案</dt><dd>{{ detailsTarget.description }}</dd>
          <dt>地点</dt><dd>{{ detailsTarget.location }}</dd>
          <dt>时间</dt>
          <dd>{{ formatDateTime(detailsTarget.starts_at) }} ～ {{ formatDateTime(detailsTarget.ends_at) }}</dd>
          <dt>报名截止</dt><dd>{{ formatDateTime(detailsTarget.registration_deadline) }}</dd>
          <dt>容量 / 预算</dt>
          <dd>{{ detailsTarget.capacity ?? '不限' }} / ￥{{ detailsTarget.budget }}</dd>
          <dt>审核状态</dt><dd>{{ reviewLabel(detailsTarget.review_status) }}</dd>
          <dt>执行状态</dt><dd>{{ executionLabel(detailsTarget.execution_status) }}</dd>
          <dt>审核意见</dt><dd>{{ detailsTarget.review_comment || '—' }}</dd>
          <dt>取消原因</dt><dd>{{ detailsTarget.cancellation_reason || '—' }}</dd>
          <dt>活动总结</dt><dd>{{ detailsTarget.summary || '—' }}</dd>
        </dl>
        <div class="modal-actions">
          <button type="button" @click="detailsTarget = null">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="rosterTarget" class="modal" @click.self="rosterTarget = null">
      <div class="modal-card">
        <h3>报名名单：{{ rosterTarget.title }}</h3>
        <table class="roster-table">
          <thead>
            <tr><th>报名人</th><th>状态</th><th>报名时间</th><th>取消时间</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in roster" :key="item.id">
              <td>{{ item.user?.display_name || `#${item.user_id}` }}（{{ item.user?.username }}）</td>
              <td>{{ item.status === 'REGISTERED' ? '已报名' : '已取消' }}</td>
              <td>{{ formatDateTime(item.registered_at) }}</td>
              <td>{{ formatDateTime(item.cancelled_at) }}</td>
            </tr>
            <tr v-if="!roster.length"><td colspan="4" class="empty">暂无报名记录</td></tr>
          </tbody>
        </table>
        <footer class="pager">
          <span>共 {{ rosterTotal }} 条</span>
          <div>
            <button :disabled="rosterPage <= 1" @click="rosterGo(rosterPage - 1)">上一页</button>
            <button :disabled="rosterPage * rosterPageSize >= rosterTotal" @click="rosterGo(rosterPage + 1)">
              下一页
            </button>
          </div>
        </footer>
        <div class="modal-actions">
          <button type="button" @click="rosterTarget = null">关闭</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.activity-page { display: flex; flex-direction: column; gap: 1rem; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
.page-head h2 { margin: 0 0 .25rem; }
.meta { margin: 0; color: #6b7280; font-size: .875rem; }
.banner { margin: 0; padding: .65rem .85rem; border-radius: 8px; font-size: .9rem; }
.banner.error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.banner.notice { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; vertical-align: top; padding: .65rem .5rem; border-bottom: 1px solid #e5e7eb; }
th { color: #4b5563; font-weight: 600; white-space: nowrap; }
.activity-cell { min-width: 220px; }
.activity-cell small { display: block; color: #6b7280; margin-top: .2rem; }
.nowrap { white-space: nowrap; }
.clamp { display: block; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mine { color: #047857; font-weight: 600; }
.actions { min-width: 150px; display: flex; flex-wrap: wrap; gap: .35rem; align-content: flex-start; }
button { padding: .4rem .7rem; border: 1px solid #d1d5db; background: white; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: .55; cursor: not-allowed; }
button.primary { background: #1d4ed8; border-color: #1d4ed8; color: white; }
button.danger-button { background: #b91c1c; border-color: #b91c1c; color: white; }
button.link { border: none; background: transparent; color: #1d4ed8; padding: .2rem .15rem; }
button.link.danger { color: #b91c1c; }
.badge { display: inline-block; margin: 0 .3rem .25rem 0; padding: .15rem .45rem; border-radius: 999px; font-size: .75rem; }
.badge.draft { background: #f3f4f6; color: #4b5563; }
.badge.pending { background: #fef3c7; color: #b45309; }
.badge.approved { background: #dcfce7; color: #047857; }
.badge.rejected { background: #fee2e2; color: #b91c1c; }
.badge.withdrawn { background: #e5e7eb; color: #4b5563; }
.badge.open { background: #dbeafe; color: #1d4ed8; }
.badge.closed { background: #ede9fe; color: #6d28d9; }
.badge.progress { background: #cffafe; color: #0e7490; }
.badge.ended { background: #e5e7eb; color: #374151; }
.badge.cancelled { background: #fee2e2; color: #991b1b; }
.pager { display: flex; justify-content: space-between; align-items: center; gap: 1rem; font-size: .85rem; color: #6b7280; }
.pager div { display: flex; gap: .5rem; }
.modal { position: fixed; inset: 0; background: rgba(15, 23, 42, .45); display: flex; align-items: center; justify-content: center; padding: 1rem; z-index: 50; }
.modal-card { background: white; border-radius: 12px; width: min(720px, 100%); max-height: 90vh; overflow: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: .9rem; }
.modal-card h3 { margin: 0; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
.grid .full { grid-column: 1 / -1; }
label { display: flex; flex-direction: column; gap: .3rem; font-size: .875rem; color: #374151; }
label.stack { display: flex; }
input, select, textarea { padding: .5rem .6rem; border: 1px solid #d1d5db; border-radius: 6px; font: inherit; width: 100%; }
textarea { resize: vertical; }
.modal-actions { display: flex; justify-content: flex-end; gap: .5rem; }
.details { display: grid; grid-template-columns: 100px 1fr; gap: .4rem .8rem; margin: 0; font-size: .9rem; }
.details dt { color: #6b7280; }
.details dd { margin: 0; }
.roster-table { margin-top: .25rem; }
.empty { text-align: center; color: #6b7280; padding: 1.25rem; }
@media (max-width: 720px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
