import { afterEach, describe, expect, it } from 'vitest'

import client from './client.js'

const originalAdapter = client.defaults.adapter

function successAdapter(capture) {
  return async (config) => {
    capture(config)
    return { data: { code: 200, data: null }, status: 200, statusText: 'OK', headers: {}, config }
  }
}

afterEach(() => {
  client.defaults.adapter = originalAdapter
  localStorage.clear()
})

describe('request interceptor', () => {
  it('adds the bearer token from localStorage', async () => {
    localStorage.setItem('access_token', 'token-1')
    let seen
    client.defaults.adapter = successAdapter((config) => {
      seen = config
    })

    await client.get('/auth/me')

    expect(seen.headers.Authorization).toBe('Bearer token-1')
    expect(client.defaults.baseURL).toMatch(/\/api\/v1$/)
  })

  it('does not add authorization when no token is stored', async () => {
    let seen
    client.defaults.adapter = successAdapter((config) => {
      seen = config
    })

    await client.get('/health')

    expect(seen.headers.Authorization).toBeUndefined()
  })
})

describe('response interceptor', () => {
  it('unwraps backend error envelopes', async () => {
    const envelope = { code: 40101, message: '登录状态已失效', data: null }
    client.defaults.adapter = async () => Promise.reject({ response: { data: envelope } })

    await expect(client.get('/auth/me')).rejects.toEqual(envelope)
  })

  it('keeps network errors without a response body', async () => {
    const networkError = new Error('Network Error')
    client.defaults.adapter = async () => Promise.reject(networkError)

    await expect(client.get('/health')).rejects.toBe(networkError)
  })
})
