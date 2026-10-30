<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import {
  createAnnualReviewApi,
  createRegistrationApi,
  listAnnualReviewsApi,
  listClubsApi,
  listRegistrationsApi,
  reviewAnnualReviewApi,
  reviewRegistrationApi,
  submitAnnualReviewApi,
  submitRegistrationApi,
  updateAnnualReviewApi,
  updateClubApi,
  updateRegistrationApi,
  withdrawAnnualReviewApi,
  withdrawRegistrationApi,
} from '../api/clubs.js'
import { REVIEW_STATUS_LABELS, formatDateTime } from '../utils/m02m03.js'

const auth = useAuthStore()
const currentYear = new Date().getFullYear()
const tab = ref('registrations')
const message = ref('')
const error = ref('')

const isManager = computed(() => auth.user?.system_roles?.includes('R03'))
const ledClubs = computed(() => auth.user?.club_authorizations || [])
const ledClubIds = computed(() => new Set(ledClubs.value.map((item) => item.club_id)))
const canManageClub = (clubId) => ledClubIds.value.has(clubId)

function setMessage(text) {
  message.value = text
  error.value = ''
}

function setError(reason) {
  error.value = reason?.message || '操作失败，请检查输入或权限'
  message.value = ''
}

async function refreshIdentity() {
  try {
    await auth.fetchMe()
    setMessage('身份与社团授权已刷新')
  } catch (reason) {
    setError(reason)
  }
}

// ---------------------------------------------------------------- 注册申请
const applications = ref([])
const appPage = ref(1)
const appPageSize = 20
const appTotal = ref(0)
const appFilter = ref('')
const showAppForm = ref(false)
const savingApp = ref(false)
const editingAppId = ref(null)
const appForm = reactive({ proposed_name: '', description: '', advisor_contact: '' })
const appReview = reactive({ application: null, decision: 'APPROVED', comment: '' })

const appPages = computed(() => Math.max(1, Math.ceil(appTotal.value / appPageSize)))

async function loadApplications() {
  try {
    const params = { page: appPage.value, page_size: appPageSize }
    if (appFilter.value) params.status = appFilter.value
    const response = await listRegistrationsApi(params)
    applications.value = response.data.data.items
    appTotal.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  }
}

function changeAppFilter() {
  appPage.value = 1
  loadApplications()
}

function resetAppForm() {
  editingAppId.value = null
  appForm.proposed_name = ''
  appForm.description = ''
  appForm.advisor_contact = ''
  showAppForm.value = false
}

function newApplication() {
  resetAppForm()
  showAppForm.value = true
}

function editApplication(application) {
  editingAppId.value = application.id
  appForm.proposed_name = application.proposed_name
  appForm.description = application.description
  appForm.advisor_contact = application.advisor_contact || ''
  showAppForm.value = true
}

async function saveApplication() {
  savingApp.value = true
  try {
    const payload = {
      proposed_name: appForm.proposed_name,
      description: appForm.description,
      advisor_contact: appForm.advisor_contact || null,
    }
    if (editingAppId.value) {
      await updateRegistrationApi(editingAppId.value, payload)
      setMessage('社团注册申请已保存')
    } else {
      await createRegistrationApi(payload)
      setMessage('社团注册申请已创建为草稿')
    }
    resetAppForm()
    await loadApplications()
  } catch (reason) {
    setError(reason)
  } finally {
    savingApp.value = false
  }
}

async function submitApplication(application) {
  try {
    await submitRegistrationApi(application.id)
    setMessage('社团注册申请已提交，等待 R03 审核')
    await loadApplications()
  } catch (reason) {
    setError(reason)
  }
}

async function withdrawApplication(application) {
  try {
    await withdrawRegistrationApi(application.id)
    setMessage('社团注册申请已撤回')
    await loadApplications()
  } catch (reason) {
    setError(reason)
  }
}

function openAppReview(application) {
  appReview.application = application
  appReview.decision = 'APPROVED'
  appReview.comment = ''
}

function closeAppReview() {
  appReview.application = null
  appReview.comment = ''
}

async function confirmAppReview() {
  try {
    await reviewRegistrationApi(appReview.application.id, {
      decision: appReview.decision,
      comment: appReview.comment || null,
    })
    setMessage(appReview.decision === 'APPROVED' ? '审核通过，已建立社团并授予申请人 R02' : '已驳回申请')
    closeAppReview()
    await Promise.all([loadApplications(), loadClubs()])
  } catch (reason) {
    setError(reason)
  }
}

// ---------------------------------------------------------------- 社团资料
const clubs = ref([])
const clubPage = ref(1)
const clubPageSize = 20
const clubTotal = ref(0)
const showClubForm = ref(false)
const editingClubId = ref(null)
const clubForm = reactive({ name: '', description: '', advisor_contact: '' })

const clubPages = computed(() => Math.max(1, Math.ceil(clubTotal.value / clubPageSize)))

async function loadClubs() {
  try {
    const response = await listClubsApi({ page: clubPage.value, page_size: clubPageSize })
    clubs.value = response.data.data.items
    clubTotal.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  }
}

function editClub(club) {
  editingClubId.value = club.id
  clubForm.name = club.name
  clubForm.description = club.description
  clubForm.advisor_contact = club.advisor_contact || ''
  showClubForm.value = true
}

function resetClubForm() {
  editingClubId.value = null
  clubForm.name = ''
  clubForm.description = ''
  clubForm.advisor_contact = ''
  showClubForm.value = false
}

async function saveClub() {
  try {
    await updateClubApi(editingClubId.value, {
      name: clubForm.name,
      description: clubForm.description,
      advisor_contact: clubForm.advisor_contact || null,
    })
    setMessage('社团资料已更新')
    resetClubForm()
    await Promise.all([loadClubs(), auth.fetchMe()])
  } catch (reason) {
    setError(reason)
  }
}

// ---------------------------------------------------------------- 年审
const reviews = ref([])
const reviewPage = ref(1)
const reviewPageSize = 20
const reviewTotal = ref(0)
const reviewFilter = ref('')
const showReviewForm = ref(false)
const editingReviewId = ref(null)
const reviewForm = reactive({ club_id: '', review_year: currentYear, materials: '' })
const annualReview = reactive({ application: null, decision: 'APPROVED', comment: '' })

const reviewPages = computed(() => Math.max(1, Math.ceil(reviewTotal.value / reviewPageSize)))

function canSeeAnnual() {
  return isManager.value || ledClubs.value.length > 0
}

async function loadReviews() {
  if (!canSeeAnnual()) {
    reviews.value = []
    reviewTotal.value = 0
    return
  }
  try {
    const params = { page: reviewPage.value, page_size: reviewPageSize }
    if (reviewFilter.value) params.status = reviewFilter.value
    const response = await listAnnualReviewsApi(params)
    reviews.value = response.data.data.items
    reviewTotal.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  }
}

function changeReviewFilter() {
  reviewPage.value = 1
  loadReviews()
}

function resetReviewForm() {
  editingReviewId.value = null
  reviewForm.club_id = ledClubs.value[0]?.club_id || ''
  reviewForm.review_year = currentYear
  reviewForm.materials = ''
  showReviewForm.value = false
}

function newAnnualReview() {
  resetReviewForm()
  showReviewForm.value = true
}

function editAnnualReview(application) {
  editingReviewId.value = application.id
  reviewForm.club_id = application.club_id
  reviewForm.review_year = application.review_year
  reviewForm.materials = application.materials
  showReviewForm.value = true
}

async function saveAnnualReview() {
  try {
    if (editingReviewId.value) {
      await updateAnnualReviewApi(editingReviewId.value, {
        review_year: Number(reviewForm.review_year),
        materials: reviewForm.materials,
      })
      setMessage('年审申请已保存')
    } else {
      await createAnnualReviewApi({
        club_id: Number(reviewForm.club_id),
        review_year: Number(reviewForm.review_year),
        materials: reviewForm.materials,
      })
      setMessage('年审申请已创建为草稿')
    }
    resetReviewForm()
    await loadReviews()
  } catch (reason) {
    setError(reason)
  }
}

async function submitAnnualReview(application) {
  try {
    await submitAnnualReviewApi(application.id)
    setMessage('年审申请已提交，等待 R03 审核')
    await loadReviews()
  } catch (reason) {
    setError(reason)
  }
}

async function withdrawAnnualReview(application) {
  try {
    await withdrawAnnualReviewApi(application.id)
    setMessage('年审申请已撤回')
    await loadReviews()
  } catch (reason) {
    setError(reason)
  }
}

function openAnnualReview(application) {
  annualReview.application = application
  annualReview.decision = 'APPROVED'
  annualReview.comment = ''
}

function closeAnnualReview() {
  annualReview.application = null
  annualReview.comment = ''
}

async function confirmAnnualReview() {
  try {
    await reviewAnnualReviewApi(annualReview.application.id, {
      decision: annualReview.decision,
      comment: annualReview.comment || null,
    })
    setMessage('年审审核结果已保存；驳回不会冻结社团或限制其他业务')
    closeAnnualReview()
    await loadReviews()
  } catch (reason) {
    setError(reason)
  }
}

onMounted(async () => {
  try {
    await auth.fetchMe()
  } catch (reason) {
    setError(reason)
  }
  resetReviewForm()
  await Promise.all([loadApplications(), loadClubs(), loadReviews()])
})
</script>

<template>
  <section class="page">
    <div class="page-head">
      <div>
        <h2>社团注册与年审</h2>
        <p class="muted">M02 · FR-03～FR-07 · R01 发起注册，R03 审核，R02 维护社团资料并提交年审</p>
      </div>
      <button class="secondary" @click="refreshIdentity">刷新身份与授权</button>
    </div>

    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice error">{{ error }}</p>

    <nav class="tabs">
      <button :class="{ active: tab === 'registrations' }" @click="tab = 'registrations'">社团注册申请</button>
      <button :class="{ active: tab === 'clubs' }" @click="tab = 'clubs'">社团资料</button>
      <button v-if="canSeeAnnual()" :class="{ active: tab === 'annual' }" @click="tab = 'annual'">年审</button>
    </nav>

    <!-- 注册申请 -->
    <div v-if="tab === 'registrations'" class="panel">
      <div class="toolbar">
        <label>
          状态
          <select v-model="appFilter" @change="changeAppFilter">
            <option value="">全部</option>
            <option v-for="(label, value) in REVIEW_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <button @click="newApplication">新建注册申请</button>
      </div>

      <form v-if="showAppForm" class="card form-card" @submit.prevent="saveApplication">
        <h3>{{ editingAppId ? '编辑注册申请' : '新建注册申请' }}</h3>
        <label>拟用社团名称<input v-model="appForm.proposed_name" maxlength="150" required /></label>
        <label>社团简介<textarea v-model="appForm.description" rows="3" required></textarea></label>
        <label>指导教师联系方式（可选）<input v-model="appForm.advisor_contact" maxlength="255" /></label>
        <div class="actions">
          <button type="submit" :disabled="savingApp">{{ savingApp ? '保存中…' : '保存草稿' }}</button>
          <button type="button" class="secondary" @click="resetAppForm">取消</button>
        </div>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th><th>拟用名称</th><th>申请人</th><th>状态</th><th>提交时间</th><th>审核意见</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="application in applications" :key="application.id">
              <td>{{ application.id }}</td>
              <td>{{ application.proposed_name }}</td>
              <td>{{ application.applicant_display_name || application.applicant_user_id }}</td>
              <td><span class="badge" :class="`status-${application.review_status.toLowerCase()}`">{{ REVIEW_STATUS_LABELS[application.review_status] }}</span></td>
              <td>{{ formatDateTime(application.submitted_at) }}</td>
              <td>{{ application.review_comment || '—' }}</td>
              <td class="row-actions">
                <template v-if="application.applicant_user_id === auth.user?.user_id">
                  <button
                    v-if="['DRAFT', 'WITHDRAWN'].includes(application.review_status)"
                    class="small"
                    @click="editApplication(application)"
                  >编辑</button>
                  <button
                    v-if="['DRAFT', 'WITHDRAWN'].includes(application.review_status)"
                    class="small"
                    @click="submitApplication(application)"
                  >提交</button>
                  <button
                    v-if="application.review_status === 'PENDING'"
                    class="small secondary"
                    @click="withdrawApplication(application)"
                  >撤回</button>
                </template>
                <button
                  v-if="isManager && application.review_status === 'PENDING' && application.applicant_user_id !== auth.user?.user_id"
                  class="small"
                  @click="openAppReview(application)"
                >审核</button>
              </td>
            </tr>
            <tr v-if="applications.length === 0"><td colspan="7" class="empty">暂无注册申请</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <button class="small secondary" :disabled="appPage <= 1" @click="appPage--; loadApplications()">上一页</button>
        <span>第 {{ appPage }} / {{ appPages }} 页，共 {{ appTotal }} 条</span>
        <button class="small secondary" :disabled="appPage >= appPages" @click="appPage++; loadApplications()">下一页</button>
      </div>

      <form v-if="appReview.application" class="card form-card" @submit.prevent="confirmAppReview">
        <h3>审核注册申请：{{ appReview.application.proposed_name }}</h3>
        <p class="muted">通过后将建立社团并授予申请人仅针对该社团的 R02 权限；驳回必须填写理由。</p>
        <label>结果
          <select v-model="appReview.decision">
            <option value="APPROVED">已通过</option>
            <option value="REJECTED">已驳回</option>
          </select>
        </label>
        <label>审核意见<textarea v-model="appReview.comment" rows="3" :required="appReview.decision === 'REJECTED'"></textarea></label>
        <div class="actions">
          <button type="submit">确认审核</button>
          <button type="button" class="secondary" @click="closeAppReview">取消</button>
        </div>
      </form>
    </div>

    <!-- 社团资料 -->
    <div v-if="tab === 'clubs'" class="panel">
      <p class="muted">R02 只能维护自己负责社团的资料；R03 只查看，不代替负责人修改业务材料。</p>
      <form v-if="showClubForm" class="card form-card" @submit.prevent="saveClub">
        <h3>编辑社团资料</h3>
        <label>社团名称<input v-model="clubForm.name" maxlength="150" required /></label>
        <label>社团简介<textarea v-model="clubForm.description" rows="3" required></textarea></label>
        <label>指导教师联系方式（可选）<input v-model="clubForm.advisor_contact" maxlength="255" /></label>
        <div class="actions">
          <button type="submit">保存</button>
          <button type="button" class="secondary" @click="resetClubForm">取消</button>
        </div>
      </form>

      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>社团名称</th><th>简介</th><th>指导教师联系方式</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="club in clubs" :key="club.id">
              <td>{{ club.id }}</td>
              <td>{{ club.name }}</td>
              <td>{{ club.description }}</td>
              <td>{{ club.advisor_contact || '—' }}</td>
              <td>
                <button v-if="canManageClub(club.id)" class="small" @click="editClub(club)">编辑资料</button>
                <span v-else class="muted">只读</span>
              </td>
            </tr>
            <tr v-if="clubs.length === 0"><td colspan="5" class="empty">暂无社团</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <button class="small secondary" :disabled="clubPage <= 1" @click="clubPage--; loadClubs()">上一页</button>
        <span>第 {{ clubPage }} / {{ clubPages }} 页，共 {{ clubTotal }} 条</span>
        <button class="small secondary" :disabled="clubPage >= clubPages" @click="clubPage++; loadClubs()">下一页</button>
      </div>
    </div>

    <!-- 年审 -->
    <div v-if="tab === 'annual'" class="panel">
      <div class="toolbar">
        <label>
          状态
          <select v-model="reviewFilter" @change="changeReviewFilter">
            <option value="">全部</option>
            <option v-for="(label, value) in REVIEW_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <button :disabled="ledClubs.length === 0" @click="newAnnualReview">新建年审申请</button>
      </div>

      <p v-if="!canSeeAnnual()" class="notice">当前账号既不是 R03，也没有任何社团 R02 授权，因此没有年审数据权限。</p>

      <form v-if="showReviewForm" class="card form-card" @submit.prevent="saveAnnualReview">
        <h3>{{ editingReviewId ? '编辑年审申请' : '新建年审申请' }}</h3>
        <label>社团
          <select v-model="reviewForm.club_id" :disabled="!!editingReviewId" required>
            <option v-for="club in ledClubs" :key="club.club_id" :value="club.club_id">{{ club.club_name }}</option>
          </select>
        </label>
        <label>年度<input v-model.number="reviewForm.review_year" type="number" min="2000" max="2100" required /></label>
        <label>年审材料<textarea v-model="reviewForm.materials" rows="4" required></textarea></label>
        <div class="actions">
          <button type="submit">保存草稿</button>
          <button type="button" class="secondary" @click="resetReviewForm">取消</button>
        </div>
      </form>

      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>社团</th><th>年度</th><th>状态</th><th>提交时间</th><th>审核意见</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="application in reviews" :key="application.id">
              <td>{{ application.id }}</td>
              <td>{{ application.club_name || application.club_id }}</td>
              <td>{{ application.review_year }}</td>
              <td><span class="badge" :class="`status-${application.review_status.toLowerCase()}`">{{ REVIEW_STATUS_LABELS[application.review_status] }}</span></td>
              <td>{{ formatDateTime(application.submitted_at) }}</td>
              <td>{{ application.review_comment || '—' }}</td>
              <td class="row-actions">
                <template v-if="canManageClub(application.club_id)">
                  <button v-if="['DRAFT', 'WITHDRAWN'].includes(application.review_status)" class="small" @click="editAnnualReview(application)">编辑</button>
                  <button v-if="['DRAFT', 'WITHDRAWN'].includes(application.review_status)" class="small" @click="submitAnnualReview(application)">提交</button>
                  <button v-if="application.review_status === 'PENDING'" class="small secondary" @click="withdrawAnnualReview(application)">撤回</button>
                </template>
                <button
                  v-if="isManager && application.review_status === 'PENDING' && application.submitted_by !== auth.user?.user_id"
                  class="small"
                  @click="openAnnualReview(application)"
                >审核</button>
              </td>
            </tr>
            <tr v-if="reviews.length === 0"><td colspan="7" class="empty">暂无年审申请</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <button class="small secondary" :disabled="reviewPage <= 1" @click="reviewPage--; loadReviews()">上一页</button>
        <span>第 {{ reviewPage }} / {{ reviewPages }} 页，共 {{ reviewTotal }} 条</span>
        <button class="small secondary" :disabled="reviewPage >= reviewPages" @click="reviewPage++; loadReviews()">下一页</button>
      </div>

      <form v-if="annualReview.application" class="card form-card" @submit.prevent="confirmAnnualReview">
        <h3>审核年审申请：{{ annualReview.application.club_name }} · {{ annualReview.application.review_year }}</h3>
        <p class="muted">驳回只保存状态、意见和站内通知，不冻结社团，也不限制活动、成员或经费业务。</p>
        <label>结果
          <select v-model="annualReview.decision">
            <option value="APPROVED">已通过</option>
            <option value="REJECTED">已驳回</option>
          </select>
        </label>
        <label>审核意见<textarea v-model="annualReview.comment" rows="3" :required="annualReview.decision === 'REJECTED'"></textarea></label>
        <div class="actions">
          <button type="submit">确认审核</button>
          <button type="button" class="secondary" @click="closeAnnualReview">取消</button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.page { display: grid; gap: 1rem; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
h2 { margin: 0 0 .35rem; }
h3 { margin: 0 0 .75rem; }
.muted { color: #6b7280; font-size: .9rem; }
.notice { padding: .7rem .9rem; border-radius: 8px; background: #eff6ff; }
.notice.success { background: #ecfdf5; color: #065f46; }
.notice.error { background: #fef2f2; color: #991b1b; }
.tabs { display: flex; gap: .5rem; border-bottom: 1px solid #e5e7eb; }
.tabs button { border: 0; background: transparent; padding: .6rem .9rem; cursor: pointer; color: #4b5563; border-bottom: 2px solid transparent; }
.tabs button.active { color: #1d4ed8; border-bottom-color: #1d4ed8; font-weight: 600; }
.panel { display: grid; gap: 1rem; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap; }
.toolbar label { display: flex; align-items: center; gap: .5rem; font-size: .9rem; }
.form-card { display: grid; gap: .75rem; max-width: 720px; }
.form-card label { display: grid; gap: .35rem; font-size: .9rem; }
input, select, textarea { padding: .55rem; border: 1px solid #9ca3af; border-radius: 6px; font: inherit; }
.actions { display: flex; gap: .5rem; }
button { padding: .5rem .85rem; border: 1px solid #1d4ed8; border-radius: 6px; background: #1d4ed8; color: white; cursor: pointer; }
button:disabled { opacity: .45; cursor: not-allowed; }
button.secondary { background: white; color: #1d4ed8; }
button.small { padding: .28rem .55rem; font-size: .82rem; }
.table-wrap { overflow-x: auto; background: white; border: 1px solid #e5e7eb; border-radius: 10px; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; padding: .6rem .7rem; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
th { background: #f9fafb; white-space: nowrap; }
.row-actions { display: flex; gap: .3rem; flex-wrap: wrap; }
.empty { text-align: center; color: #9ca3af; }
.badge { display: inline-block; padding: .18rem .5rem; border-radius: 999px; font-size: .78rem; background: #f3f4f6; }
.status-draft { background: #f3f4f6; color: #374151; }
.status-pending { background: #fef3c7; color: #92400e; }
.status-approved { background: #d1fae5; color: #065f46; }
.status-rejected { background: #fee2e2; color: #991b1b; }
.status-withdrawn { background: #ede9fe; color: #5b21b6; }
.pager { display: flex; align-items: center; justify-content: flex-end; gap: .75rem; font-size: .85rem; color: #4b5563; }
@media (max-width: 720px) {
  .page-head { flex-direction: column; }
}
</style>
