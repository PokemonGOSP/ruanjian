export const REVIEW_STATUS_LABELS = {
  DRAFT: '草稿',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  WITHDRAWN: '已撤回',
}

export const MEMBERSHIP_STATUS_LABELS = {
  PENDING: '待处理',
  APPROVED: '已同意',
  REJECTED: '已驳回',
  WITHDRAWN: '已撤回',
}

export const MEMBERSHIP_TYPE_LABELS = {
  JOIN: '入团',
  EXIT: '退出',
}

export const MEMBER_STATUS_LABELS = {
  ACTIVE: '有效',
  EXITED: '已退出',
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}
