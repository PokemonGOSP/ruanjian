import client from './client.js'

export const loginApi = (credentials) => client.post('/auth/login', credentials)
export const logoutApi = () => client.post('/auth/logout')
export const meApi = () => client.get('/auth/me')
