import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadResume, saveProfile } from '../lib/api'
import { useAuth } from '../context/AuthContext'

/* ── Step dots ── */
function Steps({ current }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      {[0, 1, 2].map((i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 30, height: 30, borderRadius: '50%',
            border: `1px solid ${i <= current ? 'var(--gold)' : 'var(--border)'}`,
            background: i < current ? 'var(--gold)' : 'transparent',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--mono)', fontSize: 10,
            color: i < current ? 'var(--bg-primary)' : i === current ? 'var(--gold)' : 'var(--text-secondary)',
            transition: 'all 0.3s ease',
          }}>
            {i < current ? '✓' : i + 1}
          </div>
          {i < 2 && <div style={{ width: 24, height: 1, background: i < current ? 'var(--gold)' : 'var(--border)', transition: 'background 0.3s ease' }} />}
        </div>
      ))}
    </div>
  )
}

/* ── Step 1: Resume ── */
function ResumeStep({ onNext, resumeData, setResumeData }) {
  const fileRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (file) => {
    if (!file) return
    if (!file.type.includes('pdf')) { setError('PDF only'); return }
    if (file.size > 10 * 1024 * 1024) { setError('Max 10MB'); return }
    setUploading(true); setError('')
    try {
      const res = await uploadResume(file)
      setResumeData({ candidateId: res.candidate_id, textLength: res.text_length, preview: res.preview, fileName: file.name })
    } catch (err) { setError(err.message || 'Upload failed') }
    finally { setUploading(false) }
  }

  return (
    <div className="fade-in">
      <h2 className="t-serif" style={{ fontSize: 28, marginBottom: 8 }}>Upload your resume</h2>
      <p className="t-body" style={{ marginBottom: 32 }}>We'll extract your skills, experience, and context to power your AI talent agent.</p>

      {!resumeData ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
          onClick={() => fileRef.current?.click()}
          style={{
            border: `1px dashed ${dragging ? 'var(--gold)' : 'rgba(255,255,255,0.14)'}`,
            padding: '64px 24px', textAlign: 'center', cursor: 'pointer',
            background: dragging ? 'rgba(201,168,76,0.03)' : 'transparent',
            transition: 'all 0.2s',
          }}
        >
          <input ref={fileRef} type="file" accept=".pdf" style={{ display: 'none' }} onChange={(e) => handleFile(e.target.files[0])} />
          {uploading ? (
            <><div className="spinner" style={{ margin: '0 auto 16px' }} /><p className="t-label">Parsing...</p></>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="1" style={{ width: 40, height: 40, margin: '0 auto 16px', opacity: 0.4 }}>
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <p style={{ color: 'var(--white)', fontWeight: 400, marginBottom: 4 }}>Drop your resume here</p>
              <p className="t-label">PDF only · Max 10MB</p>
            </>
          )}
        </div>
      ) : (
        <div className="fade-in" style={{ background: 'var(--off-black)', border: '1px solid rgba(201,168,76,0.2)', padding: '24px 28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2" style={{ width: 16, height: 16 }}><path d="M20 6 9 17l-5-5" /></svg>
            </div>
            <div>
              <p style={{ color: 'var(--white)', fontWeight: 400, fontSize: 14 }}>{resumeData.fileName}</p>
              <p className="t-label" style={{ marginTop: 2 }}>{resumeData.textLength.toLocaleString()} characters</p>
            </div>
          </div>
          <div style={{ background: 'var(--surface)', padding: 16, maxHeight: 120, overflow: 'auto' }}>
            <p style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{resumeData.preview}...</p>
          </div>
          <button onClick={() => setResumeData(null)} className="t-label" style={{ marginTop: 12, background: 'none', border: 'none', cursor: 'pointer' }}>
            Upload different file
          </button>
        </div>
      )}

      {error && <p style={{ color: 'var(--rose)', fontSize: 13, marginTop: 16 }}>{error}</p>}

      <button onClick={onNext} disabled={!resumeData} className="btn-primary" style={{ width: '100%', marginTop: 28 }}>
        Continue →
      </button>
    </div>
  )
}

/* ── Step 2: Profile ── */
function ProfileStep({ onSubmit, loading }) {
  const [form, setForm] = useState({
    name: '', linkedin_url: '', github_url: '', personal_context: '',
    target_locations: '', remote_preference: 'flexible', min_compensation: '',
    excluded_companies: '', excluded_industries: '',
  })
  const u = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({
      name: form.name,
      linkedin_url: form.linkedin_url || null,
      github_url: form.github_url || null,
      personal_context: form.personal_context || null,
      target_locations: form.target_locations ? form.target_locations.split(',').map(s => s.trim()).filter(Boolean) : null,
      remote_preference: form.remote_preference,
      min_compensation: form.min_compensation ? parseInt(form.min_compensation, 10) : null,
      excluded_companies: form.excluded_companies ? form.excluded_companies.split(',').map(s => s.trim()).filter(Boolean) : null,
      excluded_industries: form.excluded_industries ? form.excluded_industries.split(',').map(s => s.trim()).filter(Boolean) : null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="fade-in">
      <h2 className="t-serif" style={{ fontSize: 28, marginBottom: 8 }}>Complete your profile</h2>
      <p className="t-body" style={{ marginBottom: 32 }}>Tell us about yourself so your AI agent knows what to look for.</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div><label className="input-label">Full Name *</label><input type="text" required placeholder="Sean Young" value={form.name} onChange={(e) => u('name', e.target.value)} className="input" /></div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div><label className="input-label">LinkedIn</label><input type="url" placeholder="https://linkedin.com/in/..." value={form.linkedin_url} onChange={(e) => u('linkedin_url', e.target.value)} className="input" /></div>
          <div><label className="input-label">GitHub</label><input type="url" placeholder="https://github.com/..." value={form.github_url} onChange={(e) => u('github_url', e.target.value)} className="input" /></div>
        </div>

        <div><label className="input-label">Personal Context</label><textarea placeholder="What should your agent know beyond the resume?" value={form.personal_context} onChange={(e) => u('personal_context', e.target.value)} className="input" style={{ resize: 'vertical', minHeight: 100 }} /></div>
      </div>

      {/* Preferences */}
      <div style={{ borderTop: '1px solid var(--border)', marginTop: 32, paddingTop: 28 }}>
        <div className="t-label-gold" style={{ marginBottom: 20 }}>Preferences</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div><label className="input-label">Locations</label><input type="text" placeholder="Miami, NYC, Remote" value={form.target_locations} onChange={(e) => u('target_locations', e.target.value)} className="input" /></div>
            <div><label className="input-label">Remote Preference</label><select value={form.remote_preference} onChange={(e) => u('remote_preference', e.target.value)} className="input"><option value="remote_only">Remote Only</option><option value="flexible">Flexible / Hybrid</option><option value="on_site">On-Site</option></select></div>
          </div>
          <div><label className="input-label">Min Compensation (USD/yr)</label><input type="number" placeholder="150000" value={form.min_compensation} onChange={(e) => u('min_compensation', e.target.value)} className="input" /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div><label className="input-label">Excluded Companies</label><input type="text" placeholder="Company A, Company B" value={form.excluded_companies} onChange={(e) => u('excluded_companies', e.target.value)} className="input" /></div>
            <div><label className="input-label">Excluded Industries</label><input type="text" placeholder="Gambling, Defense" value={form.excluded_industries} onChange={(e) => u('excluded_industries', e.target.value)} className="input" /></div>
          </div>
        </div>
      </div>

      <button type="submit" disabled={loading || !form.name} className="btn-primary" style={{ width: '100%', marginTop: 28 }}>
        {loading ? 'Saving...' : 'Launch my agent →'}
      </button>
    </form>
  )
}

/* ── Step 3: Success ── */
function SuccessStep() {
  const navigate = useNavigate()
  return (
    <div className="fade-in" style={{ textAlign: 'center', padding: '32px 0' }}>
      <div style={{ width: 64, height: 64, borderRadius: '50%', border: '1px solid var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 28px' }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="1.5" style={{ width: 28, height: 28 }}><path d="M20 6 9 17l-5-5" /></svg>
      </div>
      <h2 className="t-serif" style={{ fontSize: 28, marginBottom: 12 }}>You're all set, Space Cowboy.</h2>
      <p className="t-body" style={{ marginBottom: 36 }}>Your AI talent agent is ready. Head to the dashboard to launch your first discovery run.</p>
      <button onClick={() => navigate('/dashboard')} className="btn-primary">Go to dashboard →</button>
    </div>
  )
}

/* ── Main ── */
export default function Onboarding() {
  const { refreshUser } = useAuth()
  const [step, setStep] = useState(0)
  const [resumeData, setResumeData] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleProfileSubmit = async (profile) => {
    setSaving(true); setError('')
    try { await saveProfile(profile); await refreshUser(); setStep(2) }
    catch (err) { setError(err.message || 'Failed to save') }
    finally { setSaving(false) }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', background: 'var(--black)', position: 'relative' }}>
      <div style={{ position: 'absolute', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, rgba(201,168,76,0.06) 0%, transparent 70%)', top: '-10%', left: '30%', pointerEvents: 'none' }} />

      <div style={{ width: '100%', maxWidth: 520, position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 36 }}>
          <span className="t-label-gold">Setup</span>
          <Steps current={step} />
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '40px 36px' }}>
          {error && <div style={{ background: 'rgba(251,113,133,0.04)', border: '1px solid rgba(251,113,133,0.2)', padding: '12px 16px', marginBottom: 20 }}><p style={{ color: 'var(--rose)', fontSize: 13 }}>{error}</p></div>}
          {step === 0 && <ResumeStep onNext={() => setStep(1)} resumeData={resumeData} setResumeData={setResumeData} />}
          {step === 1 && <ProfileStep onSubmit={handleProfileSubmit} loading={saving} />}
          {step === 2 && <SuccessStep />}
        </div>
      </div>
    </div>
  )
}
