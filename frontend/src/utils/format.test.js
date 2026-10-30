import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  downloadBlob,
  formatAmount,
  formatDate,
  formatDateTime,
  parseIdList,
  todayInput,
} from './format.js'

describe('formatDateTime', () => {
  it('returns a dash for empty values', () => {
    expect(formatDateTime(null)).toBe('—')
    expect(formatDateTime('')).toBe('—')
  })

  it('replaces the ISO separator and trims to seconds', () => {
    expect(formatDateTime('2026-10-31T09:05:07.123456')).toBe('2026-10-31 09:05:07')
  })
})

describe('formatDate', () => {
  it('keeps only the date part', () => {
    expect(formatDate('2026-10-31T09:05:07')).toBe('2026-10-31')
  })

  it('returns a dash for empty values', () => {
    expect(formatDate(undefined)).toBe('—')
  })
})

describe('formatAmount', () => {
  it('formats numbers with two decimals', () => {
    expect(formatAmount(12.345)).toBe('12.35')
    expect(formatAmount('8')).toBe('8.00')
  })

  it('falls back to zero for invalid values', () => {
    expect(formatAmount('abc')).toBe('0.00')
    expect(formatAmount(undefined)).toBe('0.00')
  })
})

describe('todayInput', () => {
  it('returns a local ISO date', () => {
    expect(todayInput()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})

describe('parseIdList', () => {
  it('parses comma, Chinese comma and whitespace separated ids', () => {
    expect(parseIdList('1, 2，3  4')).toEqual([1, 2, 3, 4])
  })

  it('drops invalid and non-positive values', () => {
    expect(parseIdList('0 -1 abc 5')).toEqual([5])
  })

  it('handles empty input', () => {
    expect(parseIdList(null)).toEqual([])
  })
})

describe('downloadBlob', () => {
  const originalCreate = URL.createObjectURL
  const originalRevoke = URL.revokeObjectURL

  afterEach(() => {
    URL.createObjectURL = originalCreate
    URL.revokeObjectURL = originalRevoke
    vi.restoreAllMocks()
  })

  it('clicks a temporary link and revokes the object URL', () => {
    const createObjectURL = vi.fn(() => 'blob:test')
    const revokeObjectURL = vi.fn()
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = revokeObjectURL
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    downloadBlob(new Blob(['csv']), 'report.csv')

    expect(createObjectURL).toHaveBeenCalledOnce()
    expect(click).toHaveBeenCalledOnce()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test')
    expect(document.querySelectorAll('a')).toHaveLength(0)
  })
})
