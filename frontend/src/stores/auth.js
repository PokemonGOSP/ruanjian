import { defineStore } from 'pinia'
import { loginApi, logoutApi, meApi } from '../api/auth.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({ token: localStorage.getItem('access_token'), user: null, loading: false }),
  getters: { isAuthenticated: (state) => Boolean(state.token) },
  actions: {
    async login(credentials) {
      this.loading = true
      try {
        const response = await loginApi(credentials)
        this.token = response.data.data.access_token
        localStorage.setItem('access_token', this.token)
        try {
          await this.fetchMe()
        } catch (reason) {
          this.clearSession()
          throw reason
        }
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      const response = await meApi()
      this.user = response.data.data
      return this.user
    },
    async logout() {
      try {
        if (this.token) await logoutApi()
      } catch {
        // 后端不可达时仍完成本地退出，避免停留在受保护页面。
      } finally {
        this.clearSession()
      }
    },
    clearSession() {
      this.token = null
      this.user = null
      localStorage.removeItem('access_token')
    },
  },
})
