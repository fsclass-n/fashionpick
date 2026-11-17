import { Fragment, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faBolt, faBoxesStacked, faCheck, faChevronDown, faCircleNotch, faEye, faFileExcel, faFilePdf, faFileInvoice,
  faPaperPlane, faRotate, faTruckFast,
} from '@fortawesome/free-solid-svg-icons'
import { api, download } from '../lib/api'
import { ORDER_STATUS, PO_STATUS, dateTime, won } from '../lib/format'
import { useRealtime, useRealtimeEvent } from '../context/RealtimeContext'
import { Badge, Empty, ErrorBox, Modal, PageHeader, Spinner, Tabs, useAsync } from '../components/ui'

const STEPS = ['pending', 'sent', 'received']
const METHOD = { email: '이메일', webhook: '웹훅', manual: '수동(전화·팩스)' }

function Stepper({ status }) {
  const idx = STEPS.indexOf(status)
  return (
    <ol className="flex items-center gap-2 text-[11px]">
      {STEPS.map((s, i) => (
        <li key={s} className="flex items-center gap-2">
          <span className={`grid size-6 place-items-center rounded-full border text-[10px] ${i <= idx ? 'border-fg bg-fg text-bg' : 'border-line text-muted'}`}>
            {i < idx ? <FontAwesomeIcon icon={faCheck} /> : i + 1}
          </span>
          <span className={i <= idx ? 'font-medium' : 'text-muted'}>{PO_STATUS[s].label}</span>
          {i < STEPS.length - 1 && <span className={`h-px w-4 md:w-8 ${i < idx ? 'bg-fg' : 'bg-line'}`} />}
        </li>
      ))}
    </ol>
  )
}

function PreviewModal({ po, onClose }) {
  const { data, loading, error } = useAsync(() => (po ? api(`/api/purchase-orders/${po.id}/preview`) : Promise.resolve(null)), [po?.id])
  if (!po) return null
  return (
    <Modal open onClose={onClose} title="발주서 미리보기" wide>
      <ErrorBox error={error} />
      {loading || !data ? <Spinner /> : (
        <div className="rounded-2xl border border-line p-5 md:p-8">
          <p className="text-center font-display text-3xl tracking-[0.5em]">발 주 서</p>
          <p className="mb-6 text-center text-[11px] tracking-[0.3em] text-muted">PURCHASE ORDER</p>
          <dl className="grid gap-x-6 gap-y-2 text-sm md:grid-cols-2">
            {[['발주번호', data.po_no], ['발주일시', data.created_at], ['수신(공급처)', data.supplier.name], ['발신(발주처)', data.store.name],
              ['공급처 담당', `${data.supplier.contact_name} ${data.supplier.phone}`], ['발주처 담당', `${data.store.manager} ${data.store.phone}`]].map(([k, v]) => (
              <div key={k} className="flex gap-3 border-b border-line py-1.5"><dt className="w-24 shrink-0 text-muted">{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>
          <div className="table-wrap mt-6">
            <table>
              <thead><tr><th>No</th>{data.template !== 'simple' && <th>주문번호</th>}<th>상품명</th><th>옵션</th><th className="text-right">수량</th><th className="text-right">도매단가</th><th className="text-right">금액</th></tr></thead>
              <tbody>
                {data.items.map((i, n) => (
                  <tr key={n}>
                    <td>{n + 1}</td>{data.template !== 'simple' && <td className="text-muted">{i.order_no}</td>}
                    <td className="max-w-64 truncate">{i.product_name}</td><td>{i.option}</td>
                    <td className="text-right">{i.quantity}</td><td className="text-right">{won(i.wholesale_price)}</td><td className="text-right">{won(i.wholesale_price * i.quantity)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-right font-display text-2xl">합계 {won(data.total_amount)}</p>
        </div>
      )}
    </Modal>
  )
}

function PurchaseOrders() {
  const { toast } = useRealtime()
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useAsync(() => api(`/api/purchase-orders${status ? `?status=${status}` : ''}`), [status])
  const [busy, setBusy] = useState('')
  const [preview, setPreview] = useState(null)
  useRealtimeEvent(['po.created', 'po.updated', 'po.failed'], reload)

  const act = async (key, fn, okMsg) => {
    setBusy(key)
    try {
      await fn()
      if (okMsg) toast({ tone: 'success', icon: 'file', title: okMsg })
      reload()
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '처리 실패', body: e.message })
    } finally {
      setBusy('')
    }
  }
  const setPoStatus = (po, s) => act(`${po.id}-${s}`, () => api(`/api/purchase-orders/${po.id}/status`, { method: 'PATCH', body: { status: s } }))

  return (
    <>
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Tabs value={status} onChange={setStatus} tabs={[{ value: '', label: '전체' }, ...STEPS.map((s) => ({ value: s, label: PO_STATUS[s].label }))]} />
        <button className="btn-ghost self-start md:self-auto" disabled={busy === 'gen'}
          onClick={() => act('gen', () => api('/api/purchase-orders/generate', { method: 'POST' }), '미배정 주문을 발주서로 생성했습니다')}>
          <FontAwesomeIcon icon={busy === 'gen' ? faCircleNotch : faFileInvoice} spin={busy === 'gen'} /> 미배정 주문 발주서 생성
        </button>
      </div>
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : !data?.length ? <Empty title="발주서가 없습니다" icon={faFileInvoice} /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.map((po) => (
            <article key={po.id} className="card flex flex-col gap-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="eyebrow">{po.po_no}</p>
                  <h3 className="mt-1 text-2xl">{po.supplier_name}</h3>
                  <p className="text-xs text-muted">수신 방식 {METHOD[po.supplier_method]} · {dateTime(po.created_at)}</p>
                </div>
                <div className="text-right">
                  <Badge tone={PO_STATUS[po.status].tone}>{PO_STATUS[po.status].label}</Badge>
                  <p className="mt-2 font-display text-2xl">{won(po.total_amount)}</p>
                </div>
              </div>
              <Stepper status={po.status} />
              <ul className="space-y-1 text-sm">
                {po.items.slice(0, 3).map((i) => (
                  <li key={i.id} className="flex justify-between gap-3"><span className="truncate">{i.product_name} <span className="text-muted">{i.option}</span></span><span className="shrink-0 text-muted">×{i.quantity}</span></li>
                ))}
                {po.items.length > 3 && <li className="text-xs text-muted">외 {po.items.length - 3}건</li>}
              </ul>
              {po.send_log && <pre className="max-h-24 overflow-y-auto rounded-xl bg-surface-2 p-3 font-sans text-[11px] whitespace-pre-wrap text-muted">{po.send_log}</pre>}
              <div className="mt-auto flex flex-wrap gap-2 border-t border-line pt-4">
                <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setPreview(po)}><FontAwesomeIcon icon={faEye} />미리보기</button>
                <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => act(`${po.id}-x`, () => download(`/api/purchase-orders/${po.id}/excel`, `${po.po_no}.xlsx`))}>
                  <FontAwesomeIcon icon={faFileExcel} />Excel</button>
                <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => act(`${po.id}-p`, () => download(`/api/purchase-orders/${po.id}/pdf`, `${po.po_no}.pdf`))}>
                  <FontAwesomeIcon icon={faFilePdf} />PDF</button>
                <span className="flex-1" />
                {po.status === 'pending' && po.supplier_method !== 'manual' && (
                  <button className="btn-accent px-3 py-1.5 text-xs" disabled={!!busy}
                    onClick={() => act(`${po.id}-send`, () => api(`/api/purchase-orders/${po.id}/send`, { method: 'POST' }), '발주서를 발송했습니다')}>
                    <FontAwesomeIcon icon={busy === `${po.id}-send` ? faCircleNotch : faPaperPlane} spin={busy === `${po.id}-send`} />공급처로 발송</button>
                )}
                {po.status === 'pending' && po.supplier_method === 'manual' && (
                  <button className="btn-primary px-3 py-1.5 text-xs" disabled={!!busy} onClick={() => setPoStatus(po, 'sent')}><FontAwesomeIcon icon={faCheck} />수동 발주 완료</button>
                )}
                {po.status === 'sent' && (
                  <button className="btn-primary px-3 py-1.5 text-xs" disabled={!!busy} onClick={() => setPoStatus(po, 'received')}><FontAwesomeIcon icon={faBoxesStacked} />입고 확인</button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      <PreviewModal po={preview} onClose={() => setPreview(null)} />
    </>
  )
}

function OrderList() {
  const [status, setStatus] = useState('')
  const [open, setOpen] = useState(null)
  const { data, loading, error, reload } = useAsync(() => api(`/api/orders${status ? `?status=${status}` : ''}`), [status])
  useRealtimeEvent(['order.created', 'po.updated', 'po.created'], reload)

  return (
    <>
      <Tabs value={status} onChange={setStatus} tabs={[{ value: '', label: '전체' }, ...Object.entries(ORDER_STATUS).map(([v, s]) => ({ value: v, label: s.label }))]} />
      <ErrorBox error={error} />
      {loading && !data ? <Spinner /> : !data?.length ? <Empty title="주문이 없습니다" desc="'테스트 주문 발생'으로 주문 → 발주 자동화 흐름을 확인해 보세요." /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>주문번호</th><th>고객</th><th>채널</th><th className="text-right">금액</th><th>상태</th><th>주문일시</th><th></th></tr></thead>
            <tbody>
              {data.map((o) => (
                <Fragment key={o.id}>
                  <tr className="cursor-pointer hover:bg-surface-2" onClick={() => setOpen(open === o.id ? null : o.id)}>
                    <td className="font-medium">{o.order_no}</td>
                    <td>{o.customer_name}</td>
                    <td className="text-muted">{o.channel}</td>
                    <td className="text-right">{won(o.total_amount)}</td>
                    <td><Badge tone={ORDER_STATUS[o.status]?.tone}>{ORDER_STATUS[o.status]?.label}</Badge></td>
                    <td className="text-muted">{dateTime(o.created_at)}</td>
                    <td><FontAwesomeIcon icon={faChevronDown} className={`text-muted transition ${open === o.id ? 'rotate-180' : ''}`} /></td>
                  </tr>
                  {open === o.id && (
                    <tr className="bg-surface-2/60">
                      <td colSpan={7} className="whitespace-normal">
                        <ul className="space-y-1.5 py-1 text-sm">
                          {o.items.map((i) => (
                            <li key={i.id} className="flex flex-wrap items-center justify-between gap-2">
                              <span>{i.product_name} <span className="text-muted">· {i.option || '옵션 없음'} · {i.quantity}개</span></span>
                              <span className="flex items-center gap-3 text-xs text-muted">
                                판매 {won(i.unit_price)} / 도매 {won(i.wholesale_price)}
                                <Badge tone={i.purchase_order_id ? 'accent' : 'muted'}>{i.purchase_order_id ? `발주서 #${i.purchase_order_id}` : '발주 미배정'}</Badge>
                              </span>
                            </li>
                          ))}
                        </ul>
                        <p className="mt-2 text-xs text-muted">{o.address} · {o.customer_phone}</p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

export default function Orders() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'orders'
  const { toast } = useRealtime()
  const [busy, setBusy] = useState(false)

  const simulate = async () => {
    setBusy(true)
    try {
      await api('/api/orders/simulate', { method: 'POST' })
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '주문 생성 실패', body: e.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader eyebrow="Orders & Purchase Orders" title={<>Order <span className="italic">automation</span></>}
        desc="주문이 들어오면 공급처별로 자동 분류해 발주서를 작성합니다. 미리보기·다운로드 후 이메일/웹훅으로 발송하고 입고까지 추적하세요."
        actions={<>
          <button className="btn-accent" onClick={simulate} disabled={busy}><FontAwesomeIcon icon={busy ? faCircleNotch : faBolt} spin={busy} /> 테스트 주문 발생</button>
        </>} />
      <Tabs value={tab} onChange={(v) => setParams({ tab: v })}
        tabs={[{ value: 'orders', label: '주문 관리', icon: faTruckFast }, { value: 'po', label: '발주서', icon: faFileInvoice }]} />
      {tab === 'po' ? <PurchaseOrders /> : <OrderList />}
      <p className="mt-6 text-xs text-muted"><FontAwesomeIcon icon={faRotate} className="mr-1" />실시간 알림 수신 시 목록이 자동으로 갱신됩니다.</p>
    </>
  )
}
