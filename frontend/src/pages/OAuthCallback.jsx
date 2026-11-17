import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from '../components/ui'

const ERRORS = {
  invalid_state: '로그인 요청이 만료되었거나 올바르지 않습니다.',
  provider_error: '소셜 로그인 제공자와 통신 중 오류가 발생했습니다.',
  cancelled: '로그인이 취소되었습니다.',
}

export default function OAuthCallback() {
  const { acceptToken } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1))
    window.history.replaceState(null, '', window.location.pathname)
    const token = params.get('token')
    if (!token) return setError(ERRORS[params.get('error')] || '소셜 로그인에 실패했습니다.')
    acceptToken(token).then(() => navigate('/', { replace: true })).catch(() => setError('세션 생성에 실패했습니다.'))
  }, [acceptToken, navigate])

  if (!error) return <Spinner label="소셜 로그인 처리 중" />
  return (
    <div className="container-x grid place-items-center py-24 text-center">
      <div>
        <p className="font-display text-3xl">Login failed</p>
        <p className="mt-3 text-sm text-muted">{error}</p>
        <Link to="/login" className="btn-primary mt-6">로그인으로 돌아가기</Link>
      </div>
    </div>
  )
}
