<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { listClubsApi } from '../api/clubs.js'
import {
  createAccountApi,
  grantRoleApi,
  listAccountsApi,
  revokeClubRoleApi,
  revokeSystemRoleApi,
  updateAccountApi,
} from '../api/accounts.js'

const PAGE_SIZE = 20
const STATUS_LABELS = { NORMAL: '正常', DISABLED: '已停用' }
const ROLE_LABELS = {
  R01: 'R01 学生用户',
  R02: 'R02 社团负责人',
  R03: 'R03 学校社团管理人员',
  R04: 'R04 系统管理员',
}
const GRANTABLE_ROLES = [
  { code: 'R02', label: 'R02 社团负责人（需指定社团）' },
  { code: 'R03', label: 'R03 学校社团管理人员' },
  { code: 'R04', label: 'R04 系统管理员' },
]
const REVOCABLE_SYSTEM_ROLES = new Set(['R03', 'R04'])

const auth = useAuthStore()
const isAdmin = computed(() => Boolean(auth.user?.system_roles?.includes('R04')))

const accounts = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')
const clubs = ref([])

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const clubNames = computed(() => Object.fromEntries(clubs.value.map((club) => [club.id, club.name])))

function clubLabel(clubId) {
  const name = clubNames.value[clubId]
  return name ? `${name}（#${clubId}）` : `社团 #${clubId}`
}

function setMessage(text) {
  message.value = text
  error.value = ''
}

function setError(reason) {
  error.value = reason?.message || '操作失败，请检查输入或权限'
  message.value = ''
}

function resetFeedback() {
  message.value = ''
  error.value = ''
}

async function loadAccounts() {
  if (!isAdmin.value) return
  loading.value = true
  try {
    const response = await listAccountsApi({ page: page.value, page_size: PAGE_SIZE })
    accounts.value = response.data.data.items
    total.value = response.data.data.total
  } catch (reason) {
    setError(reason)
  } finally {
    loading.value = false
  }
}

async function loadClubs() {
  try {
    const response = await listClubsApi({ page: 1, page_size: 100 })
    clubs.value = response.data.data.items
  } catch (reason) {
    setError(reason)
  }
}

function changePage(offset) {
  const next = page.value + offset
  if (next < 1 || next > pageCount.value) return
  page.value = next
  loadAccounts()
}

function refresh() {
  resetFeedback()
  loadAccounts()
}

// ---------------------------------------------------------------- 新建账号
const showCreate = ref(false)
const createForm = reactive({ username: '', display_name: '', password: '' })

function resetCreateForm() {
  createForm.username = ''
  createForm.display_name = ''
  createForm.password = ''
  showCreate.value = false
}

async function createAccount() {
  saving.value = true
  resetFeedback()
  try {
    const response = await createAccountApi({
      username: createForm.username,
      display_name: createForm.display_name,
      password: createForm.password,
    })
    setMessage(`账号 ${response.data.data.username} 已创建，并自动授予 R01 基础身份`)
    resetCreateForm()
    page.value = 1
    await loadAccounts()
  } catch (reason) {
    setError(reason)
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 编辑账号
const editingId = ref(null)
const editForm = reactive({ display_name: '', status: 'NORMAL' })

function startEdit(account) {
  resetFeedback()
  editingId.value = account.user_id
  editForm.display_name = account.display_name
  editForm.status = account.status
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit() {
  saving.value = true
  resetFeedback()
  try {
    const response = await updateAccountApi(editingId.value, {
      display_name: editForm.display_name,
      status: editForm.status,
    })
    setMessage(`账号 ${response.data.data.username} 已更新`)
    editingId.value = null
    await loadAccounts()
  } catch (reason) {
    setError(reason)
  } finally {
    saving.value = false
  }
}

// ---------------------------------------------------------------- 角色授权
const grantForm = reactive({ accountId: '', role_code: 'R03', club_id: '' })
const showGrantClub = computed(() => grantForm.role_code === 'R02')

function resetGrantForm() {
  grantForm.accountId = ''
  grantForm.role_code = 'R03'
  grantForm.club_id = ''
}

async function grantRole() {
  if (!grantForm.accountId) {
    setError({ message: '请选择要授权的账号' })
    return
  }
  if (grantForm.role_code === 'R02' && !grantForm.club_id) {
    setError({ message: '授予 R02 必须指定具体社团' })
    return
  }
  saving.value = true
  resetFeedback()
  try {
    const payload = { role_code: grantForm.role_code }
    if (grantForm.role_code === 'R02') payload.club_id = Number(grantForm.club_id)
    const response = await grantRoleApi(Number(grantForm.accountId), payload)
    const target = response.data.data
    const scope = target.club_id ? `（社团 #${target.club_id}）` : ''
    setMessage(`已授予 ${target.role_code}${scope}`)
    resetGrantForm()
    await loadAccounts()
  } catch (reason) {
    setError(reason)
  } finally {
    saving.value = false
  }
}

async function revokeSystemRole(account, roleCode) {
  if (!window.confirm(`确认撤销 ${account.username} 的 ${roleCode} 授权吗？历史业务数据会保留。`)) return
  resetFeedback()
  try {
    await revokeSystemRoleApi(account.user_id, roleCode)
    setMessage(`已撤销 ${account.username} 的 ${roleCode} 授权`)
    await loadAccounts()
  } catch (reason) {
    setError(reason)
  }
}

async function revokeClubRole(account, clubId) {
  if (!window.confirm(`确认撤销 ${account.username} 对 ${clubLabel(clubId)} 的 R02 授权吗？`)) return
  resetFeedback()
  try {
    await revokeClubRoleApi(account.user_id, clubId)
    setMessage(`已撤销 ${account.username} 对 ${clubLabel(clubId)} 的 R02 授权`)
    await loadAccounts()
  } catch (reason) {
    setError(reason)
  }
}

onMounted(async () => {
  if (!isAdmin.value) return
  await Promise.all([loadAccounts(), loadClubs()])
})
</script>

<template>
  <section>
    <h2>账号与角色授权（M01 / FR-23）</h2>
    <p class="muted">
      仅 R04 系统管理员可创建测试账号、启停账号，并授予或撤销 R02、R03、R04 授权身份。
      账号和授权变更只做停用，不删除历史业务数据；R01 为基础身份，不可撤销。
    </p>

    <p v-if="message" class="message ok">{{ message }}</p>
    <p v-if="error" class="message error">{{ error }}</p>

    <div v-if="!isAdmin" class="card">
      <p>当前身份没有 R04 权限，无法访问账号与授权管理。</p>
    </div>

    <template v-else>
      <div class="filters">
        <button class="btn primary" @click="showCreate = !showCreate">
          {{ showCreate ? '收起新建表单' : '新建账号' }}
        </button>
        <button class="btn" :disabled="loading" @click="refresh">{{ loading ? '加载中…' : '刷新' }}</button>
      </div>

      <form v-if="showCreate" class="card form-grid" @submit.prevent="createAccount">
        <label>用户名<input v-model="createForm.username" maxlength="64" required /></label>
        <label>显示名称<input v-model="createForm.display_name" maxlength="100" required /></label>
        <label>初始密码<input v-model="createForm.password" type="password" minlength="8" maxlength="128" required /></label>
        <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '创建中…' : '创建账号' }}</button>
      </form>

      <div class="card" style="margin-top: 1rem">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>显示名称</th>
              <th>状态</th>
              <th>系统角色</th>
              <th>社团 R02 授权</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="account in accounts" :key="account.user_id">
              <td>{{ account.user_id }}</td>
              <td>{{ account.username }}</td>
              <td>{{ account.display_name }}</td>
              <td>
                <span class="badge" :class="account.status === 'NORMAL' ? 'ok' : 'danger'">
                  {{ STATUS_LABELS[account.status] || account.status }}
                </span>
              </td>
              <td>
                <span v-for="role in account.system_roles" :key="role" class="badge">{{ ROLE_LABELS[role] || role }}</span>
                <span v-if="account.system_roles.length === 0" class="muted">—</span>
              </td>
              <td>
                <span v-for="grant in account.club_authorizations" :key="grant.club_id" class="badge warn">
                  {{ clubLabel(grant.club_id) }}
                  <button class="link" type="button" @click="revokeClubRole(account, grant.club_id)">撤销</button>
                </span>
                <span v-if="account.club_authorizations.length === 0" class="muted">—</span>
              </td>
              <td>
                <button class="btn" type="button" @click="startEdit(account)">编辑</button>
                <button
                  v-for="role in account.system_roles.filter((item) => REVOCABLE_SYSTEM_ROLES.has(item))"
                  :key="role"
                  class="btn danger"
                  type="button"
                  @click="revokeSystemRole(account, role)"
                >撤销 {{ role }}</button>
              </td>
            </tr>
            <tr v-if="accounts.length === 0">
              <td colspan="7" class="muted">暂无账号</td>
            </tr>
          </tbody>
        </table>

        <div class="pager">
          <button class="btn" :disabled="page <= 1" @click="changePage(-1)">上一页</button>
          <span>第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 个账号</span>
          <button class="btn" :disabled="page >= pageCount" @click="changePage(1)">下一页</button>
        </div>
      </div>

      <form v-if="editingId" class="card form-grid" style="margin-top: 1rem" @submit.prevent="saveEdit">
        <h3>编辑账号 #{{ editingId }}</h3>
        <label>显示名称<input v-model="editForm.display_name" maxlength="100" required /></label>
        <label>
          状态
          <select v-model="editForm.status">
            <option value="NORMAL">正常</option>
            <option value="DISABLED">已停用</option>
          </select>
        </label>
        <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
        <button class="btn" type="button" @click="cancelEdit">取消</button>
      </form>

      <form class="card form-grid" style="margin-top: 1rem" @submit.prevent="grantRole">
        <h3>授予角色</h3>
        <label>
          账号
          <select v-model="grantForm.accountId" required>
            <option value="">请选择账号</option>
            <option v-for="account in accounts" :key="account.user_id" :value="account.user_id">
              #{{ account.user_id }} {{ account.username }}（{{ account.display_name }}）
            </option>
          </select>
        </label>
        <label>
          角色
          <select v-model="grantForm.role_code">
            <option v-for="role in GRANTABLE_ROLES" :key="role.code" :value="role.code">{{ role.label }}</option>
          </select>
        </label>
        <label v-if="showGrantClub">
          目标社团
          <select v-model="grantForm.club_id" required>
            <option value="">请选择社团</option>
            <option v-for="club in clubs" :key="club.id" :value="club.id">
              #{{ club.id }} {{ club.name }}
            </option>
          </select>
        </label>
        <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '提交中…' : '授予' }}</button>
        <p class="muted">R02 必须绑定具体社团；R03、R04 为系统级授权，不能指定社团。</p>
      </form>
    </template>
  </section>
</template>

<style scoped>
.badge + .badge { margin-left: 0.35rem; }
.link {
  margin-left: 0.35rem;
  padding: 0;
  border: none;
  background: transparent;
  color: #b91c1c;
  cursor: pointer;
  font-size: 0.75rem;
  text-decoration: underline;
}
.btn + .btn { margin-left: 0.4rem; }
</style>
