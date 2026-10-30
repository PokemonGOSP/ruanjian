import client from './client.js'

export const listClubsApi = (params = {}) => client.get('/clubs', { params })
export const getClubApi = (clubId) => client.get(`/clubs/${clubId}`)
export const updateClubApi = (clubId, payload) => client.patch(`/clubs/${clubId}`, payload)

export const createRegistrationApi = (payload) => client.post('/club-registration-applications', payload)
export const listRegistrationsApi = (params = {}) => client.get('/club-registration-applications', { params })
export const updateRegistrationApi = (applicationId, payload) =>
  client.patch(`/club-registration-applications/${applicationId}`, payload)
export const submitRegistrationApi = (applicationId) =>
  client.post(`/club-registration-applications/${applicationId}/submit`)
export const withdrawRegistrationApi = (applicationId) =>
  client.post(`/club-registration-applications/${applicationId}/withdraw`)
export const reviewRegistrationApi = (applicationId, payload) =>
  client.post(`/club-registration-applications/${applicationId}/review`, payload)

export const createAnnualReviewApi = (payload) => client.post('/annual-reviews', payload)
export const listAnnualReviewsApi = (params = {}) => client.get('/annual-reviews', { params })
export const updateAnnualReviewApi = (applicationId, payload) =>
  client.patch(`/annual-reviews/${applicationId}`, payload)
export const submitAnnualReviewApi = (applicationId) => client.post(`/annual-reviews/${applicationId}/submit`)
export const withdrawAnnualReviewApi = (applicationId) =>
  client.post(`/annual-reviews/${applicationId}/withdraw`)
export const reviewAnnualReviewApi = (applicationId, payload) =>
  client.post(`/annual-reviews/${applicationId}/review`, payload)
