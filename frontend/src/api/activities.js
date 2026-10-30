import client from './client'

const unwrap = (response) => response.data.data

export const listActivities = (params) =>
  client.get('/activities', { params }).then(unwrap)

export const getActivity = (activityId) =>
  client.get(`/activities/${activityId}`).then(unwrap)

export const createActivity = (payload) =>
  client.post('/activities', payload).then(unwrap)

export const updateActivity = (activityId, payload) =>
  client.patch(`/activities/${activityId}`, payload).then(unwrap)

export const submitActivity = (activityId) =>
  client.post(`/activities/${activityId}/submit`).then(unwrap)

export const withdrawActivity = (activityId) =>
  client.post(`/activities/${activityId}/withdraw`).then(unwrap)

export const reviewActivity = (activityId, decision, comment) =>
  client.post(`/activities/${activityId}/review`, { decision, comment }).then(unwrap)

export const publishActivity = (activityId) =>
  client.post(`/activities/${activityId}/publish`).then(unwrap)

export const registerActivity = (activityId) =>
  client.post(`/activities/${activityId}/registrations`).then(unwrap)

export const cancelRegistration = (activityId) =>
  client.delete(`/activities/${activityId}/registrations/me`).then(unwrap)

export const listRegistrations = (activityId, params) =>
  client.get(`/activities/${activityId}/registrations`, { params }).then(unwrap)

export const cancelActivity = (activityId, reason) =>
  client.post(`/activities/${activityId}/cancel`, { reason }).then(unwrap)

export const endActivity = (activityId, summary) =>
  client.post(`/activities/${activityId}/end`, { summary }).then(unwrap)
