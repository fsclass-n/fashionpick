export const won = (n) => `${Number(n || 0).toLocaleString('ko-KR')}원`
export const pct = (n, digits = 1) => `${(Number(n || 0) * 100).toFixed(digits)}%`
export const dateTime = (s) =>
  s ? new Date(s).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'
export const timeAgo = (s) => {
  if (!s) return '-'
  const diff = (Date.now() - new Date(s).getTime()) / 1000
  if (diff < 60) return '방금 전'
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`
  return `${Math.floor(diff / 86400)}일 전`
}

export const ORDER_STATUS = {
  received: { label: '주문 접수', tone: 'muted' },
  ordering: { label: '발주 진행', tone: 'warn' },
  ordered: { label: '발주 완료', tone: 'accent' },
  stocked: { label: '입고 완료', tone: 'success' },
}
export const PO_STATUS = {
  pending: { label: '대기', tone: 'warn' },
  sent: { label: '발송 완료', tone: 'accent' },
  received: { label: '입고 확인', tone: 'success' },
}
export const CATEGORIES = ['아우터', '상의', '하의', '원피스', '슈즈', '가방', '액세서리']
