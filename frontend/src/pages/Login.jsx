import { useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight, faArrowTrendUp, faArrowTrendDown, faCheck, faCircleNotch, faComment, faEye, faEyeSlash, faKey, faMinus,
  faStore, faUserShield,
} from '@fortawesome/free-solid-svg-icons'
import { faGoogle } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { api, oauthUrl } from '../lib/api'
import { ErrorBox } from '../components/ui'

const RULES = [
  { test: (p) => p.length >= 8, label: '8자 이상' },
  { test: (p) => /[A-Z]/.test(p), label: '영문 대문자' },
  { test: (p) => /[a-z]/.test(p), label: '영문 소문자' },
  { test: (p) => /\d/.test(p), label: '숫자' },
  { test: (p) => /[^A-Za-z0-9\s]/.test(p), label: '특수문자' },
]
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function TrendTop({ items }) {
  const max = Math.max(...items.map((i) => i.score), 1)
  return (
    <ol className="space-y-2.5">
      {items.map((k) => (
        <li key={k.keyword} className="grid grid-cols-[1.75rem_1fr_auto] items-center gap-3 text-sm">
          <span className="font-display text-lg italic text-white/50">{String(k.rank).padStart(2, '0')}</span>
          <span className="min-w-0">
            <span className="flex items-center gap-2">
              <span className="truncate font-medium">{k.keyword}</span>
              <span className="text-[10px] tracking-wider text-white/40">{k.category}</span>
              {k.surge && <span className="rounded-full bg-accent px-1.5 text-[10px] font-bold">HOT</span>}
            </span>
            <span className="mt-1 block h-[3px] overflow-hidden rounded-full bg-white/10">
              <span className="block h-full rounded-full bg-white/70 transition-all duration-700" style={{ width: `${(k.score / max) * 100}%` }} />
            </span>
          </span>
          <span className={`w-10 text-right text-xs ${k.rank_change > 0 ? 'text-[#f0a37c]' : k.rank_change < 0 ? 'text-white/40' : 'text-white/30'}`}>
            <FontAwesomeIcon icon={k.rank_change > 0 ? faArrowTrendUp : k.rank_change < 0 ? faArrowTrendDown : faMinus} className="mr-1" />
            {k.rank_change !== 0 && Math.abs(k.rank_change)}
          </span>
        </li>
      ))}
    </ol>
  )
}

/** 좌측: 시즌 룩북 무드 그래픽 + 실시간 트렌드 TOP 10 */
function MoodPanel({ top }) {
  const season = new Date().getMonth() >= 2 && new Date().getMonth() <= 7 ? 'SS' : 'FW'
  const year = String(new Date().getFullYear()).slice(2)
  return (
    <section className="relative overflow-hidden bg-[#0e0d0c] text-[#f4efe6]">
      <div className="pointer-events-none absolute inset-0">
        <div className="animate-float-slow absolute -top-24 -left-20 size-[28rem] rounded-full bg-[radial-gradient(circle,#b4532a_0%,transparent_65%)] opacity-50 blur-2xl" />
        <div className="absolute right-[-10%] bottom-[-15%] size-[32rem] rounded-full bg-[radial-gradient(circle,#6d2233_0%,transparent_60%)] opacity-50 blur-2xl" />
        <div className="absolute top-[18%] right-[12%] hidden h-[46%] w-[34%] rotate-3 border border-white/15 md:block" />
        <div className="absolute top-[22%] right-[16%] hidden h-[46%] w-[34%] -rotate-2 bg-gradient-to-b from-[#c9a27e]/25 to-transparent md:block" />
      </div>

      <div className="relative flex h-full flex-col px-6 pt-8 pb-6 md:px-10 md:py-10">
        <div className="flex items-center justify-between">
          <span className="font-display text-2xl italic">fashionpick</span>
          <span className="text-[11px] tracking-[0.3em] text-white/50">LOOKBOOK {season} {year}</span>
        </div>

        <div className="mt-6 md:mt-auto">
          <p className="text-[11px] tracking-[0.35em] text-white/50">TREND · SOURCING · ORDER</p>
          <p className="mt-3 font-display text-5xl leading-[0.95] md:text-6xl lg:text-7xl">
            <span className="italic">{season}</span>&nbsp;{year}
            <br />
            <span className="text-white/40">Edition</span>
          </p>
          <p className="mt-4 hidden max-w-sm text-sm text-white/60 md:block">
            RPA가 매시간 트렌드 키워드를 읽고, 도매 상품을 찾고, 주문이 들어오면 발주서까지 씁니다.
          </p>
        </div>

        {/* 모바일: 가로 마퀴로 압축해 스크롤 최소화 */}
        <div className="relative mt-6 -mx-6 overflow-hidden border-y border-white/10 py-3 md:hidden">
          <div className="animate-marquee flex w-max gap-6 whitespace-nowrap text-sm">
            {[...top, ...top].map((k, i) => (
              <span key={i} className="text-white/70">
                <span className="mr-1 font-display italic text-white/40">{k.rank}</span>#{k.keyword}
                {k.surge && <span className="ml-1 text-[#f0a37c]">▲</span>}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-10 hidden rounded-2xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur md:block">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-[11px] tracking-[0.3em] text-white/60">REAL-TIME TREND TOP 10</p>
            <span className="flex items-center gap-1.5 text-[11px] text-white/50">
              <span className="size-1.5 animate-pulse rounded-full bg-[#f0a37c]" /> LIVE
            </span>
          </div>
          {top.length ? <TrendTop items={top} /> : <p className="py-8 text-center text-sm text-white/40">트렌드 데이터를 불러오는 중…</p>}
        </div>
      </div>
    </section>
  )
}

function SocialButtons({ providers }) {
  const [msg, setMsg] = useState('')
  const items = [
    { id: 'google', label: 'Google', cls: 'border border-line bg-surface', icon: <FontAwesomeIcon icon={faGoogle} /> },
    { id: 'naver', label: '네이버', cls: 'bg-[#03C75A] text-white', icon: <span className="font-black">N</span> },
    { id: 'kakao', label: '카카오', cls: 'bg-[#FEE500] text-[#191919]', icon: <FontAwesomeIcon icon={faComment} /> },
  ]
  return (
    <div>
      <div className="grid grid-cols-3 gap-2">
        {items.map((p) => (
          <button key={p.id} type="button" className={`btn rounded-xl py-3 ${p.cls}`}
            onClick={() => (providers?.oauth?.[p.id] ? (window.location.href = oauthUrl(p.id)) : setMsg(`${p.label} 로그인은 서버에 OAuth 키 등록 후 사용할 수 있습니다.`))}>
            {p.icon}<span className="hidden sm:inline">{p.label}</span>
          </button>
        ))}
      </div>
      {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
    </div>
  )
}

export default function Login() {
  const { user, login, register, testLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const [mode, setMode] = useState(params.get('mode') === 'register' ? 'register' : 'login')
  const [form, setForm] = useState({ email: '', password: '', name: '' })
  const [showPw, setShowPw] = useState(false)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [providers, setProviders] = useState(null)
  const [top, setTop] = useState([])

  useEffect(() => {
    api('/api/auth/providers').then(setProviders).catch(() => {})
    const load = () => api('/api/trends/public-top?limit=10').then(setTop).catch(() => {})
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [])

  const rules = useMemo(() => RULES.map((r) => ({ ...r, ok: r.test(form.password) })), [form.password])
  const pwValid = rules.every((r) => r.ok)
  const dest = location.state?.from?.pathname || '/'

  if (user) return <Navigate to={dest} replace />

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    if (mode === 'register' && !pwValid) return setError('비밀번호 규칙을 모두 충족해야 합니다.')
    setBusy('form')
    try {
      if (mode === 'login') await login(form.email, form.password)
      else await register(form)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy('')
    }
  }

  /** 테스트 계정: 입력창에 자동 타이핑 후 세션 처리 */
  const quick = async (role) => {
    setError(null)
    setMode('login')
    setBusy(role)
    const email = providers?.test_accounts?.[role] || (role === 'admin' ? 'admin@fashionpick.dev' : 'user@fashionpick.dev')
    for (let i = 1; i <= email.length; i += 2) {
      setForm((f) => ({ ...f, email: email.slice(0, i), password: '' }))
      await sleep(18)
    }
    setForm((f) => ({ ...f, email }))
    for (let i = 1; i <= 10; i++) {
      setForm((f) => ({ ...f, password: '•'.repeat(i) }))
      await sleep(22)
    }
    try {
      await testLogin(role)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err)
      setForm((f) => ({ ...f, password: '' }))
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="container-x py-8 md:py-14">
    <div className="grid overflow-hidden border border-line md:grid-cols-[1.1fr_1fr]">
      <MoodPanel top={top} />

      <section className="relative flex items-start justify-center bg-surface px-6 py-10 md:items-center md:px-12 md:py-14">

        <div className="w-full max-w-md">
          <p className="eyebrow">Welcome back</p>
          <h1 className="mt-2 font-display text-4xl md:text-5xl">{mode === 'login' ? 'Sign in' : 'Create account'}</h1>
          <p className="mt-2 text-sm text-muted">트렌드부터 발주까지, 쇼핑몰 운영을 자동화하세요.</p>

          {providers?.test_login !== false && (
            <div className="mt-8 grid gap-2 sm:grid-cols-2">
              <button type="button" onClick={() => quick('user')} disabled={!!busy} className="btn-ghost justify-start rounded-xl px-4 py-3 text-left">
                <FontAwesomeIcon icon={busy === 'user' ? faCircleNotch : faStore} spin={busy === 'user'} />
                <span className="leading-tight"><span className="block">일반 회원 테스트 로그인</span><span className="text-[11px] text-muted">쇼핑 · 주문 · 마이페이지</span></span>
              </button>
              <button type="button" onClick={() => quick('admin')} disabled={!!busy} className="btn-primary justify-start rounded-xl px-4 py-3 text-left">
                <FontAwesomeIcon icon={busy === 'admin' ? faCircleNotch : faUserShield} spin={busy === 'admin'} />
                <span className="leading-tight"><span className="block">테스트 관리자 로그인</span><span className="text-[11px] opacity-60">관리자 화면 · 읽기 전용</span></span>
              </button>
            </div>
          )}

          <div className="my-7 flex items-center gap-4 text-xs text-muted">
            <span className="h-px flex-1 bg-line" />또는 이메일로<span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={submit} className="space-y-4" noValidate>
            {mode === 'register' && (
              <div>
                <label className="label" htmlFor="name">이름</label>
                <input id="name" className="input" value={form.name} onChange={set('name')} required maxLength={50} autoComplete="name" />
              </div>
            )}
            <div>
              <label className="label" htmlFor="email">이메일</label>
              <input id="email" type="email" className="input" value={form.email} onChange={set('email')} required autoComplete="email" placeholder="you@shop.com" />
            </div>
            <div>
              <label className="label" htmlFor="password">비밀번호</label>
              <div className="relative">
                <input id="password" type={showPw ? 'text' : 'password'} className="input pr-12" value={form.password} onChange={set('password')} required
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder="영문 대소문자·숫자·특수문자 8자 이상" />
                <button type="button" onClick={() => setShowPw((s) => !s)} className="absolute top-1/2 right-3 grid size-8 -translate-y-1/2 place-items-center text-muted" aria-label="비밀번호 표시">
                  <FontAwesomeIcon icon={showPw ? faEyeSlash : faEye} />
                </button>
              </div>
              {(mode === 'register' || form.password) && !busy && (
                <ul className="mt-3 flex flex-wrap gap-1.5">
                  {rules.map((r) => (
                    <li key={r.label} className={`chip ${r.ok ? 'border-success/40 text-success' : 'text-muted'}`}>
                      <FontAwesomeIcon icon={r.ok ? faCheck : faMinus} className="text-[10px]" />{r.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <ErrorBox error={error} />
            <button className="btn-accent w-full rounded-xl py-3.5 text-base" disabled={!!busy || (mode === 'register' && !pwValid)}>
              {busy === 'form' && <FontAwesomeIcon icon={faCircleNotch} spin />}
              {mode === 'login' ? '로그인' : '회원가입'}
            </button>
          </form>

          <div className="mt-6">
            <SocialButtons providers={providers} />
          </div>

          <Link to="/admin/login" state={location.state} className="mt-6 flex items-center justify-between rounded-xl border border-dashed border-line px-4 py-3 text-[13px] text-muted hover:border-fg hover:text-fg">
            <span><FontAwesomeIcon icon={faKey} className="mr-2" />실제 관리자 로그인 (ADMIN_TOKEN)</span>
            <FontAwesomeIcon icon={faArrowRight} />
          </Link>

          <p className="mt-8 text-center text-sm text-muted">
            {mode === 'login' ? '아직 회원이 아니신가요?' : '이미 계정이 있으신가요?'}{' '}
            <button className="font-semibold text-fg underline underline-offset-4" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}>
              {mode === 'login' ? '회원가입' : '로그인'}
            </button>
          </p>
        </div>
      </section>
    </div>
    </div>
  )
}
