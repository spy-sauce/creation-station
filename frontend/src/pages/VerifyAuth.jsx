import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { verifyMagicLink } from '../lib/api'
import { useAuth } from '../context/AuthContext'

export default function VerifyAuth() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const [error, setError] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) { setError('No token found in the link'); return }

    verifyMagicLink(token)
      .then((res) => {
        login(res.access_token, { id: res.user_id, email: res.email, is_onboarded: res.is_onboarded })
        navigate(res.is_onboarded ? '/dashboard' : '/onboarding', { replace: true })
      })
      .catch((err) => setError(err.message || 'Failed to verify link'))
  }, [searchParams, login, navigate])

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--black)', padding: 24 }}>
        <div className="fade-in" style={{ textAlign: 'center' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', border: '1px solid var(--rose)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="var(--rose)" strokeWidth="1.5" style={{ width: 22, height: 22 }}>
              <circle cx="12" cy="12" r="10" /><path d="m15 9-6 6M9 9l6 6" />
            </svg>
          </div>
          <h2 className="t-serif" style={{ fontSize: 20, marginBottom: 8 }}>Link expired or invalid</h2>
          <p className="t-body" style={{ marginBottom: 20 }}>{error}</p>
          <a href="/login" className="t-label-gold" style={{ textDecoration: 'none' }}>Request a new link</a>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--black)' }}>
      <div className="fade-in" style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ margin: '0 auto 20px' }} />
        <p className="t-label">Verifying your link...</p>
      </div>
    </div>
  )
}
