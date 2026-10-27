<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  publishManagementNotification,
} from '../api/notifications.js'
import { formatDateTime, parseIdList } from '../utils/format.js'

const PAGE_SIZE = 20
const roleOptions = [
  { code: 'R01', label: 'R01 学生用户' },
  { code: 'R02', label: 'R02 社团负责人' },
  { code: 'R03', label: 'R03 社团管理人员' },
  { code: 'R04', label: 'R04 系统管理员' },
]
const eventLabels = {
  MANAGEMENT_NOTICE: '管理通知',
  REVIEW_RESULT: '审核结果',
  ACTIVITY_REGISTRATION: '活动报名',
  ACTIVITY_CANCELLED: '活动取消',
  MEMBERSHIP_RESULT: '成员申请结果',
  CLUB_REGISTRATION_RESULT: '社团注册结果',
}

const auth = useAuthStore()
const isManager = computed(() => Boolean(auth.user?.system_roles?.includes('R03')))

const notifications = ref([])
const total = ref(0)
const page = ref(1)
const unreadOnly = ref(false)
const loading = ref(false)
const error = ref('')
const message = ref('')
const form = reactive({
  title: '',
  content: '',
  targetType: 'CLUBS',
  userIds: '',
  roleCodes: ['R01'],
  clubIds: '',
})

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const unreadCount = computed(() => notifications.value.filter((row) => row.read_status === 'UNREAD').length)

function showError(reason) {
  error.value = reason?.message || '操作失败，请稍后重试'
}

async function load() {
  loading.value = true
  error.value = ''
  const params = { page: page.value, page_size: PAGE_SIZE }
  if (unreadOnly.value) params.read_status = 'UNREAD'
  try {
    const response = await listNotifications(params)
    notifications.value = response.data.data.items
    total.value = response.data.data.total
  } catch (reason) {
    showError(reason)
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function changePage(offset) {
  const next = page.value + offset
  if (next < 1 || next > pageCount.value) return
  page.value = next
  load()
}

async function markRead(row) {
  error.value = ''
  message.value = ''
  try {
    await markNotificationRead(row.id)
    if (unreadOnly.value) {
      await load()
    } else {
      row.read_status = 'READ'
      row.read_at = new Date().toISOString()
    }
    message.value = '通知已标记为已读'
  } catch (reason) {
    showError(reason)
  }
}

async function readAll() {
  error.value = ''
  message.value = ''
  try {
    await markAllNotificationsRead()
    message.value = '全部未读通知已标记为已读'
    await load()
  } catch (reason) {
    showError(reason)
  }
}

async function publish() {
  error.value = ''
  message.value = ''
  if (!form.title.trim() || !form.content.trim()) {
    error.value = '请填写通知标题和内容'
    return
  }
  const payload = {
    title: form.title.trim(),
    content: form.content.trim(),
    target_type: form.targetType,
  }
  if (form.targetType === 'USERS') payload.user_ids = parseIdList(form.userIds)
  if (form.targetType === 'ROLES') payload.role_codes = [...form.roleCodes]
  if (form.targetType === 'CLUBS') payload.club_ids = parseIdList(form.clubIds)
  try {
    const response = await publishManagementNotification(payload)
    message.value = `管理通知已生成，接收人数：${response.data.data.recipient_count}`
    form.title = ''
    form.content = ''
    page.value = 1
    await load()
  } catch (reason) {
    showError(reason)
  }
}

onMounted(load)
</script>

<template>
  <section class="card">
    <h2>通知中心（M06）</h2>
    <p class="muted">
      FR-19～FR-20：仅站内通知。系统通知按当前登录用户隔离；R03 可向指定社团、角色或用户范围发布管理通知。
    </p>

    <p v-if="error" class="message error">{{ error }}</p>
    <p v-if="message" class="message ok">{{ message }}</p>

    <div v-if="isManager" class="form-panel">
      <h3>发布管理通知（R03）</h3>
      <div class="form-grid">
        <label class="wide">
          标题
          <input v-model="form.title" maxlength="200" placeholder="通知标题" />
        </label>
        <label class="wide">
          内容
          <textarea v-model="form.content" maxlength="5000" rows="3" placeholder="通知内容" />
        </label>
        <label>
          目标类型
          <select v-model="form.targetType">
            <option value="CLUBS">指定社团</option>
            <option value="ROLES">指定角色</option>
            <option value="USERS">指定用户</option>
          </select>
        </label>
        <label v-if="form.targetType === 'USERS'" class="wide">
          用户 ID（逗号或空格分隔）
          <input v-model="form.userIds" placeholder="例如：1,2,3" />
        </label>
        <label v-if="form.targetType === 'ROLES'" class="wide">
          角色
          <span class="checkbox-row">
            <span v-for="role in roleOptions" :key="role.code" class="checkbox">
              <input v-model="form.roleCodes" type="checkbox" :value="role.code" />
              {{ role.label }}
            </span>
          </span>
        </label>
        <label v-if="form.targetType === 'CLUBS'" class="wide">
          社团 ID（逗号或空格分隔）
          <input v-model="form.clubIds" placeholder="例如：1,2" />
        </label>
        <div class="form-actions">
          <button class="btn primary" :disabled="loading" @click="publish">发布通知</button>
        </div>
      </div>
      <p class="muted">R02 角色目标会发送给全部有效社团负责人；社团目标会覆盖有效成员与负责人。</p>
    </div>

    <div class="filters">
      <label class="checkbox">
        <input v-model="unreadOnly" type="checkbox" @change="applyFilter" />
        只看未读
      </label>
      <span class="muted">本页未读：{{ unreadCount }}</span>
      <button class="btn" :disabled="loading" @click="load">刷新</button>
      <button class="btn" :disabled="loading" @click="readAll">全部标记已读</button>
    </div>

    <div class="notification-list">
      <article
        v-for="row in notifications"
        :key="row.id"
        class="notification"
        :class="{ unread: row.read_status === 'UNREAD' }"
      >
        <header>
          <div>
            <strong>{{ row.title }}</strong>
            <span class="badge">{{ eventLabels[row.event_type] || row.event_type }}</span>
          </div>
          <span class="badge" :class="row.read_status === 'UNREAD' ? 'warn' : 'ok'">
            {{ row.read_status === 'UNREAD' ? '未读' : '已读' }}
          </span>
        </header>
        <p>{{ row.content }}</p>
        <footer>
          <span class="muted">{{ formatDateTime(row.created_at) }}</span>
          <button
            v-if="row.read_status === 'UNREAD'"
            class="btn"
            :disabled="loading"
            @click="markRead(row)"
          >
            标记已读
          </button>
        </footer>
      </article>
      <p v-if="!notifications.length" class="muted">暂无通知。</p>
    </div>

    <div class="pager">
      <button class="btn" :disabled="page <= 1 || loading" @click="changePage(-1)">上一页</button>
      <span class="muted">第 {{ page }} / {{ pageCount }} 页，共 {{ total }} 条</span>
      <button class="btn" :disabled="page >= pageCount || loading" @click="changePage(1)">下一页</button>
    </div>
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
  flex: 1 1 300px;
}
.checkbox-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.form-actions {
  display: flex;
  align-items: center;
}
.notification-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
.notification {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.85rem;
  background: white;
}
.notification.unread {
  border-left: 4px solid #1d4ed8;
  background: #f8fbff;
}
.notification header,
.notification footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}
.notification header > div {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.notification p {
  margin: 0.6rem 0;
  white-space: pre-wrap;
}
</style>
