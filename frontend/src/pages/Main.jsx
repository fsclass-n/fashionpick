import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRight, faChevronLeft, faChevronRight, faFire } from '@fortawesome/free-solid-svg-icons'
import { api, mediaUrl } from '../lib/api'
import { useAsync } from '../components/ui'
import ProductCard, { ProductGridSkeleton } from '../components/ProductCard'

const EN = { 아우터: 'Outerwear', 상의: 'Tops', 하의: 'Bottoms', 원피스: 'Dresses', 슈즈: 'Shoes', 가방: 'Bags', 액세서리: 'Accessories' }
const TONES = ['#ebe7df', '#e3e6e4', '#ece4dc']
const season = () => `${new Date().getMonth() >= 2 && new Date().getMonth() <= 7 ? 'SS' : 'FW'} ${String(new Date().getFullYear()).slice(2)}`

function SectionHead({ title, sub, to, label = '전체보기' }) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4 md:mb-8">
      <div>
        <h2 className="section-title">{title}</h2>
        {sub && <p className="section-sub">{sub}</p>}
      </div>
      {to && <Link to={to} className="shrink-0 text-[13px] text-muted hover:text-fg">{label} <FontAwesomeIcon icon={faArrowRight} className="ml-1 text-[11px]" /></Link>}
    </div>
  )
}

/** 룩북 히어로 캐러셀 */
function Hero({ slides, keywords }) {
  const [i, setI] = useState(0)
  const n = slides.length
  useEffect(() => {
    if (n < 2) return undefined
    const t = setInterval(() => setI((x) => (x + 1) % n), 6000)
    return () => clearInterval(t)
  }, [n])
  if (!n) return <div className="aspect-[16/7] animate-pulse bg-surface-2" />
  const s = slides[i]
  const kw = keywords.find((k) => k.category === s.category)?.keyword || s.items[0]?.keyword
  return (
    <section className="relative overflow-hidden" style={{ background: TONES[i % TONES.length] }} aria-roledescription="carousel">
      <div className="container-x grid min-h-[560px] items-center gap-8 py-10 md:grid-cols-[0.9fr_1.1fr] md:py-14 lg:min-h-[640px]">
        <div key={`t${i}`} className="animate-fade-in order-2 text-[#111] md:order-1">
          <p className="text-[11px] font-semibold tracking-[0.3em] text-black/55">{season()} LOOKBOOK · {String(i + 1).padStart(2, '0')}</p>
          <h1 className="mt-4 font-display text-[44px] leading-[0.95] md:text-[72px] lg:text-[88px]">
            {EN[s.category] || s.category}<br /><span className="italic">Edit</span>
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-7 text-black/65">
            이번 시즌 <b className="text-black">#{kw}</b> 키워드를 중심으로 고른 {s.category} 셀렉션. 매시간 수집되는 트렌드 데이터로 큐레이션을 갱신합니다.
          </p>
          <div className="mt-8 flex gap-2">
            <Link to={`/shop?category=${encodeURIComponent(s.category)}`} className="btn bg-black px-6 py-3 text-white hover:opacity-85">SHOP NOW</Link>
            <Link to="/trends" className="btn border border-black/20 px-6 py-3 text-black hover:bg-black/5">TREND REPORT</Link>
          </div>
        </div>
        <div key={`i${i}`} className="animate-fade-in order-1 grid grid-cols-[1.35fr_1fr] gap-3 md:order-2 md:gap-4">
          {s.items[0] && (
            <Link to={`/products/${s.items[0].id}`} className="row-span-2 overflow-hidden bg-white/40">
              <img src={mediaUrl(s.items[0].image_url)} alt={s.items[0].name} className="aspect-[4/5] size-full object-cover transition duration-700 hover:scale-[1.03]" />
            </Link>
          )}
          {s.items.slice(1, 3).map((p) => (
            <Link key={p.id} to={`/products/${p.id}`} className="overflow-hidden bg-white/40">
              <img src={mediaUrl(p.image_url)} alt={p.name} className="aspect-[4/5] size-full object-cover transition duration-700 hover:scale-[1.03]" />
            </Link>
          ))}
        </div>
      </div>
      {n > 1 && (
        <div className="container-x absolute inset-x-0 bottom-5 flex items-center gap-3 text-black">
          <button onClick={() => setI((i - 1 + n) % n)} className="grid size-9 place-items-center rounded-full bg-white/70 hover:bg-white" aria-label="이전 룩북"><FontAwesomeIcon icon={faChevronLeft} /></button>
          <button onClick={() => setI((i + 1) % n)} className="grid size-9 place-items-center rounded-full bg-white/70 hover:bg-white" aria-label="다음 룩북"><FontAwesomeIcon icon={faChevronRight} /></button>
          <div className="ml-2 flex gap-1.5">
            {slides.map((_, k) => (
              <button key={k} onClick={() => setI(k)} aria-label={`${k + 1}번 룩북`} className={`h-[3px] transition-all ${k === i ? 'w-10 bg-black' : 'w-5 bg-black/25'}`} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function TrendStrip({ keywords }) {
  return (
    <section className="border-b border-line">
      <div className="container-x flex items-center gap-5 overflow-x-auto py-4 [scrollbar-width:none]">
        <span className="flex shrink-0 items-center gap-2 text-[13px] font-bold"><FontAwesomeIcon icon={faFire} className="text-accent" />실시간 트렌드</span>
        {keywords.map((k) => (
          <Link key={k.keyword} to={`/shop?q=${encodeURIComponent(k.keyword)}`} className="flex shrink-0 items-center gap-1.5 text-[13px] text-muted hover:text-fg">
            <b className="text-fg">{k.rank}</b>{k.keyword}{k.surge && <span className="text-[10px] text-accent">▲</span>}
          </Link>
        ))}
      </div>
    </section>
  )
}

export default function Main() {
  const { data, error } = useAsync(() => api('/api/shop/home'))
  const kws = data?.trend_keywords || []

  return (
    <>
      <Hero slides={data?.lookbook || []} keywords={kws} />
      {kws.length > 0 && <TrendStrip keywords={kws} />}

      <section className="container-x section">
        <SectionHead title="CATEGORY" sub="카테고리별 셀렉션" />
        <div className="grid grid-cols-4 gap-x-3 gap-y-6 sm:grid-cols-7 md:gap-x-5">
          {(data?.categories || []).map((c) => (
            <Link key={c.category} to={`/shop?category=${encodeURIComponent(c.category)}`} className="group text-center">
              <div className="mx-auto aspect-square w-full max-w-[120px] overflow-hidden rounded-full bg-surface-2">
                <img src={mediaUrl(c.image_url)} alt="" className="size-full scale-110 object-cover transition duration-500 group-hover:scale-125" />
              </div>
              <p className="mt-2.5 text-[13px] font-semibold">{c.category}</p>
              <p className="text-[11px] text-muted">{c.count}개</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="container-x pb-14 md:pb-20">
        <SectionHead title="NEW ARRIVALS" sub="이번 주 새로 들어온 상품" to="/shop?sort=new" />
        {error ? <p className="text-sm text-danger">{error.message}</p> : !data ? <ProductGridSkeleton /> : (
          <div className="product-grid">{data.new_arrivals.map((p) => <ProductCard key={p.id} p={p} />)}</div>
        )}
      </section>

      <section id="lookbook" className="scroll-mt-32 bg-surface-2">
        <div className="container-x section">
          <SectionHead title="LOOKBOOK" sub="트렌드 키워드로 완성한 시즌 룩" />
          <div className="grid gap-4 md:grid-cols-3 md:gap-5">
            {(data?.lookbook || []).map((l, idx) => (
              <Link key={l.category} to={`/shop?category=${encodeURIComponent(l.category)}`} className={`group relative overflow-hidden bg-surface ${idx === 0 ? 'md:col-span-2 md:row-span-2' : ''}`}>
                <img src={mediaUrl(l.items[0]?.image_url)} alt="" className={`w-full object-cover transition duration-700 group-hover:scale-[1.03] ${idx === 0 ? 'aspect-[4/5] md:aspect-auto md:h-full' : 'aspect-[4/5]'}`} />
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-5 text-white md:p-7">
                  <p className="text-[11px] tracking-[0.3em] text-white/70">{season()} · {l.category}</p>
                  <p className="mt-1 font-display text-3xl italic md:text-4xl">{EN[l.category] || l.category}</p>
                  <p className="mt-2 text-[13px] text-white/80">#{l.items[0]?.keyword} 외 {l.items.length}개 스타일 <FontAwesomeIcon icon={faArrowRight} className="ml-1" /></p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="container-x section">
        <SectionHead title="TREND PICKS" sub="실시간 트렌드 키워드 순위로 고른 상품" to="/shop?sort=trend" />
        {!data ? <ProductGridSkeleton /> : (
          <div className="product-grid">{data.trend_picks.map((p, i) => <ProductCard key={p.id} p={p} rank={i + 1} />)}</div>
        )}
      </section>

      <section className="bg-[#111] text-[#f2efe8]">
        <div className="container-x grid gap-10 py-16 md:grid-cols-[1fr_1.4fr] md:py-20">
          <div>
            <p className="text-[11px] tracking-[0.3em] text-white/50">HOW WE CURATE</p>
            <h2 className="mt-3 font-display text-4xl leading-tight italic md:text-5xl">From trend<br />to order.</h2>
          </div>
          <div className="grid gap-6 sm:grid-cols-3">
            {[['01', '트렌드 수집', '데이터랩·랭킹 페이지에서 키워드를 매시간 수집합니다.'],
              ['02', '상품 소싱', '키워드로 도매 상품과 이미지를 찾아 큐레이션합니다.'],
              ['03', '발주 자동화', '주문 즉시 공급처별 발주서를 작성해 발송합니다.']].map(([n, t, d]) => (
              <div key={n} className="border-t border-white/15 pt-5">
                <p className="font-display text-2xl italic text-white/40">{n}</p>
                <p className="mt-2 font-semibold">{t}</p>
                <p className="mt-1 text-[13px] leading-6 text-white/60">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
