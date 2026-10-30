import client from './client.js'

export const createMembershipApplicationApi = (payload) => client.post('/membership-applications', payload)
export const listMembershipApplicationsApi = (params = {}) =>
  client.get('/membership-applications', { params })
export const withdrawMembershipApplicationApi = (applicationId) =>
  client.post(`/membership-applications/${applicationId}/withdraw`)
export const processMembershipApplicationApi = (applicationId, payload) =>
  client.post(`/membership-applications/${applicationId}/process`, payload)

export const listClubMembersApi = (clubId, params = {}) => client.get(`/clubs/${clubId}/members`, { params })
export const updateClubMemberApi = (clubId, memberId, payload) =>
  client.patch(`/clubs/${clubId}/members/${memberId}`, payload)
