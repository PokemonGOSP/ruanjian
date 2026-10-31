<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import { summarizeReport } from '../api/reports.js'
import { formatAmount } from '../utils/format.js'

const ROLE_LABELS = {
  R01: '学生用户',
  R02: '社团负责人',
  R03: '社团管理人员',
  R04: '系统管理员',
}

const MODULES = [
  {
    path: '/clubs',
    title: '社团 / 年审',
    desc: '注册申请、社团资料与年度审查',
    roles: ['R01', 'R02', 'R03', 'R04'],
  },
  {
    path: '/members',
    title: '成员管理',
    desc: '入团退出申请、成员名册与职务',
    roles: ['R01', 'R02', 'R03', 'R04'],
  },
  {
    path: '/activities',
    title: '活动管理',
    desc: '活动申报、审核、发布与报名',
    roles: ['R01', 'R02', 'R03', 'R04'],
  },
  {
    path: '/finance',
    title: '经费记录',
    desc: '经费登记、修改、作废与汇总',
    roles: ['R02', 'R03', 'R04'],
  },
  {
    path: '/notifications',
    title: '通知中心',
    desc: '站内通知、已读标记与公告发布',
    roles: ['R01', 'R02', 'R03', 'R04'],
  },
  {
    path: '/reports',
    title: '统计 / 审计',
    desc: '综合统计、经费 CSV 与审计日志',
    roles: ['R02', 'R03', 'R04'],
  },
  {
    path: '/accounts',
    title: '账号 / 授权',
    desc: '账号启停与 R02 / R03 / R04 授权',
    roles: ['R04'],
  },
]

const auth = useAuthStore()
const roles = computed(() => auth.user?.system_roles || [])
const clubs = computed(() => auth.user?.club_authorizations || [])
// R02 是“用户—具体社团”的资源级授权，不在 system_roles 中，需要单独判断。
const effectiveRoles = computed(() =>
  clubs.value.length ? [...roles.value, 'R02'] : roles.value,
)
const canViewStats = computed(
  () => roles.value.includes('R03') || clubs.value.length > 0,
)
const visibleModules = computed(() =>
  MODULES.filter((module) =>
    module.roles.some((role) => effectiveRoles.value.includes(role)),
  ),
)

const summary = ref(null)
const statsLoading = ref(false)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

function roleLabel(role) {
  return ROLE_LABELS[role] || role
}

async function loadSummary() {
  if (!canViewStats.value) return
  statsLoading.value = true
  try {
    const response = await summarizeReport()
    summary.value = response.data.data
  } catch {
    summary.value = null
  } finally {
    statsLoading.value = false
  }
}

onMounted(loadSummary)
</script>

<template>
  <section class="card hero">
    <div class="hero-main">
      <p class="eyebrow">高校社团活动管理系统</p>
      <h2>首页</h2>
      <p class="welcome">
        {{ greeting }}，{{ auth.user?.display_name }}（{{ auth.user?.username }}）。
      </p>
      <p class="muted">当前身份可在下方入口进入对应模块；不同角色看到的入口与数据范围不同。</p>
    </div>
    <div class="identity">
      <div class="row">
        <span class="k">系统角色</span>
        <span class="v">
          <span v-for="role in roles" :key="role" class="badge ok">{{ roleLabel(role) }}</span>
          <span v-if="!roles.length" class="badge">无</span>
        </span>
      </div>
      <div class="row">
        <span class="k">负责社团</span>
        <span class="v">
          <span v-for="club in clubs" :key="club.club_id" class="badge">
            {{ club.club_name }}
          </span>
          <span v-if="!clubs.length" class="muted">暂无社团授权</span>
        </span>
      </div>
    </div>
  </section>

  <section v-if="canViewStats" class="card">
    <h3>数据概览</h3>
    <p class="muted">
      统计范围：{{ roles.includes('R03') ? '全校' : '本人负责的社团' }}；口径与「统计 / 审计」页一致。
    </p>
    <p v-if="statsLoading" class="muted">正在加载统计数据…</p>
    <div v-else-if="summary" class="stat-grid">
      <div class="stat"><span>社团数</span><strong>{{ summary.club_count }}</strong></div>
      <div class="stat"><span>有效成员</span><strong>{{ summary.member_count }}</strong></div>
      <div class="stat"><span>活动数</span><strong>{{ summary.activity_count }}</strong></div>
      <div class="stat"><span>有效报名</span><strong>{{ summary.registration_count }}</strong></div>
      <div class="stat"><span>经费结余</span><strong>{{ formatAmount(summary.finance_balance) }}</strong></div>
    </div>
    <p v-else class="muted">统计数据暂不可用。</p>
  </section>

  <section class="card">
    <h3>快捷入口</h3>
    <div class="module-grid">
      <RouterLink v-for="module in visibleModules" :key="module.path" class="module" :to="module.path">
        <span class="module-title">{{ module.title }}</span>
        <span class="module-desc">{{ module.desc }}</span>
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(240px, 1fr);
  gap: 1.5rem;
  margin-bottom: 1rem;
}
.eyebrow {
  margin: 0;
  color: #1d4ed8;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
}
.hero h2 {
  margin: 0.25rem 0 0.5rem;
  font-size: 1.5rem;
}
.welcome {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
}
.identity {
  display: grid;
  gap: 0.75rem;
  align-content: start;
  padding: 0.9rem 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
}
.identity .row {
  display: grid;
  gap: 0.35rem;
}
.identity .k {
  color: #6b7280;
  font-size: 0.8rem;
}
.identity .v {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  font-size: 0.9rem;
}
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}
.module {
  display: grid;
  gap: 0.3rem;
  padding: 0.9rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.module:hover {
  border-color: #1d4ed8;
  box-shadow: 0 2px 8px rgba(29, 78, 216, 0.12);
}
.module-title {
  font-weight: 600;
}
.module-desc {
  color: #6b7280;
  font-size: 0.85rem;
}
@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }
}
</style>
