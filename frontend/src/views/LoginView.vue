<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const form = reactive({ username: 'student01', password: 'Student123!' })
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  try { await auth.login(form); await router.push('/') }
  catch (reason) { error.value = reason?.message || '登录失败' }
}
</script>

<template>
  <main class="login-page">
    <form class="card" @submit.prevent="submit">
      <h1>高校社团活动管理系统</h1>
      <p>Engineering Skeleton V0.1</p>
      <label>用户名<input v-model="form.username" autocomplete="username" /></label>
      <label>密码<input v-model="form.password" type="password" autocomplete="current-password" /></label>
      <button :disabled="auth.loading">{{ auth.loading ? '登录中…' : '登录' }}</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; padding: 1rem; }
form { width: min(420px, 100%); display: grid; gap: 1rem; }
label { display: grid; gap: .35rem; }
input { padding: .65rem; border: 1px solid #9ca3af; border-radius: 6px; }
button { padding: .7rem; color: white; background: #1d4ed8; border: 0; border-radius: 6px; }
.error { color: #b91c1c; }
</style>
