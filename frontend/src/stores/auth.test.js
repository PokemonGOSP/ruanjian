import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/auth.js', () => ({
  loginApi: vi.fn(),
  logoutApi: vi.fn(),
  meApi: vi.fn(),
}))

import { loginApi, logoutApi, meApi } from '../api/auth.js'
import { useAuthStore } from './auth.js'

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('logs in, persists the token and loads the current user', async () => {
    loginApi.mockResolvedValue({ data: { data: { access_token: 'token-1' } } })
    meApi.mockResolvedValue({ data: { data: { id: 1, username: 'student01' } } })
    const store = useAuthStore()

    await store.login({ username: 'student01', password: 'Student123!' })

    expect(loginApi).toHaveBeenCalledWith({ username: 'student01', password: 'Student123!' })
    expect(store.token).toBe('token-1')
    expect(localStorage.getItem('access_token')).toBe('token-1')
    expect(store.user).toEqual({ id: 1, username: 'student01' })
    expect(store.isAuthenticated).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('resets loading when login fails', async () => {
    loginApi.mockRejectedValue(new Error('bad credentials'))
    const store = useAuthStore()

    await expect(store.login({})).rejects.toThrow('bad credentials')

    expect(store.loading).toBe(false)
    expect(store.token).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('stores the user returned by fetchMe', async () => {
    meApi.mockResolvedValue({ data: { data: { id: 2, username: 'leader01' } } })
    const store = useAuthStore()

    const user = await store.fetchMe()

    expect(user).toEqual({ id: 2, username: 'leader01' })
    expect(store.user).toEqual({ id: 2, username: 'leader01' })
  })

  it('clears local state even if logout fails', async () => {
    localStorage.setItem('access_token', 'token-1')
    logoutApi.mockRejectedValue(new Error('network'))
    const store = useAuthStore()
    store.token = 'token-1'
    store.user = { id: 1 }

    await expect(store.logout()).rejects.toThrow('network')

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('skips the logout request without a token', async () => {
    const store = useAuthStore()

    await store.logout()

    expect(logoutApi).not.toHaveBeenCalled()
    expect(store.isAuthenticated).toBe(false)
  })
})
