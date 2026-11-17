import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleNotch, faXmark } from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { CATEGORIES } from '../lib/format'
import { Empty, ErrorBox } from '../components/ui'
import ProductCard, { ProductGridSkeleton } from '../components/ProductCard'

const SORTS = [['new', '신상품순'], ['trend', '트렌드순'], ['price_asc', '낮은 가격순'], ['price_desc', '높은 가격순']]
const PAGE = 24

export default function Shop() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') || ''
  const q = params.get('q') || ''
  const keyword = params.get('keyword') || ''
  const sort = params.get('sort') || 'new'
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const filterKey = `${category}|${q}|${keyword}|${sort}`

  const update = (patch) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next)
  }

  useEffect(() => setPage(1), [filterKey])
  useEffect(() => {
    let alive = true
    setLoading(true)
    const qs = new URLSearchParams({ page, size: PAGE, sort })
    if (category) qs.set('category', category)
    if (q) qs.set('q', q)
    if (keyword) qs.set('keyword', keyword)
    api(`/api/shop/products?${qs}`)
      .then((r) => { if (!alive) return; setTotal(r.total); setItems((prev) => (page === 1 ? r.items : [...prev, ...r.items])); setError(null) })
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [filterKey, page]) // eslint-disable-line react-hooks/exhaustive-deps

  const title = q ? `‘${q}’ 검색 결과` : keyword ? `#${keyword}` : category || (sort === 'trend' ? 'BEST' : sort === 'new' && params.get('sort') ? 'NEW' : '전체 상품')

  return (
    <div className="container-x pt-8 pb-4 md:pt-12">
      <nav className="mb-4 text-[12px] text-muted" aria-label="breadcrumb">
        <Link to="/" className="hover:text-fg">홈</Link> <span className="mx-1.5">/</span> <Link to="/shop" className="hover:text-fg">SHOP</Link>
        {category && <><span className="mx-1.5">/</span><span className="text-fg">{category}</span></>}
      </nav>
      <h1 className="text-[28px] font-bold tracking-tight md:text-[36px]">{title}</h1>

      <div className="mt-6 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
        <button onClick={() => update({ category: '' })} className={`chip shrink-0 px-4 py-2 text-[13px] ${!category ? 'border-fg bg-fg text-bg' : 'hover:border-fg'}`}>전체</button>
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => update({ category: c })} className={`chip shrink-0 px-4 py-2 text-[13px] ${category === c ? 'border-fg bg-fg text-bg' : 'hover:border-fg'}`}>{c}</button>
        ))}
      </div>

      <div className="mt-6 mb-6 flex flex-wrap items-center justify-between gap-3 border-y border-line py-3">
        <div className="flex flex-wrap items-center gap-2 text-[13px]">
          <span className="text-muted">총 <b className="text-fg">{total.toLocaleString()}</b>개</span>
          {q && <button onClick={() => update({ q: '' })} className="chip">“{q}” <FontAwesomeIcon icon={faXmark} /></button>}
          {keyword && <button onClick={() => update({ keyword: '' })} className="chip">#{keyword} <FontAwesomeIcon icon={faXmark} /></button>}
        </div>
        <div className="flex items-center gap-1 text-[13px]" role="radiogroup" aria-label="정렬">
          {SORTS.map(([v, l], i) => (
            <span key={v} className="flex items-center">
              {i > 0 && <span className="mx-2 h-2.5 w-px bg-line" />}
              <button role="radio" aria-checked={sort === v} onClick={() => update({ sort: v })} className={sort === v ? 'font-bold' : 'text-muted hover:text-fg'}>{l}</button>
            </span>
          ))}
        </div>
      </div>

      <ErrorBox error={error} />
      {loading && page === 1 ? <ProductGridSkeleton count={12} /> : items.length === 0 ? (
        <Empty title="조건에 맞는 상품이 없습니다" desc="다른 키워드로 검색하거나 카테고리를 변경해 보세요." action={<Link to="/shop" className="btn-ghost">전체 상품 보기</Link>} />
      ) : (
        <div className="product-grid">{items.map((p) => <ProductCard key={p.id} p={p} />)}</div>
      )}
      {items.length < total && (
        <div className="mt-14 text-center">
          <button className="btn-ghost min-w-56 py-3" disabled={loading} onClick={() => setPage((p) => p + 1)}>
            {loading && <FontAwesomeIcon icon={faCircleNotch} spin />}더보기 <span className="text-muted">{items.length} / {total}</span>
          </button>
        </div>
      )}
    </div>
  )
}
