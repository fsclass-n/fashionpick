import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCheck, faCircleNotch, faMagnifyingGlass, faRobot, faRotateLeft, faStore, faTag, faWandMagicSparkles, faXmark,
} from '@fortawesome/free-solid-svg-icons'
import { api, mediaUrl } from '../../lib/api'
import { CATEGORIES, pct, won } from '../../lib/format'
import { useRealtime, useRealtimeEvent } from '../../context/RealtimeContext'
import { Badge, Empty, ErrorBox, Modal, PageHeader, Spinner, Tabs, WriteButton } from '../../components/ui'

const SWATCH = { 블랙: '#1f1f1f', 아이보리: '#efe8da', 그레이: '#9a9a9a', 네이비: '#23304a', 베이지: '#d8c3a5', 브라운: '#6b4a35', 카키: '#6b6b47', 버건디: '#6d2233', 스카이블루: '#9cc3e0' }
const PAGE = 30

function ProductCard({ p, onRegister, onUnregister }) {
  const [loaded, setLoaded] = useState(false)
  return (
    <article className="group mb-3 break-inside-avoid overflow-hidden rounded-2xl border border-line bg-surface md:mb-4">
      <div className="relative overflow-hidden bg-surface-2" style={{ aspectRatio: `1 / ${p.image_ratio || 1.25}` }}>
        {p.image_url && (
          <img src={mediaUrl(p.image_url)} alt={p.name} loading="lazy" onLoad={() => setLoaded(true)}
            className={`size-full object-cover transition duration-700 group-hover:scale-[1.04] ${loaded ? 'opacity-100' : 'opacity-0'}`} />
        )}
        <div className="absolute top-2 left-2 flex flex-wrap gap-1">
          <span className="rounded-full bg-black/60 px-2 py-0.5 text-[10px] text-white backdrop-blur">#{p.keyword}</span>
        </div>
        {p.status === 'registered' && (
          <span className="absolute top-2 right-2 grid size-7 place-items-center rounded-full bg-success text-xs text-white" title="판매 등록됨"><FontAwesomeIcon icon={faCheck} /></span>
        )}
      </div>
      <div className="space-y-2.5 p-3 md:p-4">
        <p className="text-[11px] text-muted"><FontAwesomeIcon icon={faStore} className="mr-1" />{p.supplier_name} · {p.category}</p>
        <h3 className="line-clamp-2 font-sans text-sm leading-snug font-medium">{p.registered_name || p.name}</h3>
        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs">
          <span className="text-muted">도매가</span><span className="text-right">{won(p.wholesale_price)}</span>
          <span className="text-muted">예상 판매가</span><span className="text-right font-semibold">{won(p.sale_price)}</span>
          <span className="text-muted">마진율</span><span className={`text-right font-semibold ${p.margin_rate >= 0.5 ? 'text-success' : 'text-warn'}`}>{pct(p.margin_rate)}</span>
        </div>
        {(p.options?.colors?.length > 0 || p.options?.sizes?.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5 border-t border-line pt-2.5">
            {p.options.colors?.map((c) => (
              <span key={c} title={c} className="size-3.5 rounded-full border border-line" style={{ background: SWATCH[c] || '#ccc' }} />
            ))}
            <span className="ml-auto text-[10px] text-muted">{p.options.sizes?.join(' · ')}</span>
          </div>
        )}
        <div className="flex items-center justify-between pt-1">
          <span className={`text-[11px] ${p.stock > 0 ? 'text-muted' : 'text-danger'}`}>재고 {p.stock > 0 ? `${p.stock}개` : '확인 필요'}</span>
          {p.status === 'registered' ? (
            <WriteButton className="text-[11px] text-muted underline-offset-4 hover:underline disabled:no-underline disabled:opacity-60" onClick={() => onUnregister(p)}>
              <FontAwesomeIcon icon={faRotateLeft} className="mr-1" />등록 해제
            </WriteButton>
          ) : (
            <WriteButton className="btn-primary px-3 py-1.5 text-xs" onClick={() => onRegister(p)}><FontAwesomeIcon icon={faTag} />원클릭 등록</WriteButton>
          )}
        </div>
      </div>
    </article>
  )
}

function RegisterModal({ product, onClose, onDone }) {
  const [name, setName] = useState('')
  const [price, setPrice] = useState(0)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!product) return
    setBusy(true)
    setError(null)
    api(`/api/products/${product.id}/suggest-name`)
      .then((s) => { setName(s.name); setPrice(s.sale_price) })
      .catch(setError)
      .finally(() => setBusy(false))
  }, [product])

  if (!product) return null
  const margin = price ? (price - product.wholesale_price) / price : 0
  const submit = async () => {
    setBusy(true)
    try {
      onDone(await api(`/api/products/${product.id}/register`, { method: 'POST', body: { registered_name: name, sale_price: Number(price) } }))
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }

  return (
    <Modal open onClose={onClose} title="원클릭 상품 등록">
      <div className="flex gap-4">
        <img src={mediaUrl(product.image_url)} alt="" className="h-32 w-24 shrink-0 rounded-xl object-cover" />
        <div className="text-sm">
          <p className="text-xs text-muted">{product.supplier_name}</p>
          <p className="font-medium">{product.name}</p>
          <p className="mt-2 text-xs text-muted">도매가 {won(product.wholesale_price)}</p>
        </div>
      </div>
      <div className="mt-6 space-y-4">
        <div>
          <label className="label"><FontAwesomeIcon icon={faWandMagicSparkles} className="mr-1" />트렌드 키워드 추천 상품명</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={255} />
        </div>
        <div>
          <label className="label">판매가</label>
          <input type="number" className="input" value={price} min={product.wholesale_price + 1} step={100} onChange={(e) => setPrice(e.target.value)} />
          <p className={`mt-1.5 text-xs ${margin >= 0.5 ? 'text-success' : 'text-warn'}`}>마진 {won(price - product.wholesale_price)} · 마진율 {pct(margin)}</p>
        </div>
        <ErrorBox error={error} />
        <div className="grid grid-cols-2 gap-2 pt-2">
          <button className="btn-ghost" onClick={onClose}>취소</button>
          <WriteButton className="btn-accent" onClick={submit} disabled={busy || !name}>{busy && <FontAwesomeIcon icon={faCircleNotch} spin />}판매 상품으로 등록</WriteButton>
        </div>
      </div>
    </Modal>
  )
}

export default function Sourcing() {
  const [params, setParams] = useSearchParams()
  const { toast } = useRealtime()
  const status = params.get('status') ?? 'sourced'
  const category = params.get('category') || ''
  const keyword = params.get('keyword') || ''
  const q = params.get('q') || ''
  const [search, setSearch] = useState(q)
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [target, setTarget] = useState(null)
  const [tick, setTick] = useState(0)

  const update = (patch) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    if ('status' in patch) next.set('status', patch.status)
    setParams(next)
  }

  useEffect(() => setSearch(q), [q])
  useEffect(() => { setPage(1) }, [status, category, keyword, q, tick])
  useEffect(() => {
    let alive = true
    setLoading(true)
    const qs = new URLSearchParams({ page, size: PAGE })
    if (status) qs.set('status', status)
    if (category) qs.set('category', category)
    if (keyword) qs.set('keyword', keyword)
    if (q) qs.set('q', q)
    api(`/api/products?${qs}`)
      .then((r) => { if (!alive) return; setTotal(r.total); setItems((prev) => (page === 1 ? r.items : [...prev, ...r.items])); setError(null) })
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [status, category, keyword, q, page, tick])

  useRealtimeEvent('rpa.job', (m) => m.data.job === 'product_sourcing' && m.data.status === 'success' && setTick((t) => t + 1))

  const runSourcing = async () => {
    try {
      await api('/api/admin/rpa/jobs/product_sourcing/run', { method: 'POST' })
      toast({ tone: 'info', icon: 'robot', title: '도매 상품 수집을 시작했습니다', body: '완료되면 실시간 알림으로 알려드립니다.' })
    } catch (e) {
      toast({ tone: 'danger', icon: 'warn', title: '실행 실패', body: e.message })
    }
  }
  const replace = (p) => setItems((list) => (status && p.status !== status ? list.filter((x) => x.id !== p.id) : list.map((x) => (x.id === p.id ? p : x))))
  const unregister = async (p) => replace(await api(`/api/products/${p.id}/unregister`, { method: 'POST' }))

  return (
    <>
      <PageHeader eyebrow="Wholesale Sourcing" title={<>Sourced <span className="italic">picks</span></>}
        desc="트렌드 키워드로 도매 사이트에서 수집한 상품입니다. 마진을 확인하고 원클릭으로 판매 상품에 등록하세요."
        actions={<WriteButton className="btn-accent" onClick={runSourcing}><FontAwesomeIcon icon={faRobot} /> 지금 수집 실행</WriteButton>} />

      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <Tabs value={status} onChange={(v) => update({ status: v })}
          tabs={[{ value: 'sourced', label: '소싱 대기' }, { value: 'registered', label: '판매 등록' }, { value: '', label: '전체' }]} />
        <form onSubmit={(e) => { e.preventDefault(); update({ q: search.trim() }) }} className="relative w-full lg:w-80">
          <FontAwesomeIcon icon={faMagnifyingGlass} className="absolute top-1/2 left-4 -translate-y-1/2 text-muted" />
          <input className="input rounded-full pl-11" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="상품명·키워드 검색" />
        </form>
      </div>
      <div className="mb-6 flex flex-wrap gap-2">
        <button onClick={() => update({ category: '' })} className={`chip px-3 py-1.5 text-sm ${!category ? 'border-fg bg-fg text-bg' : ''}`}>전체</button>
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => update({ category: c })} className={`chip px-3 py-1.5 text-sm ${category === c ? 'border-fg bg-fg text-bg' : 'hover:bg-surface-2'}`}>{c}</button>
        ))}
        {keyword && <Badge tone="accent" className="py-1.5">#{keyword}<button onClick={() => update({ keyword: '' })} aria-label="키워드 필터 해제"><FontAwesomeIcon icon={faXmark} className="ml-1" /></button></Badge>}
        {q && <Badge tone="info" className="py-1.5">“{q}”<button onClick={() => update({ q: '' })} aria-label="검색 해제"><FontAwesomeIcon icon={faXmark} className="ml-1" /></button></Badge>}
      </div>

      <ErrorBox error={error} />
      <p className="mb-4 text-sm text-muted">총 {total.toLocaleString()}개 상품</p>
      {loading && page === 1 ? <Spinner /> : items.length === 0 ? (
        <Empty title="조건에 맞는 상품이 없습니다" desc="필터를 변경하거나 RPA 도매 수집을 실행해 보세요." />
      ) : (
        <div className="columns-2 gap-3 md:columns-3 md:gap-4 lg:columns-4 2xl:columns-5">
          {items.map((p) => <ProductCard key={p.id} p={p} onRegister={setTarget} onUnregister={unregister} />)}
        </div>
      )}
      {items.length < total && (
        <div className="mt-8 text-center">
          <button className="btn-ghost px-8" disabled={loading} onClick={() => setPage((p) => p + 1)}>
            {loading && <FontAwesomeIcon icon={faCircleNotch} spin />}더 보기 ({items.length}/{total})
          </button>
        </div>
      )}
      <RegisterModal product={target} onClose={() => setTarget(null)}
        onDone={(p) => { replace(p); setTarget(null); toast({ tone: 'success', icon: 'bag', title: '판매 상품으로 등록되었습니다', body: p.registered_name }) }} />
    </>
  )
}
