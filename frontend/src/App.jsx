import { lazy } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Main from './pages/Main'

const Shop = lazy(() => import('./pages/Shop'))
const ProductDetail = lazy(() => import('./pages/ProductDetail'))
const Trends = lazy(() => import('./pages/Trends'))
const Login = lazy(() => import('./pages/Login'))
const AdminLogin = lazy(() => import('./pages/AdminLogin'))
const OAuthCallback = lazy(() => import('./pages/OAuthCallback'))
const MyPage = lazy(() => import('./pages/MyPage'))
const Terms = lazy(() => import('./pages/Info').then((m) => ({ default: m.Terms })))
const Privacy = lazy(() => import('./pages/Info').then((m) => ({ default: m.Privacy })))
const Support = lazy(() => import('./pages/Info').then((m) => ({ default: m.Support })))
const NotFound = lazy(() => import('./pages/NotFound'))
const AdminLayout = lazy(() => import('./components/AdminLayout'))
const AdminDashboard = lazy(() => import('./pages/admin/Dashboard'))
const AdminSourcing = lazy(() => import('./pages/admin/Sourcing'))
const AdminOrders = lazy(() => import('./pages/admin/Orders'))
const AdminRpa = lazy(() => import('./pages/admin/Manage').then((m) => ({ default: m.AdminRpa })))
const AdminSuppliers = lazy(() => import('./pages/admin/Manage').then((m) => ({ default: m.AdminSuppliers })))
const AdminMembers = lazy(() => import('./pages/admin/Manage').then((m) => ({ default: m.AdminMembers })))

/** 로그인 필요 페이지. admin: 실제 관리자 + 테스트 관리자(읽기 전용) */
function RequireAuth({ children, admin }) {
  const { user, loading, isAdmin } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="세션 확인 중" />
  if (!user) return <Navigate to={admin ? '/admin/login' : '/login'} replace state={{ from: location }} />
  if (admin && !isAdmin) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      {/* 모든 페이지는 글로벌 헤더/푸터 공통 레이아웃 안에서 렌더링, 최초 진입은 메인(/) */}
      <Route element={<Layout />}>
        <Route index element={<Main />} />
        <Route path="shop" element={<Shop />} />
        <Route path="products/:id" element={<ProductDetail />} />
        <Route path="trends" element={<Trends />} />
        <Route path="login" element={<Login />} />
        <Route path="admin/login" element={<AdminLogin />} />
        <Route path="oauth/callback" element={<OAuthCallback />} />
        <Route path="terms" element={<Terms />} />
        <Route path="privacy" element={<Privacy />} />
        <Route path="support" element={<Support />} />
        <Route path="mypage" element={<RequireAuth><MyPage /></RequireAuth>} />
        <Route path="settings" element={<Navigate to="/mypage?tab=notify" replace />} />
        <Route path="admin" element={<RequireAuth admin><AdminLayout /></RequireAuth>}>
          <Route index element={<AdminDashboard />} />
          <Route path="sourcing" element={<AdminSourcing />} />
          <Route path="orders" element={<AdminOrders />} />
          <Route path="rpa" element={<AdminRpa />} />
          <Route path="suppliers" element={<AdminSuppliers />} />
          <Route path="members" element={<AdminMembers />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
