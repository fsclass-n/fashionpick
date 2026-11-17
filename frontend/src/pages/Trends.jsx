import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowDown, faArrowUp, faFire, faMinus, faRotate, faStar } from '@fortawesome/free-solid-svg-icons'
import { api } from '../lib/api'
import { CATEGORIES, dateTime, pct } from '../lib/format'
import { useRealtimeEvent } from '../context/RealtimeContext'
import { Badge, ErrorBox, PageHeader, Spinner, Tabs, useAsync } from '../components/ui'
import Plot from '../components/Plot'

function WordCloud({ items }) {
  const max = Math.max(...items.map((i) => i.score), 1)
  const min = Math.min(...items.map((i) => i.score), 0)
  const shuffled = useMemo(() => [...items].sort((a, b) => (a.keyword.length * 7 + a.rank) % 5 - (b.keyword.length * 7 + b.rank) % 5), [items])
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 py-4">
      {shuffled.map((k) => {
        const t = (k.score - min) / (max - min || 1)
        return (
          <Link key={k.keyword} to={`/sourcing?keyword=${encodeURIComponent(k.keyword)}`}
            className={`leading-none transition hover:text-accent ${k.surge ? 'text-accent' : t > 0.6 ? 'text-fg' : 'text-muted'}`}
            style={{ fontSize: `${0.8 + t * 1.9}rem`, fontWeight: 300 + Math.round(t * 5) * 100 }}
            title={`${k.category} · ${k.rank}위 · ${k.score}`}>
            {k.surge && <FontAwesomeIcon icon={faFire} className="mr-1 text-[0.6em]" />}
            {k.keyword}
          </Link>
        )
      })}
    </div>
  )
}

function RankChange({ k }) {
  if (k.is_new) return <Badge tone="accent">NEW</Badge>
  if (!k.rank_change) return <span className="text-muted"><FontAwesomeIcon icon={faMinus} /></span>
  const up = k.rank_change > 0
  return (
    <span className={up ? 'text-accent' : 'text-muted'}>
      <FontAwesomeIcon icon={up ? faArrowUp : faArrowDown} className="mr-1 text-xs" />{Math.abs(k.rank_change)}
    </span>
  )
}

export default function Trends() {
  const [category, setCategory] = useState('')
  const latest = useAsync(() => api('/api/trends/latest'))
  const cats = useAsync(() => api('/api/trends/categories'))
  const [selected, setSelected] = useState([])
  const top5 = useMemo(() => (latest.data || []).slice(0, 5).map((k) => k.keyword), [latest.data])
  const tracked = selected.length ? selected : top5
  const hist = useAsync(() => (tracked.length ? api(`/api/trends/history?keywords=${encodeURIComponent(tracked.join(','))}`) : Promise.resolve({ series: [] })), [tracked.join(',')])

  useRealtimeEvent('rpa.job', (m) => m.data.job === 'trend_collect' && m.data.status === 'success' && (latest.reload(), cats.reload(), hist.reload()))

  const list = useMemo(() => (latest.data || []).filter((k) => !category || k.category === category), [latest.data, category])
  const toggle = (kw) => setSelected((s) => (s.includes(kw) ? s.filter((x) => x !== kw) : [...s, kw].slice(-6)))

  const lineData = useMemo(() => (hist.data?.series || []).map((s) => ({
    x: s.points.map((p) => new Date(p.at)), y: s.points.map((p) => p.score), name: s.keyword, type: 'scatter', mode: 'lines',
    line: { width: 2.5, shape: 'spline' },
  })), [hist.data])
  const barData = useMemo(() => {
    const top = [...list].slice(0, 12).reverse()
    return [{ type: 'bar', orientation: 'h', x: top.map((k) => k.score), y: top.map((k) => k.keyword),
      marker: { color: top.map((k) => (k.surge ? '#b4532a' : '#8a8378')) }, hovertemplate: '%{y}: %{x:.1f}<extra></extra>' }]
  }, [list])
  const treeData = useMemo(() => {
    const items = latest.data || []
    return [{ type: 'treemap', branchvalues: 'remainder',
      labels: ['전체', ...CATEGORIES, ...items.map((k) => k.keyword)],
      parents: ['', ...CATEGORIES.map(() => '전체'), ...items.map((k) => k.category)],
      values: [0, ...CATEGORIES.map(() => 0), ...items.map((k) => k.score)],
      textinfo: 'label+percent parent', marker: { line: { width: 1 } }, hovertemplate: '%{label}<br>%{value:.1f}<extra></extra>' }]
  }, [latest.data])
  const LAYOUT_LINE = useMemo(() => ({ yaxis: { title: { text: '검색 지수' } }, hovermode: 'x unified' }), [])
  const LAYOUT_BAR = useMemo(() => ({ margin: { l: 110, r: 16, t: 8, b: 32 } }), [])
  const LAYOUT_TREE = useMemo(() => ({ margin: { l: 0, r: 0, t: 0, b: 0 } }), [])

  const collectedAt = latest.data?.[0]?.collected_at

  return (
    <>
      <PageHeader eyebrow="Trend Keywords" title={<>What’s <span className="italic">trending</span></>}
        desc="RPA가 수집한 패션 키워드의 순위 변동, 검색량 추이, 카테고리별 비중입니다. 급상승 키워드는 자동으로 하이라이트됩니다."
        actions={<button className="btn-ghost" onClick={() => { latest.reload(); cats.reload(); hist.reload() }}><FontAwesomeIcon icon={faRotate} /> 새로고침</button>} />
      <ErrorBox error={latest.error} />
      {latest.loading && !latest.data ? <Spinner /> : (
        <div className="space-y-6">
          <section className="card p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl">Keyword cloud</h2>
              <span className="text-xs text-muted">최근 수집 {dateTime(collectedAt)}</span>
            </div>
            <WordCloud items={latest.data || []} />
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="card p-6">
              <h2 className="text-2xl">Search index trend</h2>
              <p className="mb-2 text-xs text-muted">{selected.length ? '선택한 키워드' : '상위 5개 키워드'} · 표에서 <FontAwesomeIcon icon={faStar} /> 로 비교 키워드 선택</p>
              {hist.loading && !hist.data ? <Spinner /> : <Plot data={lineData} layout={LAYOUT_LINE} />}
            </section>
            <section className="card p-6">
              <h2 className="text-2xl">Category share</h2>
              <p className="mb-2 text-xs text-muted">카테고리 → 키워드 트리맵</p>
              <Plot data={treeData} layout={LAYOUT_TREE} />
            </section>
          </div>

          <section>
            <Tabs value={category} onChange={setCategory}
              tabs={[{ value: '', label: '전체', count: latest.data?.length }, ...CATEGORIES.map((c) => ({ value: c, label: c, count: (latest.data || []).filter((k) => k.category === c).length }))]} />
            <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
              <div className="card p-6">
                <h2 className="mb-2 text-2xl">Top 12 {category && <span className="text-base text-muted">· {category}</span>}</h2>
                <Plot data={barData} layout={LAYOUT_BAR} height={380} />
              </div>
              <div className="table-wrap max-h-[34rem] overflow-y-auto">
                <table>
                  <thead className="sticky top-0 z-10 bg-surface"><tr><th></th><th>순위</th><th>키워드</th><th>카테고리</th><th className="text-right">점수</th><th className="text-right">증감</th><th>변동</th><th></th></tr></thead>
                  <tbody>
                    {list.map((k) => (
                      <tr key={k.keyword} className={k.surge ? 'bg-accent/5' : ''}>
                        <td><button onClick={() => toggle(k.keyword)} aria-label="비교" className={selected.includes(k.keyword) ? 'text-accent' : 'text-line hover:text-muted'}><FontAwesomeIcon icon={faStar} /></button></td>
                        <td className="font-display text-lg italic">{k.rank}</td>
                        <td className="font-medium">{k.keyword} {k.surge && <Badge tone="accent" className="ml-1"><FontAwesomeIcon icon={faFire} />급상승</Badge>}</td>
                        <td className="text-muted">{k.category}</td>
                        <td className="text-right">{k.score.toFixed(1)}</td>
                        <td className={`text-right ${k.growth > 0 ? 'text-accent' : 'text-muted'}`}>{k.growth > 0 ? '+' : ''}{pct(k.growth)}</td>
                        <td><RankChange k={k} /></td>
                        <td><Link to={`/sourcing?keyword=${encodeURIComponent(k.keyword)}`} className="text-xs text-muted underline-offset-4 hover:text-fg hover:underline">소싱 →</Link></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

          {cats.data && (
            <section className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
              {cats.data.map((c) => (
                <button key={c.category} onClick={() => setCategory(c.category)} className={`card p-4 text-left transition hover:border-fg ${category === c.category ? 'border-fg' : ''}`}>
                  <p className="eyebrow">{c.category}</p>
                  <p className="mt-2 font-display text-2xl">{pct(c.share, 0)}</p>
                  <p className="text-xs text-muted">키워드 {c.keywords} · 급상승 {c.surges}</p>
                </button>
              ))}
            </section>
          )}
        </div>
      )}
    </>
  )
}
