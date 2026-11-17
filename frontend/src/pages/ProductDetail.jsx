import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCheck, faChevronDown, faCircleNotch, faFire, faHeart, faMinus, faPlus, faTruckFast,
} from '@fortawesome/free-solid-svg-icons'
import { faHeart as faHeartLine } from '@fortawesome/free-regular-svg-icons'
import { api, mediaUrl } from '../lib/api'
import { pct, won } from '../lib/format'
import { useAuth } from '../context/AuthContext'
import { ErrorBox, Modal, Spinner, WriteButton, useAsync } from '../components/ui'
import ProductCard from '../components/ProductCard'

const SWATCH = { 블랙: '#1f1f1f', 아이보리: '#efe8da', 그레이: '#9a9a9a', 네이비: '#23304a', 베이지: '#d8c3a5', 브라운: '#6b4a35', 카키: '#6b6b47', 버건디: '#6d2233', 스카이블루: '#9cc3e0' }
const WISH_KEY = 'fp_wishlist'

/** 데모 이미지(placeholder)는 color 파라미터만 바꿔 색상별 컷을 만든다 */
const colorImage = (url, color) => (url?.includes('/media/placeholder/') && color ? url.replace(/color=[^&]*/, `color=${encodeURIComponent(color)}`) : url)

function Accordion({ title, children, defaultOpen }) {
  const [open, setOpen] = useState(!!defaultOpen)
  return (
    <div className="border-b border-line">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between py-4 text-left text-[14px] font-semibold" aria-expanded={open}>
        {title}<FontAwesomeIcon icon={faChevronDown} className={`text-xs text-muted transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="pb-5 text-[13px] leading-6 text-muted">{children}</div>}
    </div>
  )
}

function useWish(id) {
  const [list, setList] = useState(() => JSON.parse(localStorage.getItem(WISH_KEY) || '[]'))
  const on = list.includes(id)
  const toggle = () => {
    const next = on ? list.filter((x) => x !== id) : [...list, id]
    localStorage.setItem(WISH_KEY, JSON.stringify(next))
    setList(next)
  }
  return [on, toggle]
}

function CheckoutModal({ open, onClose, product, option, quantity, onDone }) {
  const { user } = useAuth()
  const [form, setForm] = useState({ customer_name: '', customer_phone: '', address: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  useEffect(() => { if (open) setForm((f) => ({ ...f, customer_name: f.customer_name || user?.name || '' })) }, [open, user])
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      onDone(await api('/api/shop/orders', { method: 'POST', body: { ...form, items: [{ product_id: product.id, option, quantity }] } }))
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal open={open} onClose={onClose} title="주문하기">
      <div className="mb-5 flex gap-4 border-b border-line pb-5">
        <img src={mediaUrl(product.image_url)} alt="" className="h-24 w-20 object-cover" />
        <div className="text-[13px]">
          <p className="font-medium">{product.name}</p>
          <p className="mt-1 text-muted">{option || '옵션 없음'} · {quantity}개</p>
          <p className="mt-2 text-[15px] font-bold">{won(product.price * quantity)}</p>
        </div>
      </div>
      <form onSubmit={submit} className="space-y-4">
        <div><label className="label" htmlFor="co-name">받는 분</label><input id="co-name" className="input" value={form.customer_name} onChange={set('customer_name')} required maxLength={100} /></div>
        <div><label className="label" htmlFor="co-phone">연락처</label><input id="co-phone" className="input" value={form.customer_phone} onChange={set('customer_phone')} required minLength={9} maxLength={20} placeholder="010-0000-0000" inputMode="tel" /></div>
        <div><label className="label" htmlFor="co-addr">배송지</label><input id="co-addr" className="input" value={form.address} onChange={set('address')} required minLength={5} maxLength={255} placeholder="도로명 주소" /></div>
        <p className="rounded-xl bg-surface-2 px-4 py-3 text-[12px] text-muted">데모 서비스로 실제 결제는 진행되지 않습니다. 주문 즉시 공급처별 발주서가 자동 생성됩니다.</p>
        <ErrorBox error={error} />
        <WriteButton className="btn-primary w-full py-3.5 text-[15px]" disabled={busy}>
          {busy && <FontAwesomeIcon icon={faCircleNotch} spin />}{won(product.price * quantity)} 주문하기
        </WriteButton>
      </form>
    </Modal>
  )
}

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const { data: p, error, loading } = useAsync(() => api(`/api/shop/products/${id}`), [id])
  const [color, setColor] = useState('')
  const [size, setSize] = useState('')
  const [qty, setQty] = useState(1)
  const [warn, setWarn] = useState('')
  const [checkout, setCheckout] = useState(false)
  const [done, setDone] = useState(null)
  const [wish, toggleWish] = useWish(Number(id))

  useEffect(() => { setColor(''); setSize(''); setQty(1); setWarn('') }, [id])
  const colors = p?.options?.colors || []
  const sizes = p?.options?.sizes || []
  const gallery = useMemo(() => (p ? (colors.length ? colors.map((c) => colorImage(p.image_url, c)) : [p.image_url]) : []), [p]) // eslint-disable-line react-hooks/exhaustive-deps
  const mainImage = colorImage(p?.image_url, color || colors[0])

  if (loading && !p) return <Spinner />
  if (error) return <div className="container-x py-16"><ErrorBox error={error} /><Link to="/shop" className="btn-ghost mt-6">상품 목록으로</Link></div>

  const buy = () => {
    if (colors.length && !color) return setWarn('색상을 선택해 주세요.')
    if (sizes.length && !size) return setWarn('사이즈를 선택해 주세요.')
    if (!user) return navigate('/login', { state: { from: location } })
    setWarn('')
    setCheckout(true)
  }
  const option = [color, size].filter(Boolean).join('/')

  return (
    <div className="container-x pt-6 md:pt-10">
      <nav className="mb-5 text-[12px] text-muted" aria-label="breadcrumb">
        <Link to="/" className="hover:text-fg">홈</Link><span className="mx-1.5">/</span>
        <Link to={`/shop?category=${encodeURIComponent(p.category)}`} className="hover:text-fg">{p.category}</Link>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[1.25fr_1fr] lg:gap-14">
        <div className="grid gap-3 self-start md:grid-cols-[72px_1fr]">
          <div className="order-2 flex gap-2 overflow-x-auto md:order-1 md:flex-col">
            {gallery.map((src, i) => (
              <button key={src} onClick={() => setColor(colors[i] || '')} aria-label={`${colors[i] || '기본'} 이미지`}
                className={`w-16 shrink-0 overflow-hidden border md:w-full ${mainImage === src ? 'border-fg' : 'border-transparent'}`}>
                <img src={mediaUrl(src)} alt="" className="aspect-[4/5] w-full object-cover" />
              </button>
            ))}
          </div>
          <div className="order-1 overflow-hidden bg-surface-2 md:order-2">
            <img src={mediaUrl(mainImage)} alt={p.name} className="aspect-[4/5] w-full object-cover" />
          </div>
        </div>

        <div className="lg:sticky lg:top-36 lg:self-start">
          <p className="text-[12px] font-bold tracking-[0.08em] uppercase">fashionpick <span className="font-normal text-muted">· {p.category}</span></p>
          <h1 className="mt-2 text-[22px] leading-snug font-semibold md:text-[26px]">{p.name}</h1>
          <p className="mt-4 text-[26px] font-bold">{won(p.price)}</p>
          {p.trend && (
            <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1.5 text-[12px] text-accent">
              <FontAwesomeIcon icon={faFire} /> 트렌드 키워드 #{p.keyword} {p.trend.rank}위
              {p.trend.growth > 0 && <span>· 검색량 +{pct(p.trend.growth, 0)}</span>}
            </p>
          )}

          <div className="mt-7 space-y-6 border-t border-line pt-6">
            {colors.length > 0 && (
              <div>
                <p className="mb-2.5 text-[13px] font-semibold">색상 <span className="font-normal text-muted">{color}</span></p>
                <div className="flex flex-wrap gap-2">
                  {colors.map((c) => (
                    <button key={c} onClick={() => setColor(c)} title={c} aria-label={c} aria-pressed={color === c}
                      className={`grid size-9 place-items-center rounded-full border-2 ${color === c ? 'border-fg' : 'border-transparent'}`}>
                      <span className="grid size-7 place-items-center rounded-full border border-line" style={{ background: SWATCH[c] || '#ccc' }}>
                        {color === c && <FontAwesomeIcon icon={faCheck} className={`text-[10px] ${['아이보리', '베이지', '스카이블루'].includes(c) ? 'text-black' : 'text-white'}`} />}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {sizes.length > 0 && (
              <div>
                <p className="mb-2.5 text-[13px] font-semibold">사이즈</p>
                <div className="flex flex-wrap gap-2">
                  {sizes.map((s) => (
                    <button key={s} onClick={() => setSize(s)} aria-pressed={size === s}
                      className={`min-w-14 border px-3 py-2.5 text-[13px] transition ${size === s ? 'border-fg bg-fg text-bg' : 'border-line hover:border-fg'}`}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex items-center justify-between">
              <div className="flex items-center border border-line">
                <button onClick={() => setQty((q) => Math.max(1, q - 1))} className="grid size-10 place-items-center" aria-label="수량 감소"><FontAwesomeIcon icon={faMinus} className="text-xs" /></button>
                <span className="w-10 text-center text-[14px]">{qty}</span>
                <button onClick={() => setQty((q) => Math.min(p.stock || 99, q + 1))} className="grid size-10 place-items-center" aria-label="수량 증가"><FontAwesomeIcon icon={faPlus} className="text-xs" /></button>
              </div>
              <p className="text-[13px] text-muted">총 상품금액 <b className="ml-2 text-[20px] text-fg">{won(p.price * qty)}</b></p>
            </div>
          </div>

          {warn && <p className="mt-4 text-[13px] text-danger">{warn}</p>}
          <div className="mt-6 grid grid-cols-[56px_1fr] gap-2">
            <button onClick={toggleWish} aria-pressed={wish} aria-label="관심상품" className="grid h-14 place-items-center border border-line text-lg hover:border-fg">
              <FontAwesomeIcon icon={wish ? faHeart : faHeartLine} className={wish ? 'text-accent' : ''} />
            </button>
            <WriteButton onClick={buy} disabled={!p.in_stock} className="btn-primary h-14 rounded-none text-[15px]">
              {p.in_stock ? '바로 구매하기' : '품절'}
            </WriteButton>
          </div>
          <p className="mt-3 flex items-center gap-2 text-[12px] text-muted"><FontAwesomeIcon icon={faTruckFast} />주문 즉시 공급처 발주 · 평균 2~3일 내 출고</p>

          <div className="mt-8 border-t border-line">
            <Accordion title="상품 정보" defaultOpen>
              <dl className="grid grid-cols-[88px_1fr] gap-y-1.5">
                <dt>카테고리</dt><dd className="text-fg">{p.category}</dd>
                <dt>트렌드 키워드</dt><dd className="text-fg">#{p.keyword}</dd>
                <dt>색상</dt><dd className="text-fg">{colors.join(', ') || '-'}</dd>
                <dt>사이즈</dt><dd className="text-fg">{sizes.join(', ') || '-'}</dd>
                <dt>재고</dt><dd className="text-fg">{p.in_stock ? '구매 가능' : '일시 품절'}</dd>
              </dl>
            </Accordion>
            <Accordion title="배송 안내">주문이 접수되면 공급처별 발주서가 자동으로 작성·발송되며, 공급처 출고 후 2~3일 내 받아보실 수 있습니다. 5만원 이상 무료배송 (데모).</Accordion>
            <Accordion title="교환 · 반품 안내">상품 수령 후 7일 이내 교환·반품을 신청할 수 있습니다. 착용 흔적이 있거나 택이 제거된 경우 교환·반품이 제한됩니다.</Accordion>
          </div>
        </div>
      </div>

      {p.related?.length > 0 && (
        <section className="section">
          <h2 className="section-title mb-6">함께 보면 좋은 {p.category}</h2>
          <div className="product-grid">{p.related.slice(0, 4).map((r) => <ProductCard key={r.id} p={r} />)}</div>
        </section>
      )}

      <CheckoutModal open={checkout} onClose={() => setCheckout(false)} product={p} option={option} quantity={qty}
        onDone={(order) => { setCheckout(false); setDone(order) }} />
      <Modal open={!!done} onClose={() => setDone(null)} title="주문이 완료되었습니다">
        <p className="text-[14px]">주문번호 <b>{done?.order_no}</b></p>
        <p className="mt-1 text-[13px] text-muted">결제 금액 {won(done?.total_amount)} · 공급처 발주가 자동으로 진행됩니다.</p>
        <div className="mt-6 grid grid-cols-2 gap-2">
          <button className="btn-ghost" onClick={() => setDone(null)}>쇼핑 계속하기</button>
          <Link to="/mypage" className="btn-primary">주문 내역 보기</Link>
        </div>
      </Modal>
    </div>
  )
}
