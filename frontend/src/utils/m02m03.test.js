import { describe, expect, it } from 'vitest'

import {
  MEMBERSHIP_STATUS_LABELS,
  MEMBERSHIP_TYPE_LABELS,
  MEMBER_STATUS_LABELS,
  REVIEW_STATUS_LABELS,
  formatDateTime,
} from './m02m03.js'

describe('label maps', () => {
  it('covers every review status', () => {
    expect(REVIEW_STATUS_LABELS).toEqual({
      DRAFT: '草稿',
      PENDING: '待审核',
      APPROVED: '已通过',
      REJECTED: '已驳回',
      WITHDRAWN: '已撤回',
    })
  })

  it('covers membership status and type', () => {
    expect(MEMBERSHIP_STATUS_LABELS.APPROVED).toBe('已同意')
    expect(MEMBERSHIP_TYPE_LABELS).toEqual({ JOIN: '入团', EXIT: '退出' })
    expect(MEMBER_STATUS_LABELS.EXITED).toBe('已退出')
  })
})

describe('formatDateTime', () => {
  it('formats valid timestamps', () => {
    const text = formatDateTime('2026-10-31T08:00:00')
    expect(text).not.toBe('—')
    expect(text).toContain('2026')
  })

  it('keeps unparseable values as-is', () => {
    expect(formatDateTime('not-a-date')).toBe('not-a-date')
  })

  it('returns a dash for empty values', () => {
    expect(formatDateTime(null)).toBe('—')
  })
})
