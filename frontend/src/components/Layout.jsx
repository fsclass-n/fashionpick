import { Suspense, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowRight, faArrowUp, faComment, faGauge, faHeadset, faMagnifyingGlass, faMoon, faRightFromBracket, faSun, faUser,
} from '@fortawesome/free-solid-svg-icons'
import { faGithub, faInstagram, faYoutube } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useRealtime } from '../context/RealtimeContext'
import { CATEGORIES } from '../lib/format'
import { MAIN_NAV, ROLE_LABEL, SITE, SNS } from '../lib/site'
import Toasts, { OrderPopup } from './Toasts'
import { Spinner } from './ui'

const SNS_ICON = { instagram: faInstagram, youtube: faYoutube, kakao: faComment, github: faGithub }

function Logo({ className = '' }) {
  return (
    <Link to="/" className={`flex items-baseline gap-1 ${className}`} aria-label="fashionpick 홈">
      <span className="font-display text-[26px] leading-none font-semibold tracking-tight italic md:text-[30px]">fashionpick</span>
      <span className="size-1.5 rounded-full bg-accent" />
    </Link>
  )
}

function useSearchSubmit(onDone) {
  const navigate = useNavigate()
  return (q) => {
    if (!q.trim()) return
    navigate(`/shop?q=${encodeURIComponent(q.trim())}`)
    onDone?.()
  }
}

/** 최상단 유틸리티 바 (데스크톱) */
function TopBar() {
  const { user, isAdmin, logout } = useAuth()
  const { status } = useRealtime()
  const sep = <span className="h-2.5 w-px bg-line" />
  return (
    <div className="hidden border-b border-line text-[11px] text-muted md:block">
      <div className="container-x flex h-9 items-center justify-between">
        <p className="flex items-center gap-2">
          <span className={`size-1.5 rounded-full ${status === 'online' ? 'bg-success' : 'bg-accent'}`} />
          트렌드 키워드 기반 큐레이션 · RPA가 매시간 업데이트합니다
        </p>
        <nav className="flex items-center gap-3">
          {user ? (
            <>
              <span className="text-fg">{user.name}님</span>{sep}
              <Link to="/mypage" className="hover:text-fg">마이페이지</Link>{sep}
              {isAdmin && <><Link to="/admin" className="font-semibold text-fg hover:text-accent">관리자</Link>{sep}</>}
              <button onClick={logout} className="hover:text-fg">로그아웃</button>
            </>
          ) : (
            <>
              <Link to="/login" className="hover:text-fg">로그인</Link>{sep}
              <Link to="/login?mode=register" className="hover:text-fg">회원가입</Link>
            </>
          )}
          {sep}<Link to="/support" className="hover:text-fg">고객센터</Link>
        </nav>
      </div>
    </div>
  )
}

/** 햄버거 ↔ X 모션 */
function Hamburger({ open, onClick }) {
  const line = 'absolute left-0 h-[1.5px] w-[22px] bg-current transition-all duration-300 ease-[cubic-bezier(.7,0,.3,1)]'
  return (
    <button onClick={onClick} aria-label={open ? '메뉴 닫기' : '메뉴 열기'} aria-expanded={open}
      className="relative z-[61] grid size-10 place-items-center md:hidden">
      <span className="relative block h-4 w-[22px]">
        <span className={`${line} ${open ? 'top-[7px] rotate-45' : 'top-0'}`} />
        <span className={`${line} top-[7px] ${open ? 'translate-x-3 opacity-0' : 'opacity-100'}`} />
        <span className={`${line} ${open ? 'top-[7px] -rotate-45' : 'top-[14px]'}`} />
      </span>
    </button>
  )
}

function SearchBox({ className = '', onDone, autoFocus }) {
  const [params] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const submit = useSearchSubmit(onDone)
  return (
    <form onSubmit={(e) => { e.preventDefault(); submit(q) }} className={`relative ${className}`} role="search">
      <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus={autoFocus} aria-label="상품 검색"
        className="h-10 w-full rounded-full border border-line bg-surface-2 pr-11 pl-4 text-[13px] outline-none transition focus:border-fg focus:bg-surface"
        placeholder="트렌드 키워드, 상품명 검색" />
      <button className="absolute top-1/2 right-1.5 grid size-8 -translate-y-1/2 place-items-center text-muted hover:text-fg" aria-label="검색">
        <FontAwesomeIcon icon={faMagnifyingGlass} />
      </button>
    </form>
  )
}

function CategoryBar() {
  const location = useLocation()
  const [params] = useSearchParams()
  const active = location.pathname === '/shop' ? params.get('category') || 'ALL' : null
  const item = (key, to, label) => (
    <Link key={key} to={to}
      className={`relative shrink-0 py-3 text-[13px] transition md:text-sm ${active === key ? 'font-semibold text-fg after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-fg' : 'text-muted hover:text-fg'}`}>
      {label}
    </Link>
  )
  return (
    <div className="border-t border-line">
      <nav className="container-x flex gap-6 overflow-x-auto [scrollbar-width:none] md:gap-8" aria-label="카테고리">
        {item('ALL', '/shop', '전체')}
        {CATEGORIES.map((c) => item(c, `/shop?category=${encodeURIComponent(c)}`, c))}
      </nav>
    </div>
  )
}

function Drawer({ open, onClose }) {
  const { user, isAdmin, logout } = useAuth()
  const { dark, toggle } = useTheme()
  return (
    <>
      <div onClick={onClose}
        className={`fixed inset-0 z-[55] bg-black/40 backdrop-blur-sm transition-opacity duration-300 md:hidden ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`} />
      <aside aria-hidden={!open}
        className={`fixed top-0 right-0 z-[60] flex h-dvh w-[86%] max-w-sm flex-col overflow-y-auto bg-surface px-6 pt-32 pb-8 transition-[transform,visibility] duration-500 ease-[cubic-bezier(.7,0,.2,1)] md:hidden ${open ? 'visible translate-x-0 shadow-2xl' : 'invisible translate-x-full'}`}>
        <SearchBox onDone={onClose} />
        <nav className="mt-6 flex flex-col">
          {MAIN_NAV.map((n) => (
            <Link key={n.to} to={n.to} onClick={onClose} className="flex items-center justify-between border-b border-line py-4 text-xl font-bold tracking-tight">
              {n.label}<FontAwesomeIcon icon={faArrowRight} className="text-sm text-muted" />
            </Link>
          ))}
        </nav>
        <p className="eyebrow mt-8 mb-3">카테고리</p>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <Link key={c} to={`/shop?category=${encodeURIComponent(c)}`} onClick={onClose} className="chip px-3 py-1.5 text-sm">{c}</Link>
          ))}
        </div>
        <p className="eyebrow mt-8 mb-3">My</p>
        <div className="grid gap-2 text-sm">
          {user ? (
            <>
              <Link to="/mypage" onClick={onClose} className="rounded-xl bg-surface-2 px-4 py-3"><FontAwesomeIcon icon={faUser} className="mr-3" />마이페이지 · 주문내역</Link>
              <Link to="/mypage?tab=notify" onClick={onClose} className="rounded-xl bg-surface-2 px-4 py-3"><FontAwesomeIcon icon={faHeadset} className="mr-3" />주문·발주 알림 설정</Link>
              {isAdmin && <Link to="/admin" onClick={onClose} className="rounded-xl bg-fg px-4 py-3 text-bg"><FontAwesomeIcon icon={faGauge} className="mr-3" />관리자 콘솔</Link>}
            </>
          ) : (
            <Link to="/login" onClick={onClose} className="btn-primary py-3">로그인 / 회원가입</Link>
          )}
          <button onClick={toggle} className="rounded-xl bg-surface-2 px-4 py-3 text-left">
            <FontAwesomeIcon icon={dark ? faSun : faMoon} className="mr-3" />{dark ? '라이트 모드' : '다크 모드'}
          </button>
        </div>
        {user && (
          <div className="mt-auto pt-8">
            <p className="text-sm font-medium">{user.name}</p>
            <p className="mb-4 text-xs text-muted">{user.email} · {ROLE_LABEL[user.role]}</p>
            <button onClick={() => { logout(); onClose() }} className="btn-ghost w-full"><FontAwesomeIcon icon={faRightFromBracket} /> 로그아웃</button>
          </div>
        )}
      </aside>
    </>
  )
}

function Header() {
  const { user, isAdmin } = useAuth()
  const { dark, toggle } = useTheme()
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => setOpen(false), [location.pathname, location.search])
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
  }, [open])

  const navCls = 'text-[14px] font-bold tracking-[0.04em] transition hover:text-accent'
  const icon = 'grid size-10 place-items-center rounded-full transition hover:bg-surface-2'
  return (
    <>
      <TopBar />
      <header className="sticky top-0 z-[62] bg-bg/95 backdrop-blur-xl">
        <div className="container-x flex h-16 items-center gap-6 md:h-[72px] lg:gap-10">
          <Logo />
          <nav className="hidden items-center gap-7 md:flex" aria-label="주요 메뉴">
            {MAIN_NAV.map((n) => <Link key={n.to} to={n.to} className={navCls}>{n.label}</Link>)}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <SearchBox className="mr-2 hidden w-64 lg:block xl:w-80" />
            <Link to="/shop" className={`${icon} lg:hidden`} aria-label="검색"><FontAwesomeIcon icon={faMagnifyingGlass} /></Link>
            <button onClick={toggle} className={`${icon} hidden md:grid`} aria-label="테마 전환"><FontAwesomeIcon icon={dark ? faSun : faMoon} /></button>
            <Link to={user ? '/mypage' : '/login'} className={`${icon} hidden md:grid`} aria-label="마이페이지"><FontAwesomeIcon icon={faUser} /></Link>
            {isAdmin && (
              <NavLink to="/admin" className="btn-primary ml-1 hidden px-3.5 py-2 text-xs md:inline-flex">
                <FontAwesomeIcon icon={faGauge} />ADMIN
              </NavLink>
            )}
            <Hamburger open={open} onClick={() => setOpen((o) => !o)} />
          </div>
        </div>
        <CategoryBar />
        <div className="border-b border-line" />
      </header>
      <Drawer open={open} onClose={() => setOpen(false)} />
    </>
  )
}

function Footer() {
  const [show, setShow] = useState(false)
  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  const head = 'mb-4 text-[13px] font-bold text-fg'
  const li = 'block py-1 text-[13px] text-muted transition hover:text-fg'

  return (
    <footer className="mt-24 border-t border-line bg-surface">
      <div className="container-x grid gap-10 py-14 md:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-sm text-[13px] leading-6 text-muted">
            트렌드 키워드로 고르고, 도매 소싱부터 발주까지 자동화하는 패션 셀렉트숍.
          </p>
          <div className="mt-6 flex gap-2">
            {SNS.map((s) => s.url ? (
              <a key={s.id} href={s.url} target="_blank" rel="noreferrer" aria-label={s.label} title={s.label}
                className="grid size-10 place-items-center rounded-full border border-line transition hover:border-fg hover:bg-fg hover:text-bg">
                <FontAwesomeIcon icon={SNS_ICON[s.id]} />
              </a>
            ) : (
              <span key={s.id} aria-label={`${s.label} (준비 중)`} title={`${s.label} · 준비 중`}
                className="grid size-10 cursor-not-allowed place-items-center rounded-full border border-line text-muted/60">
                <FontAwesomeIcon icon={SNS_ICON[s.id]} />
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className={head}>고객센터</p>
          <p className="text-2xl font-bold tracking-tight">{SITE.cs.phone}</p>
          <p className="mt-2 text-[13px] leading-6 text-muted">{SITE.cs.hours}<br />{SITE.cs.lunch}<br />{SITE.cs.closed}</p>
          <a href={`mailto:${SITE.cs.email}`} className="mt-2 block text-[13px] text-muted hover:text-fg">{SITE.cs.email}</a>
        </div>
        <div>
          <p className={head}>쇼핑 안내</p>
          <Link to="/shop" className={li}>전체 상품</Link>
          <Link to="/shop?sort=new" className={li}>신상품</Link>
          <Link to="/trends" className={li}>트렌드 리포트</Link>
          <Link to="/mypage" className={li}>주문 조회</Link>
          <Link to="/support#faq" className={li}>자주 묻는 질문</Link>
        </div>
        <div>
          <p className={head}>회사</p>
          <Link to="/support#about" className={li}>회사 소개</Link>
          <Link to="/terms" className={li}>이용약관</Link>
          <Link to="/privacy" className={`${li} font-bold text-fg`}>개인정보처리방침</Link>
          <Link to="/support" className={li}>고객센터</Link>
          <Link to="/admin/login" className={li}>관리자 로그인</Link>
        </div>
      </div>
      <div className="border-t border-line">
        <div className="container-x py-7 text-[12px] leading-6 text-muted">
          <p className="flex flex-wrap gap-x-3">
            <span>상호 {SITE.company}</span><span>대표 {SITE.ceo}</span><span>사업자등록번호 {SITE.bizNo}</span>
            <span>통신판매업신고 {SITE.mailOrderNo}</span>
          </p>
          <p className="flex flex-wrap gap-x-3">
            <span>주소 {SITE.address}</span><span>개인정보보호책임자 {SITE.privacyOfficer}</span><span>호스팅 {SITE.hosting}</span>
          </p>
          <p className="mt-3">팀 fashionpick · 박미금(조장) · 김모란 · 이오리 · 홍기흥 — 포트폴리오용 데모 서비스로 실제 결제·배송이 이루어지지 않습니다.</p>
          <p className="mt-1">© {new Date().getFullYear()} fashionpick. All rights reserved.</p>
        </div>
      </div>
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        aria-label="맨 위로 이동"
        className={`fixed right-5 bottom-5 z-40 grid size-12 place-items-center rounded-full border border-line bg-surface text-fg shadow-[0_6px_24px_rgba(0,0,0,.12)] transition-all duration-300 hover:-translate-y-1 hover:bg-fg hover:text-bg md:right-8 md:bottom-8 ${show ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'}`}
      >
        <FontAwesomeIcon icon={faArrowUp} />
      </button>
    </footer>
  )
}

/** 모든 페이지 공통 레이아웃: 글로벌 헤더 + 본문 + 푸터 + 실시간 알림 */
export default function Layout() {
  const location = useLocation()
  useEffect(() => {
    if (location.hash) {
      document.getElementById(location.hash.slice(1))?.scrollIntoView({ behavior: 'smooth' })
    } else {
      window.scrollTo(0, 0)
    }
  }, [location.pathname, location.hash])

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="w-full flex-1">
        <Suspense fallback={<Spinner />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <Toasts />
      <OrderPopup />
    </div>
  )
}
