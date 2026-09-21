<script setup>
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
</script>

<template>
  <section class="card">
    <h2>首页 / Dashboard</h2>
    <p>欢迎，{{ auth.user?.display_name }}（{{ auth.user?.username }}）。</p>
    <p>系统身份：{{ auth.user?.system_roles?.join('、') || '无' }}</p>
    <p>负责社团：{{ auth.user?.club_authorizations?.map((item) => item.club_name).join('、') || '无' }}</p>
    <p>已实现链路：登录 → JWT → /auth/me → Pinia → 当前页面。</p>
  </section>
</template>
