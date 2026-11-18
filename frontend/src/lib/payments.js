// 토스페이먼츠 결제위젯(주문서형) SDK v2 — 테스트 키라 실제 출금 없음
let sdkPromise
const loadSdk = () =>
  (sdkPromise ||= new Promise((resolve, reject) => {
    if (window.TossPayments) return resolve(window.TossPayments)
    const s = Object.assign(document.createElement('script'), { src: 'https://js.tosspayments.com/v2/standard', async: true })
    s.onload = () => resolve(window.TossPayments)
    s.onerror = () => reject(new Error('토스페이먼츠 결제 모듈을 불러오지 못했습니다.'))
    document.head.appendChild(s)
  }))

export const PAYMENT_METHODS = [
  { value: 'card', label: '신용카드', desc: '토스페이먼츠 · 테스트 승인' },
  { value: 'easypay', label: '간편결제', desc: '토스페이 · 네이버페이 등' },
  { value: 'bank', label: '무통장입금', desc: '입금 후 관리자 확인' },
]
export const PAY_LABEL = { card: '신용카드', easypay: '간편결제', bank: '무통장입금', '': '-' }
export const PAY_STATUS = { pending: ['warn', '결제 대기'], paid: ['success', '결제 완료'], failed: ['danger', '결제 실패'] }

/** 결제수단·약관 UI 를 주문 모달 안에 그린다 */
export async function renderTossWidget(p, methodsSelector, agreementSelector) {
  const TossPayments = await loadSdk()
  const widgets = TossPayments(p.client_key).widgets({ customerKey: p.customer_key })
  await widgets.setAmount({ currency: 'KRW', value: p.amount })
  await Promise.all([
    widgets.renderPaymentMethods({ selector: methodsSelector, variantKey: 'DEFAULT' }),
    widgets.renderAgreement({ selector: agreementSelector, variantKey: 'AGREEMENT' }),
  ])
  return widgets
}

/** 결제 요청 → 성공 시 /payment/success?paymentKey&orderId&amount 로 이동해 서버가 승인(금액 대조) */
export function requestTossPayment(widgets, p) {
  const origin = window.location.origin
  return widgets.requestPayment({
    orderId: p.order_id,
    orderName: p.order_name,
    customerName: p.customer_name,
    successUrl: `${origin}/payment/success`,
    failUrl: `${origin}/payment/fail`,
  })
}
