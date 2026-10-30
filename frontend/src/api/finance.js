import client from './client.js'

export const summarizeFinance = (params) => client.get('/finance-records/summary', { params })
export const listFinanceRecords = (params) => client.get('/finance-records', { params })
export const createFinanceRecord = (payload) => client.post('/finance-records', payload)
export const updateFinanceRecord = (recordId, payload) => client.patch(`/finance-records/${recordId}`, payload)
export const voidFinanceRecord = (recordId, reason) => client.post(`/finance-records/${recordId}/void`, { reason })
