import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Landing from './pages/Landing'
import Login from './pages/Login'
import VerifyAuth from './pages/VerifyAuth'
import Onboarding from './pages/Onboarding'
import DashboardLayout from './layouts/DashboardLayout'
import Overview from './pages/Overview'
import Candidates from './pages/Candidates'
import Pipeline from './pages/Pipeline'
import ReviewQueue from './pages/ReviewQueue'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

function ProtectedRoute({ requireOnboarded = false }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--black)' }}>
      <div className="spinner" />
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  if (requireOnboarded && !user.is_onboarded) return <Navigate to="/onboarding" replace />
  return <Outlet />
}

function PublicRoute() {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--black)' }}>
      <div className="spinner" />
    </div>
  )
  if (user) return <Navigate to={user.is_onboarded ? '/dashboard' : '/onboarding'} replace />
  return <Outlet />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<Login />} />
          </Route>
          <Route path="/auth/verify" element={<VerifyAuth />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/onboarding" element={<Onboarding />} />
          </Route>
          <Route element={<ProtectedRoute requireOnboarded />}>
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Overview />} />
              <Route path="candidates" element={<Candidates />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="review" element={<ReviewQueue />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
