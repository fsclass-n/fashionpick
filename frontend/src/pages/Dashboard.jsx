import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight, faBagShopping, faBolt, faFileInvoice, faFire, faShirt, faWonSign,
} from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { ORDER_STATUS, dateTime, pct, won } from '../lib/format'
import { useRealtime, useRealtimeEvent } from '../context/RealtimeContext'
import { useAuth } from '../context/AuthContext'
import { Badge, Empty, ErrorBox, PageHeader, Spinner, StatCard, useAsync } from '../components/ui'
import { EVENT_ICONS } from '../components/Toasts'

const FLOW = [
  { step: '01', title: 'Trend', desc: '네이버 데이터랩·랭킹 페이지에서 키워드 수집', to: '/trends' },
  { step: '02', title: 'Sourcing', desc: '키워드로 도매 상품·이미지 자동 수집', to: '/sourcing' },
  { step: '03', title: 'Order', desc: '주문 발생 시 공급처별 발주서 자동 작성·발송', to: '/orders' },
]

export default function Dashboard() {
  const { user } = useAuth()
  const { feed } = useRealtime()
  const { data, error, loading, reload } = useAsync(() => api('/api/dashboard/summary'))
  useRealtimeEvent(['order.created', 'po.created', 'po.updated', 'rpa.job'], reload)

  const simulate = async () => {
    await api('/api/orders/simulate', { method: 'POST' }).catch(() => {})
  }

  return (
    <>
      <PageHeader
        eyebrow={`Hello, ${user?.name}`}
        title={<>Today’s <span className="italic">edit</span></>}
        desc="오늘의 트렌드와 소싱·주문·발주 현황을 한눈에 확인하세요."
        actions={<button className="btn-accent" onClick={simulate}><FontAwesomeIcon icon={faBolt} /> 테스트 주문 발생</button>}
      />
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
            <StatCard label="오늘 주문" value={data.orders_today} sub={won(data.revenue_today)} icon={faBagShopping} tone="accent" />
            <StatCard label="발주 대기" value={data.po_pending} sub={`발송 완료 ${data.po_sent}건`} icon={faFileInvoice} />
            <StatCard label="판매 등록 상품" value={data.products_registered} sub={`소싱 대기 ${data.products_sourced}건`} icon={faShirt} />
            <StatCard label="급상승 키워드" value={data.surge_count} sub="직전 수집 대비" icon={faFire} />
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <section className="card p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-2xl">Trend Top 5</h2>
                <Link to="/trends" className="text-sm text-muted hover:text-fg">전체 보기 <FontAwesomeIcon icon={faArrowRight} /></Link>
              </div>
              <ol className="divide-y divide-line">
                {data.top_keywords.map((k) => (
                  <li key={k.keyword} className="flex items-center gap-4 py-3">
                    <span className="w-8 font-display text-2xl italic text-muted">{k.rank}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{k.keyword}</p>
                      <p className="text-xs text-muted">{k.category} · 점수 {k.score.toFixed(1)}</p>
                    </div>
                    {k.surge && <Badge tone="accent"><FontAwesomeIcon icon={faFire} />급상승</Badge>}
                    <span className={`w-14 text-right text-sm ${k.growth > 0 ? 'text-accent' : 'text-muted'}`}>{k.growth > 0 ? '+' : ''}{pct(k.growth)}</span>
                    <Link to={`/sourcing?keyword=${encodeURIComponent(k.keyword)}`} className="btn-ghost hidden px-3 py-1.5 text-xs sm:inline-flex">소싱</Link>
                  </li>
                ))}
              </ol>
            </section>

            <section className="card p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-2xl">Live feed</h2>
                <span className="text-xs text-muted">WebSocket</span>
              </div>
              {feed.length ? (
                <ul className="max-h-80 space-y-3 overflow-y-auto pr-1">
                  {feed.map((f) => (
                    <li key={f.id} className="flex gap-3 text-sm">
                      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-2"><FontAwesomeIcon icon={EVENT_ICONS[f.icon]} className="text-xs" /></span>
                      <span className="min-w-0">
                        <span className="block font-medium">{f.title}</span>
                        <span className="block truncate text-xs text-muted">{f.body}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty title="아직 실시간 이벤트가 없습니다" desc="'테스트 주문 발생'을 누르면 주문 → 발주서 생성 알림이 실시간으로 표시됩니다." />
              )}
            </section>
          </div>

          <section className="card p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-2xl">Recent orders</h2>
              <Link to="/orders" className="text-sm text-muted hover:text-fg">주문 관리 <FontAwesomeIcon icon={faArrowRight} /></Link>
            </div>
            <div className="table-wrap border-0">
              <table>
                <thead><tr><th>주문번호</th><th>고객</th><th>상품</th><th className="text-right">금액</th><th>상태</th><th>주문일시</th></tr></thead>
                <tbody>
                  {data.recent_orders.map((o) => (
                    <tr key={o.id}>
                      <td className="font-medium">{o.order_no}</td>
                      <td>{o.customer_name}</td>
                      <td className="max-w-56 truncate text-muted">{o.items[0]?.product_name}{o.items.length > 1 && ` 외 ${o.items.length - 1}건`}</td>
                      <td className="text-right">{won(o.total_amount)}</td>
                      <td><Badge tone={ORDER_STATUS[o.status]?.tone}>{ORDER_STATUS[o.status]?.label}</Badge></td>
                      <td className="text-muted">{dateTime(o.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="grid gap-3 md:grid-cols-3">
            {FLOW.map((f) => (
              <Link key={f.step} to={f.to} className="group card flex flex-col gap-6 p-6 transition hover:border-fg">
                <span className="eyebrow">{f.step} · RPA</span>
                <span className="font-display text-4xl italic">{f.title}</span>
                <span className="flex items-end justify-between text-sm text-muted">
                  {f.desc}<FontAwesomeIcon icon={faArrowRight} className="transition group-hover:translate-x-1" />
                </span>
              </Link>
            ))}
          </section>
          <p className="text-right text-xs text-muted"><FontAwesomeIcon icon={faWonSign} className="mr-1" />금액은 판매가 기준입니다.</p>
        </div>
      )}
    </>
  )
}
