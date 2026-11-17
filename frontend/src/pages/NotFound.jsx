import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="font-display text-8xl italic">404</p>
      <p className="mt-4 text-muted">찾으시는 페이지가 없습니다.</p>
      <Link to="/" className="btn-primary mt-8">대시보드로</Link>
    </div>
  )
}
