import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faBagShopping, faCircleInfo, faFileInvoice, faFire, faPaperPlane, faRobot, faTriangleExclamation, faUser, faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { useRealtime } from '../context/RealtimeContext'
import { won } from '../lib/format'

export const EVENT_ICONS = {
  bag: faBagShopping, file: faFileInvoice, send: faPaperPlane, warn: faTriangleExclamation, fire: faFire,
  robot: faRobot, user: faUser, info: faCircleInfo,
}
const TONE_BAR = { accent: 'bg-accent', success: 'bg-success', danger: 'bg-danger', warn: 'bg-warn', info: 'bg-fg' }

export default function Toasts() {
  const { toasts, dismiss } = useRealtime()
  const navigate = useNavigate()
  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-20 z-[80] flex flex-col items-stretch gap-2 md:inset-x-auto md:top-24 md:right-6 md:bottom-auto md:w-96" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className="animate-toast-in pointer-events-auto relative flex overflow-hidden rounded-2xl border border-line bg-surface shadow-xl">
          <span className={`w-1 shrink-0 ${TONE_BAR[t.tone] || TONE_BAR.info}`} />
          <button className="flex flex-1 items-start gap-3 px-4 py-3 text-left" onClick={() => { if (t.link) navigate(t.link); dismiss(t.id) }}>
            <FontAwesomeIcon icon={EVENT_ICONS[t.icon] || faCircleInfo} className="mt-1 text-sm" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{t.title}</span>
              {t.body && <span className="block truncate text-xs text-muted">{t.body}</span>}
            </span>
          </button>
          <button onClick={() => dismiss(t.id)} className="px-3 text-muted hover:text-fg" aria-label="닫기">
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>
      ))}
    </div>
  )
}

/** 신규 주문 발생 시 화면 중앙 팝업 */
export function OrderPopup() {
  const { popup, closePopup } = useRealtime()
  const navigate = useNavigate()
  if (!popup) return null
  const d = popup.data
  return (
    <div className="animate-fade-in fixed inset-0 z-[75] grid place-items-center bg-black/40 p-5 backdrop-blur-sm" onClick={closePopup}>
      <div className="animate-toast-in w-full max-w-sm overflow-hidden rounded-3xl bg-surface text-center shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="bg-fg px-6 py-8 text-bg">
          <span className="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-accent text-xl text-white">
            <FontAwesomeIcon icon={faBagShopping} />
          </span>
          <p className="eyebrow text-bg/60">New Order</p>
          <p className="mt-2 font-display text-3xl">{won(d.total_amount)}</p>
        </div>
        <div className="space-y-1 px-6 py-6 text-sm">
          <p className="font-semibold">{d.order_no}</p>
          <p className="text-muted">{d.customer_name} 님 · 상품 {d.items}건</p>
          <p className="pt-2 text-xs text-muted">공급처별 발주서가 자동으로 작성되었습니다.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 px-6 pb-6">
          <button className="btn-ghost" onClick={closePopup}>닫기</button>
          <button className="btn-primary" onClick={() => { closePopup(); navigate('/orders?tab=po') }}>발주서 보기</button>
        </div>
      </div>
    </div>
  )
}
