<script setup>
defineProps({ title: String, moduleId: String, frs: String, owner: String })
</script>

<template>
  <section class="card">
    <h2>{{ title }}</h2>
    <p>模块：{{ moduleId }}</p>
    <p>需求：{{ frs }}</p>
    <p><strong>TODO({{ owner }})</strong>：当前仅提供路由与页面占位，不包含完整业务 UI。</p>
  </section>
</template>
