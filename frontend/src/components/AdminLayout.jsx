import { Link, NavLink, Outlet } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faGaugeHigh, faKey, faLock, faRobot, faShieldHalved, faShirt, faStore, faTruckFast, faUsers,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/admin', label: '대시보드', icon: faGaugeHigh, end: true },
  { to: '/admin/sourcing', label: '상품 소싱', icon: faShirt },
  { to: '/admin/orders', label: '주문·발주', icon: faTruckFast },
  { to: '/admin/rpa', label: 'RPA 작업', icon: faRobot },
  { to: '/admin/suppliers', label: '공급처', icon: faStore },
  { to: '/admin/members', label: '회원 권한', icon: faUsers },
]

/** 관리자 콘솔 공통 레이아웃 (글로벌 헤더/푸터 안쪽에 위치) */
export default function AdminLayout() {
  const { user, readOnly } = useAuth()
  return (
    <div className="container-x pt-6 md:pt-8">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <p className="flex items-center gap-2 text-[13px] font-bold tracking-[0.12em]">
          <FontAwesomeIcon icon={faShieldHalved} />ADMIN CONSOLE
        </p>
        <p className="flex items-center gap-2 text-[12px] text-muted">
          {user.name}
          {readOnly ? (
            <span className="chip border-warn/40 bg-warn/10 font-semibold text-warn"><FontAwesomeIcon icon={faLock} />테스트 관리자 · 읽기 전용</span>
          ) : (
            <span className="chip border-success/40 bg-success/10 font-semibold text-success"><FontAwesomeIcon icon={faKey} />실제 관리자 · 전체 권한</span>
          )}
        </p>
      </div>

      <nav className="-mx-5 flex gap-1 overflow-x-auto border-b border-line px-5 [scrollbar-width:none] md:mx-0 md:px-0" aria-label="관리자 메뉴">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}
            className={({ isActive }) => `relative flex shrink-0 items-center gap-2 px-3 py-3.5 text-[13px] transition md:px-4 md:text-sm ${isActive ? 'font-semibold text-fg after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-fg' : 'text-muted hover:text-fg'}`}>
            <FontAwesomeIcon icon={n.icon} className="text-xs" />{n.label}
          </NavLink>
        ))}
      </nav>

      {readOnly && (
        <div className="mt-5 flex flex-col gap-3 rounded-2xl border border-warn/40 bg-warn/10 px-5 py-4 text-[13px] md:flex-row md:items-center md:justify-between" role="status">
          <p className="text-fg">
            <FontAwesomeIcon icon={faLock} className="mr-2 text-warn" />
            <b>읽기 전용 모드</b> — 모든 관리자 화면을 조회할 수 있지만, 데이터 생성·수정·삭제 요청은 서버에서 차단됩니다.
          </p>
          <Link to="/admin/login" className="btn-primary shrink-0 px-4 py-2 text-xs"><FontAwesomeIcon icon={faKey} />실제 관리자로 로그인</Link>
        </div>
      )}

      <div className="pt-8 md:pt-10">
        <Outlet />
      </div>
    </div>
  )
}
