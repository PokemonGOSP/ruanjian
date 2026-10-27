import client from './client.js'

export const listNotifications = (params) => client.get('/notifications', { params })
export const markNotificationRead = (notificationId) => client.post(`/notifications/${notificationId}/read`)
export const markAllNotificationsRead = () => client.post('/notifications/read-all')
export const publishManagementNotification = (payload) => client.post('/notifications/management', payload)
