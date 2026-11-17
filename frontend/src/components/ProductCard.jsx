import { useState } from 'react'
import { Link } from 'react-router-dom'
import { mediaUrl } from '../lib/api'
import { won } from '../lib/format'

/** 스토어프런트 표준 상품 카드 (4:5 이미지 · 브랜드 · 상품명 · 가격 · 키워드) */
export default function ProductCard({ p, rank }) {
  const [loaded, setLoaded] = useState(false)
  return (
    <Link to={`/products/${p.id}`} className="group block">
      <div className="relative aspect-[4/5] overflow-hidden bg-surface-2">
        <img src={mediaUrl(p.image_url)} alt={p.name} loading="lazy" onLoad={() => setLoaded(true)}
          className={`size-full object-cover transition duration-700 ease-out group-hover:scale-[1.03] ${loaded ? 'opacity-100' : 'opacity-0'}`} />
        <div className="absolute top-2.5 left-2.5 flex flex-wrap gap-1">
          {p.is_new && <span className="bg-fg px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-bg">NEW</span>}
          {p.trend_surge && <span className="bg-accent px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white">HOT</span>}
        </div>
        {rank != null && (
          <span className="absolute bottom-0 left-0 grid size-8 place-items-center bg-fg text-[13px] font-bold text-bg">{rank}</span>
        )}
        {!p.in_stock && (
          <div className="absolute inset-0 grid place-items-center bg-white/55 text-[13px] font-semibold tracking-widest text-black">SOLD OUT</div>
        )}
      </div>
      <div className="space-y-1 pt-3">
        <p className="text-[11px] font-bold tracking-[0.08em] uppercase">fashionpick <span className="font-normal text-muted">· {p.category}</span></p>
        <p className="line-clamp-2 text-[13px] leading-snug text-fg/85 group-hover:underline group-hover:underline-offset-2">{p.name}</p>
        <p className="text-[15px] font-bold">{won(p.price)}</p>
        <p className="text-[11px] text-muted">
          #{p.keyword}{p.trend_rank && p.trend_rank <= 20 && <span className="ml-1.5 text-accent">트렌드 {p.trend_rank}위</span>}
        </p>
      </div>
    </Link>
  )
}

export function ProductGridSkeleton({ count = 8 }) {
  return (
    <div className="product-grid">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="animate-pulse">
          <div className="aspect-[4/5] bg-surface-2" />
          <div className="mt-3 h-3 w-1/3 bg-surface-2" />
          <div className="mt-2 h-3 w-4/5 bg-surface-2" />
          <div className="mt-2 h-4 w-1/4 bg-surface-2" />
        </div>
      ))}
    </div>
  )
}
