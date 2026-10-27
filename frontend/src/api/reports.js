import client from './client.js'

export const summarizeReport = (params) => client.get('/reports/summary', { params })
export const exportReport = (params) =>
  client.get('/reports/export', { params, responseType: 'blob' })
export const listAuditLogs = (params) => client.get('/audit-logs', { params })
