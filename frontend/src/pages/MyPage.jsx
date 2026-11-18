import { Link, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBagShopping, faBell, faCheck, faGauge, faRightFromBracket, faUser } from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { ORDER_STATUS, dateTime, won } from '../lib/format'
import { ROLE_LABEL } from '../lib/site'
import { useAuth } from '../context/AuthContext'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { Badge, Empty, ErrorBox, Spinner, useAsync } from '../components/ui'
import NotificationSettings from '../components/NotificationSettings'
import { PAY_LABEL, PAY_STATUS } from '../lib/payments'

const STEPS = ['received', 'ordering', 'ordered', 'stocked']
const STEP_LABEL = { received: '주문 접수', ordering: '발주 진행', ordered: '발주 완료', stocked: '입고·출고 준비' }

function OrderSteps({ status }) {
  const idx = STEPS.indexOf(status)
  return (
    <ol className="grid grid-cols-4 gap-1 text-center text-[11px]">
      {STEPS.map((s, i) => (
        <li key={s}>
          <span className={`block h-[3px] ${i <= idx ? 'bg-fg' : 'bg-line'}`} />
          <span className={`mt-2 block ${i <= idx ? 'font-semibold' : 'text-muted'}`}>{i < idx && <FontAwesomeIcon icon={faCheck} className="mr-1" />}{STEP_LABEL[s]}</span>
        </li>
      ))}
    </ol>
  )
}

function MyOrders() {
  const { data, loading, error, reload } = useAsync(() => api('/api/me/orders'))
  useRealtimeEvent(['order.placed', 'order.status'], reload)
  if (loading && !data) return <Spinner />
  if (error) return <ErrorBox error={error} />
  if (!data.length) return <Empty icon={faBagShopping} title="주문 내역이 없습니다" desc="마음에 드는 상품을 찾아보세요." action={<Link to="/shop" className="btn-primary">쇼핑하러 가기</Link>} />
  return (
    <div className="space-y-4">
      {data.map((o) => (
        <article key={o.id} className="border border-line p-5 md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
            <div>
              <p className="text-[13px] font-semibold">{dateTime(o.created_at)} <span className="ml-2 font-normal text-muted">{o.order_no}</span></p>
            </div>
            <span className="flex gap-1.5">
              <Badge tone={(PAY_STATUS[o.payment_status] || [])[0]}>{PAY_LABEL[o.payment_method] || '결제'} · {(PAY_STATUS[o.payment_status] || [])[1]}</Badge>
              <Badge tone={ORDER_STATUS[o.status]?.tone}>{ORDER_STATUS[o.status]?.label}</Badge>
            </span>
          </div>
          {o.payment_method === 'bank' && o.payment_status === 'pending' && (
            <p className="mt-3 rounded-xl bg-warn/10 px-4 py-3 text-[12px] text-warn">입금 대기 중입니다 · 입금자명 {o.depositor_name} · {dateTime(o.deposit_due_at)}까지 입금 (모의)</p>
          )}
          <ul className="divide-y divide-line">
            {o.items.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-4 py-3 text-[13px]">
                <Link to={`/products/${i.product_id}`} className="min-w-0 hover:underline">
                  <span className="line-clamp-1">{i.product_name}</span>
                  <span className="text-muted">{i.option || '옵션 없음'} · {i.quantity}개</span>
                </Link>
                <span className="shrink-0 font-semibold">{won(i.unit_price * i.quantity)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4"><OrderSteps status={o.status} /></div>
          <p className="mt-4 text-right text-[14px]">결제 금액 <b className="ml-2 text-[17px]">{won(o.total_amount)}</b></p>
        </article>
      ))}
    </div>
  )
}

function Profile() {
  const { user, isAdmin, logout } = useAuth()
  const rows = [['이름', user.name], ['이메일', user.email], ['회원 등급', ROLE_LABEL[user.role]], ['가입 경로', user.provider],
    ['가입일', dateTime(user.created_at)], ['최근 로그인', dateTime(user.last_login_at)]]
  return (
    <div className="max-w-xl">
      <dl className="divide-y divide-line border-y border-line text-[14px]">
        {rows.map(([k, v]) => <div key={k} className="grid grid-cols-[110px_1fr] py-3.5"><dt className="text-muted">{k}</dt><dd>{v}</dd></div>)}
      </dl>
      <div className="mt-6 flex gap-2">
        {isAdmin && <Link to="/admin" className="btn-primary"><FontAwesomeIcon icon={faGauge} />관리자 콘솔</Link>}
        <button onClick={logout} className="btn-ghost"><FontAwesomeIcon icon={faRightFromBracket} />로그아웃</button>
      </div>
    </div>
  )
}

const TABS = [
  { value: 'orders', label: '주문 내역', icon: faBagShopping },
  { value: 'profile', label: '회원 정보', icon: faUser },
  { value: 'notify', label: '알림 설정', icon: faBell },
]

export default function MyPage() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'orders'
  return (
    <div className="container-x pt-8 md:pt-12">
      <div className="flex flex-col gap-2 border-b border-fg pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="eyebrow">My Page</p>
          <h1 className="mt-2 text-[28px] font-bold tracking-tight md:text-[36px]">{user.name}님, 안녕하세요</h1>
        </div>
        <Badge tone={user.role === 'user' ? 'muted' : 'accent'}>{ROLE_LABEL[user.role]}</Badge>
      </div>
      <div className="grid gap-8 pt-8 md:grid-cols-[200px_1fr] md:gap-12">
        <nav className="flex gap-1 overflow-x-auto md:flex-col" aria-label="마이페이지 메뉴">
          {TABS.map((t) => (
            <button key={t.value} onClick={() => setParams({ tab: t.value })}
              className={`flex shrink-0 items-center gap-3 px-3 py-2.5 text-left text-[14px] transition ${tab === t.value ? 'bg-fg font-semibold text-bg' : 'text-muted hover:text-fg'}`}>
              <FontAwesomeIcon icon={t.icon} className="w-4" />{t.label}
            </button>
          ))}
        </nav>
        <section>
          <h2 className="mb-5 text-[18px] font-bold">{TABS.find((t) => t.value === tab)?.label}</h2>
          {tab === 'orders' && <MyOrders />}
          {tab === 'profile' && <Profile />}
          {tab === 'notify' && <NotificationSettings />}
        </section>
      </div>
    </div>
  )
}
