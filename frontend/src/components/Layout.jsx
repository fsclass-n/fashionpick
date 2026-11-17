import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowUp, faBell, faChartLine, faGaugeHigh, faMagnifyingGlass, faMoon, faRightFromBracket,
  faShirt, faSun, faTruckFast, faUserShield, faGear, faArrowRight,
} from '@fortawesome/free-solid-svg-icons'
import { faGithub } from '@fortawesome/free-brands-svg-icons'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useRealtime } from '../context/RealtimeContext'
import { CATEGORIES } from '../lib/format'
import Toasts, { OrderPopup } from './Toasts'

const NAV = [
  { to: '/', label: '대시보드', icon: faGaugeHigh, end: true },
  { to: '/trends', label: '트렌드', icon: faChartLine },
  { to: '/sourcing', label: '상품 소싱', icon: faShirt },
  { to: '/orders', label: '주문·발주', icon: faTruckFast },
]

function Logo() {
  return (
    <Link to="/" className="flex items-baseline gap-1.5">
      <span className="font-display text-2xl font-semibold italic tracking-tight">fashionpick</span>
      <span className="size-1.5 rounded-full bg-accent" />
    </Link>
  )
}

function WsDot() {
  const { status } = useRealtime()
  const color = { online: 'bg-success', connecting: 'bg-warn animate-pulse', offline: 'bg-muted' }[status]
  const label = { online: '실시간 연결됨', connecting: '연결 중', offline: '오프라인' }[status]
  return (
    <span className="hidden items-center gap-2 text-xs text-muted lg:inline-flex" title={label}>
      <span className={`size-2 rounded-full ${color}`} /> LIVE
    </span>
  )
}

/** 햄버거 ↔ X 자 아이콘 모션 */
function Hamburger({ open, onClick }) {
  const line = 'absolute left-0 h-[1.5px] w-6 bg-current transition-all duration-300 ease-[cubic-bezier(.7,0,.3,1)]'
  return (
    <button onClick={onClick} aria-label={open ? '메뉴 닫기' : '메뉴 열기'} aria-expanded={open}
      className="relative z-[61] grid size-11 place-items-center rounded-full md:hidden">
      <span className="relative block h-4 w-6">
        <span className={`${line} ${open ? 'top-[7px] rotate-45' : 'top-0'}`} />
        <span className={`${line} top-[7px] ${open ? 'translate-x-3 opacity-0' : 'opacity-100'}`} />
        <span className={`${line} ${open ? 'top-[7px] -rotate-45' : 'top-[14px]'}`} />
      </span>
    </button>
  )
}

/** 우측 → 좌측 슬라이딩 드로어 (모바일) */
function Drawer({ open, onClose }) {
  const { user, isAdmin, logout } = useAuth()
  const { dark, toggle } = useTheme()
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  const search = (e) => {
    e.preventDefault()
    if (!q.trim()) return
    navigate(`/sourcing?q=${encodeURIComponent(q.trim())}`)
    onClose()
  }

  return (
    <>
      <div onClick={onClose}
        className={`fixed inset-0 z-[55] bg-black/40 backdrop-blur-sm transition-opacity duration-300 md:hidden ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`} />
      <aside aria-hidden={!open}
        className={`fixed top-0 right-0 z-[60] flex h-dvh w-[86%] max-w-sm flex-col overflow-y-auto bg-surface px-6 pt-20 pb-8 shadow-2xl transition-transform duration-500 ease-[cubic-bezier(.7,0,.2,1)] md:hidden ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <form onSubmit={search} className="relative mb-6">
          <FontAwesomeIcon icon={faMagnifyingGlass} className="absolute top-1/2 left-4 -translate-y-1/2 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} className="input rounded-full pl-11" placeholder="트렌드 키워드·상품 검색" />
        </form>

        <nav className="flex flex-col">
          {[...NAV, ...(isAdmin ? [{ to: '/admin', label: '관리자', icon: faUserShield }] : [])].map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} onClick={onClose}
              className={({ isActive }) => `flex items-center justify-between border-b border-line py-4 font-display text-2xl ${isActive ? 'text-accent' : ''}`}>
              {n.label}
              <FontAwesomeIcon icon={n.icon} className="text-base text-muted" />
            </NavLink>
          ))}
        </nav>

        <p className="eyebrow mt-8 mb-3">카테고리</p>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <Link key={c} to={`/sourcing?category=${encodeURIComponent(c)}`} onClick={onClose} className="chip px-3 py-1.5 text-sm hover:bg-surface-2">
              {c}
            </Link>
          ))}
        </div>

        <p className="eyebrow mt-8 mb-3">설정</p>
        <Link to="/settings" onClick={onClose} className="flex items-center justify-between rounded-xl bg-surface-2 px-4 py-3 text-sm">
          <span><FontAwesomeIcon icon={faBell} className="mr-3" />주문·발주 알림 설정</span>
          <FontAwesomeIcon icon={faArrowRight} className="text-muted" />
        </Link>
        <button onClick={toggle} className="mt-2 flex items-center justify-between rounded-xl bg-surface-2 px-4 py-3 text-sm">
          <span><FontAwesomeIcon icon={dark ? faSun : faMoon} className="mr-3" />{dark ? '라이트 모드' : '다크 모드'}</span>
        </button>

        <div className="mt-auto pt-8">
          <p className="text-sm font-medium">{user?.name}</p>
          <p className="mb-4 text-xs text-muted">{user?.email} · {user?.role === 'admin' ? '관리자' : '일반 회원'}</p>
          <button onClick={logout} className="btn-ghost w-full"><FontAwesomeIcon icon={faRightFromBracket} /> 로그아웃</button>
        </div>
      </aside>
    </>
  )
}

function Header() {
  const { user, isAdmin, logout } = useAuth()
  const { dark, toggle } = useTheme()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => setOpen(false), [location.pathname])
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
  }, [open])
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const link = ({ isActive }) =>
    `relative px-1 py-2 text-sm transition after:absolute after:inset-x-0 after:-bottom-px after:h-px after:origin-left after:bg-fg after:transition-transform ${isActive ? 'text-fg after:scale-x-100' : 'text-muted hover:text-fg after:scale-x-0'}`

  return (
    <>
      <header className={`sticky top-0 z-[62] border-b transition-colors ${scrolled || open ? 'border-line bg-bg/85 backdrop-blur-xl' : 'border-transparent bg-bg'}`}>
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-5 md:h-20 md:px-8">
          <Logo />
          <nav className="hidden items-center gap-7 md:flex">
            {NAV.map((n) => <NavLink key={n.to} to={n.to} end={n.end} className={link}>{n.label}</NavLink>)}
            {isAdmin && <NavLink to="/admin" className={link}>관리자</NavLink>}
          </nav>
          <div className="flex items-center gap-1 md:gap-2">
            <WsDot />
            <Link to="/settings" className="hidden size-10 place-items-center rounded-full hover:bg-surface-2 md:grid" aria-label="알림 설정">
              <FontAwesomeIcon icon={faGear} />
            </Link>
            <button onClick={toggle} className="hidden size-10 place-items-center rounded-full hover:bg-surface-2 md:grid" aria-label="테마 전환">
              <FontAwesomeIcon icon={dark ? faSun : faMoon} />
            </button>
            <div className="hidden items-center gap-3 border-l border-line pl-4 md:flex">
              <div className="text-right leading-tight">
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-[11px] text-muted">{isAdmin ? 'ADMIN' : 'MEMBER'}</p>
              </div>
              <button onClick={logout} className="grid size-10 place-items-center rounded-full hover:bg-surface-2" aria-label="로그아웃">
                <FontAwesomeIcon icon={faRightFromBracket} />
              </button>
            </div>
            <Hamburger open={open} onClick={() => setOpen((o) => !o)} />
          </div>
        </div>
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

  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-[2fr_1fr_1fr] md:px-8">
        <div>
          <p className="font-display text-4xl italic md:text-6xl">From trend<br />to order.</p>
          <p className="mt-4 max-w-md text-sm text-muted">
            RPA로 트렌드 키워드를 읽고, 도매 상품을 소싱하고, 발주서까지 자동으로. 패션 쇼핑몰 운영 자동화 플랫폼 fashionpick.
          </p>
        </div>
        <div className="text-sm">
          <p className="eyebrow mb-3">Team</p>
          <p className="leading-7 text-muted">박미금(조장) · 김모란<br />이오리 · 홍기흥</p>
        </div>
        <div className="text-sm">
          <p className="eyebrow mb-3">Links</p>
          <a href="https://fsclass-n.github.io/fashionpick/" target="_blank" rel="noreferrer" className="block leading-7 text-muted hover:text-fg">Project Page</a>
          <a href="https://github.com/fsclass-n/fashionpick" target="_blank" rel="noreferrer" className="block leading-7 text-muted hover:text-fg">
            <FontAwesomeIcon icon={faGithub} className="mr-1.5" />GitHub
          </a>
        </div>
      </div>
      <div className="border-t border-line py-6 text-center text-xs text-muted">© {new Date().getFullYear()} fashionpick. All rights reserved.</div>
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        aria-label="맨 위로"
        className={`fixed right-5 bottom-5 z-40 grid size-12 place-items-center rounded-full bg-fg text-bg shadow-lg transition-all duration-300 hover:-translate-y-1 md:right-8 md:bottom-8 ${show ? 'translate-y-0 opacity-100' : 'pointer-events-none translate-y-4 opacity-0'}`}
      >
        <FontAwesomeIcon icon={faArrowUp} />
      </button>
    </footer>
  )
}

export default function Layout() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 px-5 pt-8 md:px-8 md:pt-12">
        <Outlet />
      </main>
      <Footer />
      <Toasts />
      <OrderPopup />
    </div>
  )
}
