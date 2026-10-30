import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('../api/auth.js', () => ({
  loginApi: vi.fn(),
  logoutApi: vi.fn(),
  meApi: vi.fn(),
}))

import { logoutApi, meApi } from '../api/auth.js'
import { useAuthStore } from '../stores/auth.js'
import router from './index.js'

function signIn(store, user = { id: 1, username: 'student01' }) {
  store.token = 'token-1'
  store.user = user
}

describe('router authentication guard', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('redirects unauthenticated visitors to the login page', async () => {
    await router.push('/activities')

    expect(router.currentRoute.value.name).toBe('login')
  })

  it('allows an authenticated user with a loaded profile', async () => {
    const store = useAuthStore()
    signIn(store)

    await router.push('/activities')

    expect(router.currentRoute.value.path).toBe('/activities')
    expect(meApi).not.toHaveBeenCalled()
  })

  it('loads the profile before entering a protected route', async () => {
    meApi.mockResolvedValue({ data: { data: { id: 5, username: 'leader01' } } })
    const store = useAuthStore()
    store.token = 'token-1'

    await router.push('/clubs')

    expect(meApi).toHaveBeenCalledOnce()
    expect(store.user).toEqual({ id: 5, username: 'leader01' })
    expect(router.currentRoute.value.path).toBe('/clubs')
  })

  it('sends authenticated users away from the login page', async () => {
    const store = useAuthStore()
    signIn(store)

    await router.push('/login')

    expect(router.currentRoute.value.name).toBe('dashboard')
  })

  it('logs out and redirects when the profile cannot be loaded', async () => {
    meApi.mockRejectedValue(new Error('401'))
    logoutApi.mockResolvedValue({})
    const store = useAuthStore()
    store.token = 'token-1'

    await router.push('/reports')

    expect(logoutApi).toHaveBeenCalledOnce()
    expect(store.token).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(router.currentRoute.value.name).toBe('login')
  })
})
