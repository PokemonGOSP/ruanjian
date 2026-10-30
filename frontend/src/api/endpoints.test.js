import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockClient } = vi.hoisted(() => ({
  mockClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('./client.js', () => ({ default: mockClient }))

import * as accounts from './accounts.js'
import * as activities from './activities.js'
import * as clubs from './clubs.js'
import * as finance from './finance.js'
import * as members from './members.js'
import * as notifications from './notifications.js'
import * as reports from './reports.js'

beforeEach(() => {
  for (const method of ['get', 'post', 'patch', 'delete']) {
    mockClient[method].mockReset()
    mockClient[method].mockResolvedValue({ data: { data: null } })
  }
})

describe('account endpoints', () => {
  it('lists accounts with query params', () => {
    accounts.listAccountsApi({ page: 2 })

    expect(mockClient.get).toHaveBeenCalledWith('/accounts', { params: { page: 2 } })
  })

  it('builds role assignment paths', () => {
    accounts.grantRoleApi(7, { role_code: 'R03' })
    accounts.revokeSystemRoleApi(7, 'R04')
    accounts.revokeClubRoleApi(7, 3)

    expect(mockClient.post).toHaveBeenCalledWith('/accounts/7/role-assignments', { role_code: 'R03' })
    expect(mockClient.delete).toHaveBeenCalledWith('/accounts/7/role-assignments/R04')
    expect(mockClient.delete).toHaveBeenCalledWith('/accounts/7/club-role-assignments/3')
  })
})

describe('finance endpoints', () => {
  it('voids a record with a reason', () => {
    finance.voidFinanceRecord(9, '重复登记')

    expect(mockClient.post).toHaveBeenCalledWith('/finance-records/9/void', { reason: '重复登记' })
  })

  it('requests a summary with filters', () => {
    finance.summarizeFinance({ club_id: 1 })

    expect(mockClient.get).toHaveBeenCalledWith('/finance-records/summary', { params: { club_id: 1 } })
  })
})

describe('report endpoints', () => {
  it('requests a blob export', () => {
    reports.exportReport({ club_id: 1 })

    expect(mockClient.get).toHaveBeenCalledWith('/reports/export', {
      params: { club_id: 1 },
      responseType: 'blob',
    })
  })
})

describe('activity endpoints', () => {
  it('unwraps the response envelope', async () => {
    mockClient.get.mockResolvedValue({ data: { data: { items: [], total: 0 } } })

    const result = await activities.listActivities({ page: 1 })

    expect(mockClient.get).toHaveBeenCalledWith('/activities', { params: { page: 1 } })
    expect(result).toEqual({ items: [], total: 0 })
  })

  it('uses the current-user registration path', () => {
    activities.registerActivity(4)
    activities.cancelRegistration(4)

    expect(mockClient.post).toHaveBeenCalledWith('/activities/4/registrations')
    expect(mockClient.delete).toHaveBeenCalledWith('/activities/4/registrations/me')
  })

  it('sends review decisions', () => {
    activities.reviewActivity(4, 'APPROVED', '材料完整')

    expect(mockClient.post).toHaveBeenCalledWith('/activities/4/review', {
      decision: 'APPROVED',
      comment: '材料完整',
    })
  })
})

describe('membership, club and notification endpoints', () => {
  it('lists club members with a scoped path', () => {
    members.listClubMembersApi(2, { page: 1 })

    expect(mockClient.get).toHaveBeenCalledWith('/clubs/2/members', { params: { page: 1 } })
  })

  it('marks all notifications read', () => {
    notifications.markAllNotificationsRead()

    expect(mockClient.post).toHaveBeenCalledWith('/notifications/read-all')
  })

  it('reviews a club registration application', () => {
    clubs.reviewRegistrationApi(5, { decision: 'APPROVED' })

    expect(mockClient.post).toHaveBeenCalledWith('/club-registration-applications/5/review', {
      decision: 'APPROVED',
    })
  })
})
