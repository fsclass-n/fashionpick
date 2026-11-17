import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleNotch, faEye, faEyeSlash, faKey, faShieldHalved } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { ErrorBox } from '../components/ui'

/** 실제 관리자 로그인: 서버 .env 의 ADMIN_TOKEN 으로만 진입 (전체 CRUD 권한) */
export default function AdminLogin() {
  const { isRealAdmin, adminLogin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [token, setToken] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [enabled, setEnabled] = useState(null)

  useEffect(() => { api('/api/auth/providers').then((p) => setEnabled(p.admin_login)).catch(() => setEnabled(null)) }, [])
  const dest = location.state?.from?.pathname?.startsWith('/admin') ? location.state.from.pathname : '/admin'
  if (isRealAdmin) return <Navigate to={dest} replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await adminLogin(token)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container-x grid place-items-center py-14 md:py-24">
      <div className="w-full max-w-md">
        <span className="grid size-14 place-items-center rounded-full bg-fg text-xl text-bg"><FontAwesomeIcon icon={faShieldHalved} /></span>
        <p className="eyebrow mt-6">Administrator</p>
        <h1 className="mt-2 font-display text-4xl md:text-5xl">Admin sign in</h1>
        <p className="mt-3 text-[13px] leading-6 text-muted">
          서버 <code className="rounded bg-surface-2 px-1.5 py-0.5">.env</code>의 <b className="text-fg">ADMIN_TOKEN</b>으로 인증하는 실제 관리자 전용 입구입니다.
          인증하면 모든 데이터를 생성·수정·삭제할 수 있습니다. 5회 실패하면 5분 동안 잠깁니다.
        </p>
        {enabled === false && (
          <p className="mt-5 rounded-xl border border-warn/40 bg-warn/10 px-4 py-3 text-[13px] text-warn">서버에 ADMIN_TOKEN이 설정되지 않아 실제 관리자 로그인이 비활성화되어 있습니다.</p>
        )}
        <form onSubmit={submit} className="mt-8 space-y-4">
          <div>
            <label className="label" htmlFor="admin-token">Admin Token</label>
            <div className="relative">
              <FontAwesomeIcon icon={faKey} className="absolute top-1/2 left-4 -translate-y-1/2 text-muted" />
              <input id="admin-token" type={show ? 'text' : 'password'} className="input pr-12 pl-11" value={token} autoComplete="off"
                onChange={(e) => setToken(e.target.value)} required placeholder="ADMIN_TOKEN 값을 입력하세요" />
              <button type="button" onClick={() => setShow((s) => !s)} className="absolute top-1/2 right-3 grid size-8 -translate-y-1/2 place-items-center text-muted" aria-label="토큰 표시">
                <FontAwesomeIcon icon={show ? faEyeSlash : faEye} />
              </button>
            </div>
          </div>
          <ErrorBox error={error} />
          <button className="btn-primary w-full rounded-xl py-3.5" disabled={busy || !token || enabled === false}>
            {busy && <FontAwesomeIcon icon={faCircleNotch} spin />}관리자 인증
          </button>
        </form>
        <p className="mt-8 text-center text-[13px] text-muted">
          화면만 둘러보시려면 <Link to="/login" className="font-semibold text-fg underline underline-offset-4">테스트 관리자 로그인(읽기 전용)</Link>을 이용하세요.
        </p>
      </div>
    </div>
  )
}
