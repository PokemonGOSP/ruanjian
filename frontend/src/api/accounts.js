import client from './client.js'

export const listAccountsApi = (params = {}) => client.get('/accounts', { params })
export const createAccountApi = (payload) => client.post('/accounts', payload)
export const updateAccountApi = (accountId, payload) => client.patch(`/accounts/${accountId}`, payload)
export const grantRoleApi = (accountId, payload) =>
  client.post(`/accounts/${accountId}/role-assignments`, payload)
export const revokeSystemRoleApi = (accountId, roleCode) =>
  client.delete(`/accounts/${accountId}/role-assignments/${roleCode}`)
export const revokeClubRoleApi = (accountId, clubId) =>
  client.delete(`/accounts/${accountId}/club-role-assignments/${clubId}`)
