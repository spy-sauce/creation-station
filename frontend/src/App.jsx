import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { routes } from './lib/routes'
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

/**
 * Protected route wrapper.
 * Redirects to login if unauthenticated.
 * Optionally requires onboarding completion.
 */
function ProtectedRoute({ requireOnboarded = false }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
        <div className="spinner" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to={routes.login} replace />
  }

  if (requireOnboarded && !user.is_onboarded) {
    return <Navigate to={routes.onboarding} replace />
  }

  return <Outlet />
}

/**
 * Public route wrapper.
 * Redirects authenticated users to appropriate destination.
 */
function PublicRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
        <div className="spinner" />
      </div>
    )
  }

  if (user) {
    return <Navigate to={user.is_onboarded ? routes.overview : routes.onboarding} replace />
  }

  return <Outlet />
}

/**
 * Main application component.
 * Routes per NUTRIENTS.md §E route map.
 */
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public landing page */}
          <Route path={routes.landing} element={<Landing />} />

          {/* Auth routes — redirect authenticated users */}
          <Route element={<PublicRoute />}>
            <Route path={routes.login} element={<Login />} />
          </Route>

          {/* Magic link verification — no auth required */}
          <Route path={routes.verifyAuth} element={<VerifyAuth />} />

          {/* Onboarding — requires auth, no onboarding required */}
          <Route element={<ProtectedRoute />}>
            <Route path={routes.onboarding} element={<Onboarding />} />
          </Route>

          {/* Dashboard routes — requires auth + onboarding */}
          <Route element={<ProtectedRoute requireOnboarded />}>
            <Route element={<DashboardLayout />}>
              <Route path={routes.overview} element={<Overview />} />
              <Route path={routes.candidates} element={<Candidates />} />
              <Route path={routes.pipeline} element={<Pipeline />} />
              <Route path={routes.reviewQueue} element={<ReviewQueue />} />
              <Route path={routes.analytics} element={<Analytics />} />
              <Route path={routes.settings} element={<Settings />} />
            </Route>
          </Route>

          {/* Legacy redirect: /dashboard/* → new routes */}
          <Route path="/dashboard" element={<Navigate to={routes.overview} replace />} />
          <Route path="/dashboard/candidates" element={<Navigate to={routes.candidates} replace />} />
          <Route path="/dashboard/pipeline" element={<Navigate to={routes.pipeline} replace />} />
          <Route path="/dashboard/review" element={<Navigate to={routes.reviewQueue} replace />} />
          <Route path="/dashboard/analytics" element={<Navigate to={routes.analytics} replace />} />
          <Route path="/dashboard/settings" element={<Navigate to={routes.settings} replace />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to={routes.landing} replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
