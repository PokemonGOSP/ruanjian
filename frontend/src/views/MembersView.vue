<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { listClubsApi } from '../api/clubs.js'
import {
  createMembershipApplicationApi,
  listClubMembersApi,
  listMembershipApplicationsApi,
  processMembershipApplicationApi,
  updateClubMemberApi,
  withdrawMembershipApplicationApi,
} from '../api/members.js'
import {
  MEMBERSHIP_STATUS_LABELS,
  MEMBERSHIP_TYPE_LABELS,
  MEMBER_STATUS_LABELS,
  formatDateTime,
} from '../utils/m02m03.js'

const auth = useAuthStore()
const tab = ref('applications')
const message = ref('')
const error = ref('')

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

// ---------------------------------------------------------------- 申请
const clubs = ref([])
const applications = ref([])
const appPage = ref(1)
const appPageSize = 20
const appTotal = ref(0)
const viewMode = ref('mine')
const appStatus = ref('')
const appType = ref('')
const showAppForm = ref(false)
const appForm = reactive({ club_id: '', application_type: 'JOIN', reason: '' })
const appReview = reactive({ application: null, decision: 'APPROVED', comment: '' })

const appPages = computed(() => Math.max(1, Math.ceil(appTotal.value / appPageSize)))

async function loadClubs() {
  try {
    const response = await listClubsApi({ page: 1, page_size: 100 })
    clubs.value = response.data.data.items
  } catch (reason) {
    setError(reason)
  }
}

async function loadApplications() {
  try {
    const params = { page: appPage.value, page_size: appPageSize }
    if (viewMode.value) params.scope = viewMode.value
    if (appStatus.value) params.status = appStatus.value
    if (appType.value) params.application_type = appType.value
    const response = await listMembershipApplicationsApi(params)
    applications.value = response.data.data.items
    appTotal.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  }
}

function changeFilter() {
  appPage.value = 1
  loadApplications()
}

function newApplication() {
  appForm.club_id = clubs.value[0]?.id || ''
  appForm.application_type = 'JOIN'
  appForm.reason = ''
  showAppForm.value = true
}

async function saveApplication() {
  try {
    await createMembershipApplicationApi({
      club_id: Number(appForm.club_id),
      application_type: appForm.application_type,
      reason: appForm.reason || null,
    })
    setMessage('成员申请已提交，等待目标社团 R02 处理')
    showAppForm.value = false
    viewMode.value = 'mine'
    appPage.value = 1
    await loadApplications()
  } catch (reason) {
    setError(reason)
  }
}

async function withdrawApplication(application) {
  try {
    await withdrawMembershipApplicationApi(application.id)
    setMessage('成员申请已撤回')
    await loadApplications()
  } catch (reason) {
    setError(reason)
  }
}

function openProcess(application) {
  appReview.application = application
  appReview.decision = 'APPROVED'
  appReview.comment = ''
}

function closeProcess() {
  appReview.application = null
  appReview.comment = ''
}

async function confirmProcess() {
  const clubId = appReview.application.club_id
  try {
    await processMembershipApplicationApi(appReview.application.id, {
      decision: appReview.decision,
      comment: appReview.comment || null,
    })
    setMessage(
      appReview.decision === 'APPROVED'
        ? '成员申请已同意，成员关系已同步更新'
        : '成员申请已驳回，成员关系未变化',
    )
    closeProcess()
    await loadApplications()
    if (rosterClubId.value === clubId) {
      await loadRoster()
    }
  } catch (reason) {
    setError(reason)
  }
}

// ---------------------------------------------------------------- 名册
const members = ref([])
const memberPage = ref(1)
const memberPageSize = 20
const memberTotal = ref(0)
const memberStatus = ref('')
const rosterClubId = ref('')
const editingMemberId = ref(null)
const positionDraft = ref('')

const memberPages = computed(() => Math.max(1, Math.ceil(memberTotal.value / memberPageSize)))
const canEditPosition = computed(() => canManageClub(rosterClubId.value))

async function loadRoster() {
  if (!rosterClubId.value) {
    members.value = []
    memberTotal.value = 0
    return
  }
  try {
    const params = { page: memberPage.value, page_size: memberPageSize }
    if (memberStatus.value) params.status = memberStatus.value
    const response = await listClubMembersApi(rosterClubId.value, params)
    members.value = response.data.data.items
    memberTotal.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  }
}

function changeRosterClub() {
  memberPage.value = 1
  editingMemberId.value = null
  loadRoster()
}

function changeMemberStatus() {
  memberPage.value = 1
  loadRoster()
}

function editPosition(member) {
  editingMemberId.value = member.id
  positionDraft.value = member.position_name || ''
}

function savePosition(member) {
  updateClubMemberApi(rosterClubId.value, member.id, {
    position_name: positionDraft.value || null,
  })
    .then(async () => {
      setMessage('社团职务已更新')
      editingMemberId.value = null
      await loadRoster()
    })
    .catch(setError)
}

function cancelPosition() {
  editingMemberId.value = null
  positionDraft.value = ''
}

onMounted(async () => {
  try {
    await auth.fetchMe()
  } catch (reason) {
    setError(reason)
  }
  if (ledClubs.value.length > 0) {
    viewMode.value = 'managed'
    rosterClubId.value = ledClubs.value[0].club_id
  }
  await loadClubs()
  await Promise.all([loadApplications(), loadRoster()])
})
</script>

<template>
  <section class="page">
    <div class="page-head">
      <div>
        <h2>成员管理</h2>
        <p class="muted">M03 · FR-08～FR-10 · R01 申请入团/退出，R02 处理本社团申请并维护职务</p>
      </div>
      <button class="secondary" @click="refreshIdentity">刷新身份与授权</button>
    </div>

    <p v-if="message" class="notice success">{{ message }}</p>
    <p v-if="error" class="notice error">{{ error }}</p>

    <nav class="tabs">
      <button :class="{ active: tab === 'applications' }" @click="tab = 'applications'">入团/退出申请</button>
      <button :class="{ active: tab === 'roster' }" @click="tab = 'roster'">成员名册</button>
    </nav>

    <!-- 申请 -->
    <div v-if="tab === 'applications'" class="panel">
      <div class="toolbar">
        <div class="filters">
          <label>
            范围
            <select v-model="viewMode" @change="changeFilter">
              <option value="mine">我的申请</option>
              <option value="managed">我负责社团的申请</option>
              <option value="">本人 + 负责社团</option>
            </select>
          </label>
          <label>
            状态
            <select v-model="appStatus" @change="changeFilter">
              <option value="">全部</option>
              <option v-for="(label, value) in MEMBERSHIP_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </label>
          <label>
            类型
            <select v-model="appType" @change="changeFilter">
              <option value="">全部</option>
              <option v-for="(label, value) in MEMBERSHIP_TYPE_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </label>
        </div>
        <button @click="newApplication">提交成员申请</button>
      </div>

      <form v-if="showAppForm" class="card form-card" @submit.prevent="saveApplication">
        <h3>提交入团/退出申请</h3>
        <label>目标社团
          <select v-model="appForm.club_id" required>
            <option v-for="club in clubs" :key="club.id" :value="club.id">{{ club.name }}</option>
          </select>
        </label>
        <label>申请类型
          <select v-model="appForm.application_type">
            <option value="JOIN">入团</option>
            <option value="EXIT">退出</option>
          </select>
        </label>
        <label>说明（可选）<textarea v-model="appForm.reason" rows="3" maxlength="2000"></textarea></label>
        <p class="muted">入团要求当前不是有效成员；退出要求当前是有效成员。同一社团不能有重复的待处理申请。</p>
        <div class="actions">
          <button type="submit">提交申请</button>
          <button type="button" class="secondary" @click="showAppForm = false">取消</button>
        </div>
      </form>

      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>ID</th><th>社团</th><th>申请人</th><th>类型</th><th>状态</th><th>说明</th><th>提交时间</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="application in applications" :key="application.id">
              <td>{{ application.id }}</td>
              <td>{{ application.club_name || application.club_id }}</td>
              <td>{{ application.applicant_display_name || application.applicant_user_id }}</td>
              <td>{{ MEMBERSHIP_TYPE_LABELS[application.application_type] }}</td>
              <td><span class="badge" :class="`status-${application.status.toLowerCase()}`">{{ MEMBERSHIP_STATUS_LABELS[application.status] }}</span></td>
              <td>{{ application.reason || '—' }}</td>
              <td>{{ formatDateTime(application.created_at) }}</td>
              <td class="row-actions">
                <button
                  v-if="application.applicant_user_id === auth.user?.user_id && application.status === 'PENDING'"
                  class="small secondary"
                  @click="withdrawApplication(application)"
                >撤回</button>
                <button
                  v-if="canManageClub(application.club_id) && application.status === 'PENDING' && application.applicant_user_id !== auth.user?.user_id"
                  class="small"
                  @click="openProcess(application)"
                >处理</button>
              </td>
            </tr>
            <tr v-if="applications.length === 0"><td colspan="8" class="empty">暂无成员申请</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <button class="small secondary" :disabled="appPage <= 1" @click="appPage--; loadApplications()">上一页</button>
        <span>第 {{ appPage }} / {{ appPages }} 页，共 {{ appTotal }} 条</span>
        <button class="small secondary" :disabled="appPage >= appPages" @click="appPage++; loadApplications()">下一页</button>
      </div>

      <form v-if="appReview.application" class="card form-card" @submit.prevent="confirmProcess">
        <h3>处理成员申请：{{ appReview.application.applicant_display_name }} · {{ MEMBERSHIP_TYPE_LABELS[appReview.application.application_type] }}</h3>
        <label>结果
          <select v-model="appReview.decision">
            <option value="APPROVED">已同意</option>
            <option value="REJECTED">已驳回</option>
          </select>
        </label>
        <label>处理意见<textarea v-model="appReview.comment" rows="3" maxlength="2000"></textarea></label>
        <p class="muted">同意入团会建立或恢复有效成员关系；同意退出会把成员关系置为已退出；驳回不改变成员关系。</p>
        <div class="actions">
          <button type="submit">确认处理</button>
          <button type="button" class="secondary" @click="closeProcess">取消</button>
        </div>
      </form>
    </div>

    <!-- 名册 -->
    <div v-if="tab === 'roster'" class="panel">
      <div class="toolbar">
        <div class="filters">
          <label>
            社团
            <select v-model="rosterClubId" @change="changeRosterClub">
              <option value="">请选择社团</option>
              <option v-for="club in clubs" :key="club.id" :value="club.id">{{ club.name }}</option>
            </select>
          </label>
          <label>
            状态
            <select v-model="memberStatus" @change="changeMemberStatus">
              <option value="">全部</option>
              <option v-for="(label, value) in MEMBER_STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
            </select>
          </label>
        </div>
        <span class="muted">R02 可查看完整名册并维护职务；有效成员只能查看本人的受限记录。</span>
      </div>

      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>成员</th><th>社团职务</th><th>状态</th><th>加入时间</th><th>退出时间</th></tr></thead>
          <tbody>
            <tr v-for="member in members" :key="member.id">
              <td>{{ member.id }}</td>
              <td>{{ member.display_name }}</td>
              <td>
                <template v-if="canEditPosition && editingMemberId === member.id">
                  <input v-model="positionDraft" maxlength="100" class="inline-input" />
                  <button class="small" @click="savePosition(member)">保存</button>
                  <button class="small secondary" @click="cancelPosition">取消</button>
                </template>
                <template v-else>
                  <span>{{ member.position_name || '—' }}</span>
                  <button
                    v-if="canEditPosition && member.status === 'ACTIVE'"
                    class="small secondary"
                    @click="editPosition(member)"
                  >维护职务</button>
                </template>
              </td>
              <td><span class="badge" :class="member.status === 'ACTIVE' ? 'status-approved' : 'status-withdrawn'">{{ MEMBER_STATUS_LABELS[member.status] }}</span></td>
              <td>{{ formatDateTime(member.joined_at) }}</td>
              <td>{{ formatDateTime(member.exited_at) }}</td>
            </tr>
            <tr v-if="members.length === 0"><td colspan="6" class="empty">选择有权限的社团后显示名册</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pager">
        <button class="small secondary" :disabled="memberPage <= 1" @click="memberPage--; loadRoster()">上一页</button>
        <span>第 {{ memberPage }} / {{ memberPages }} 页，共 {{ memberTotal }} 条</span>
        <button class="small secondary" :disabled="memberPage >= memberPages" @click="memberPage++; loadRoster()">下一页</button>
      </div>
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
.filters { display: flex; gap: 1rem; flex-wrap: wrap; }
.filters label { display: flex; align-items: center; gap: .5rem; font-size: .9rem; }
.form-card { display: grid; gap: .75rem; max-width: 720px; }
.form-card label { display: grid; gap: .35rem; font-size: .9rem; }
input, select, textarea { padding: .55rem; border: 1px solid #9ca3af; border-radius: 6px; font: inherit; }
.inline-input { width: 130px; padding: .25rem .4rem; }
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
.status-pending { background: #fef3c7; color: #92400e; }
.status-approved { background: #d1fae5; color: #065f46; }
.status-rejected { background: #fee2e2; color: #991b1b; }
.status-withdrawn { background: #ede9fe; color: #5b21b6; }
.pager { display: flex; align-items: center; justify-content: flex-end; gap: .75rem; font-size: .85rem; color: #4b5563; }
@media (max-width: 720px) {
  .page-head { flex-direction: column; }
}
</style>
