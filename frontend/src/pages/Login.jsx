import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { requestMagicLink, verifyMagicLink } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { routes } from '../lib/routes'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState('')
  const [magicLink, setMagicLink] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleRequestLink = async (e) => {
    e.preventDefault()
    if (!email) return
    setLoading(true)
    setError('')
    try {
      const res = await requestMagicLink(email)
      setStep('link-sent')
      if (res.magic_link) setMagicLink(res)
    } catch (err) {
      setError(err.message || 'Failed to send login link')
    } finally {
      setLoading(false)
    }
  }

  const handleDevLogin = async () => {
    if (!magicLink?.token) return
    setStep('verifying')
    setLoading(true)
    try {
      const res = await verifyMagicLink(magicLink.token)
      login(res.access_token, { id: res.user_id, email: res.email, is_onboarded: res.is_onboarded })
      navigate(res.is_onboarded ? routes.overview : routes.onboarding)
    } catch (err) {
      setError(err.message || 'Failed to verify link')
      setStep('email')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', position: 'relative', background: 'var(--black)' }}>
      {/* Subtle gold glow */}
      <div style={{ position: 'absolute', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%)', top: '40%', left: '55%', transform: 'translate(-50%,-50%)', pointerEvents: 'none' }} />

      <div className="fade-in" style={{ width: '100%', maxWidth: 440, position: 'relative', zIndex: 1 }}>
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <a href="/" className="t-label-gold" style={{ textDecoration: 'none', display: 'inline-block', marginBottom: 40 }}>
            SY / Talent Agent
          </a>
          <h1 className="t-serif" style={{ fontSize: 'clamp(36px, 5vw, 48px)', marginBottom: 12 }}>
            Welcome back.
          </h1>
          <p className="t-label">No passwords — just vibes</p>
        </div>

        {/* Card */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '40px 36px' }}>

          {step === 'email' && (
            <form onSubmit={handleRequestLink}>
              <div style={{ marginBottom: 24 }}>
                <label className="input-label">Email address</label>
                <input
                  type="email"
                  required
                  autoFocus
                  placeholder="spy@seanyoung.biz"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                />
              </div>

              {error && <p style={{ color: 'var(--rose)', fontSize: 13, marginBottom: 16 }}>{error}</p>}

              <button type="submit" disabled={loading || !email} className="btn-primary" style={{ width: '100%' }}>
                {loading ? 'Sending...' : 'Send magic link →'}
              </button>
            </form>
          )}

          {step === 'link-sent' && (
            <div className="fade-in" style={{ textAlign: 'center' }}>
              <div style={{ width: 56, height: 56, border: '1px solid var(--gold)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="1.5" style={{ width: 22, height: 22 }}>
                  <rect x="2" y="4" width="20" height="16" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </div>

              <h2 className="t-serif" style={{ fontSize: 22, marginBottom: 8 }}>Check your email</h2>
              <p className="t-body" style={{ marginBottom: 28 }}>
                We sent a login link to <span style={{ color: 'var(--white)' }}>{email}</span>
              </p>

              {magicLink && (
                <div style={{ border: '1px solid rgba(201,168,76,0.25)', padding: '20px 24px', marginBottom: 24, background: 'rgba(201,168,76,0.02)' }}>
                  <div className="t-label-gold" style={{ marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--gold)', display: 'inline-block' }} />
                    Dev Mode
                  </div>
                  <button onClick={handleDevLogin} disabled={loading} className="btn-primary" style={{ width: '100%' }}>
                    {loading ? 'Verifying...' : 'Log in now →'}
                  </button>
                </div>
              )}

              <button
                onClick={() => { setStep('email'); setError(''); setMagicLink(null) }}
                className="t-label"
                style={{ background: 'none', border: 'none', cursor: 'pointer', transition: 'color 0.2s' }}
              >
                Use a different email
              </button>
            </div>
          )}

          {step === 'verifying' && (
            <div className="fade-in" style={{ textAlign: 'center', padding: '24px 0' }}>
              <div className="spinner" style={{ margin: '0 auto 20px' }} />
              <p className="t-label">Verifying your link...</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: 48 }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.15em', color: 'rgba(244,241,235,0.15)' }}>
            VIBESPACE LLC · THE DOT CONNECTOR · MIAMI, FL
          </span>
        </div>
      </div>
    </div>
  )
}
