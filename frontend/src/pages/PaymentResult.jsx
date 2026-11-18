import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleCheck, faCircleNotch, faCircleXmark } from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { won } from '../lib/format'

/** 토스페이먼츠 결제창 리다이렉트 결과: 성공이면 서버 승인(금액 대조) 후 결과 표시 */
export default function PaymentResult({ ok }) {
  const [params] = useSearchParams()
  const [state, setState] = useState(ok ? 'confirming' : 'fail')
  const [order, setOrder] = useState(null)
  const [msg, setMsg] = useState(params.get('message') || '')
  const once = useRef(false)

  useEffect(() => {
    if (!ok || once.current) return
    once.current = true
    api('/api/shop/payments/toss/confirm', { method: 'POST', body: {
      paymentKey: params.get('paymentKey'), orderId: params.get('orderId'), amount: Number(params.get('amount')) } })
      .then((o) => { setOrder(o); setState('done') })
      .catch((e) => { setMsg(e.message); setState('fail') })
  }, [ok, params])

  return (
    <div className="container-x grid place-items-center py-20 text-center md:py-28">
      <div className="w-full max-w-md">
        {state === 'confirming' && <><FontAwesomeIcon icon={faCircleNotch} spin className="text-4xl" /><p className="mt-5 font-semibold">결제를 승인하고 있습니다…</p></>}
        {state === 'done' && (
          <>
            <FontAwesomeIcon icon={faCircleCheck} className="text-5xl text-success" />
            <h1 className="mt-5 text-[26px] font-bold">결제가 완료되었습니다</h1>
            <p className="mt-2 text-[14px] text-muted">주문번호 <b className="text-fg">{order.order_no}</b> · {won(order.total_amount)}</p>
            <p className="mt-1 text-[13px] text-muted">공급처별 발주서가 자동으로 작성되었습니다.</p>
          </>
        )}
        {state === 'fail' && (
          <>
            <FontAwesomeIcon icon={faCircleXmark} className="text-5xl text-danger" />
            <h1 className="mt-5 text-[26px] font-bold">결제가 완료되지 않았습니다</h1>
            <p className="mt-2 text-[14px] text-muted">{msg || '결제가 취소되었거나 승인에 실패했습니다.'}</p>
          </>
        )}
        <p className="mt-6 rounded-xl bg-surface-2 px-4 py-3 text-[12px] text-muted">토스페이먼츠 테스트 결제(모의 결제)로 실제 출금은 일어나지 않습니다.</p>
        <div className="mt-6 grid grid-cols-2 gap-2">
          <Link to="/shop" className="btn-ghost">쇼핑 계속하기</Link>
          <Link to="/mypage" className="btn-primary">주문 내역 보기</Link>
        </div>
      </div>
    </div>
  )
}
