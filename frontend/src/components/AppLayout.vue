<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()
const links = [
  ['/', '首页'], ['/clubs', '社团/年审'], ['/members', '成员'], ['/activities', '活动'],
  ['/finance', '经费'], ['/notifications', '通知'], ['/reports', '统计/审计'], ['/accounts', '账号/授权'],
]
async function logout() { await auth.logout(); await router.push('/login') }
</script>

<template>
  <div class="layout">
    <aside>
      <h1>社团管理</h1>
      <RouterLink v-for="[path, label] in links" :key="path" :to="path">{{ label }}</RouterLink>
    </aside>
    <main>
      <header>
        <span>{{ auth.user?.display_name }}（{{ auth.user?.system_roles?.join('、') }}）</span>
        <button @click="logout">退出</button>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout { min-height: 100vh; display: grid; grid-template-columns: 220px 1fr; }
aside { background: #172554; color: white; padding: 1.25rem; display: flex; flex-direction: column; gap: .5rem; }
aside h1 { font-size: 1.2rem; }
aside a { padding: .65rem; border-radius: 6px; }
aside a.router-link-active { background: #1d4ed8; }
main { padding: 1.5rem; }
header { display: flex; justify-content: flex-end; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
button { padding: .45rem .9rem; }
</style>
