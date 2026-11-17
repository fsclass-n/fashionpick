import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import Login from './pages/Login'
import OAuthCallback from './pages/OAuthCallback'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Trends = lazy(() => import('./pages/Trends'))
const Sourcing = lazy(() => import('./pages/Sourcing'))
const Orders = lazy(() => import('./pages/Orders'))
const Admin = lazy(() => import('./pages/Admin'))
const Settings = lazy(() => import('./pages/Settings'))
const NotFound = lazy(() => import('./pages/NotFound'))

function RequireAuth({ children, admin }) {
  const { user, loading, isAdmin } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="세션 확인 중" />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (admin && !isAdmin) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Dashboard />} />
          <Route path="trends" element={<Trends />} />
          <Route path="sourcing" element={<Sourcing />} />
          <Route path="orders" element={<Orders />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<RequireAuth admin><Admin /></RequireAuth>} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
