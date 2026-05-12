import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div style={{ background: 'var(--black)' }}>
      {/* Nav */}
      <nav className="ta-nav">
        <a href="#" className="ta-nav-logo">SY / Talent Agent</a>
        <div className="ta-nav-links" style={{ listStyle: 'none' }}>
          <a href="#features" className="ta-nav-link">Features</a>
          <a href="#how" className="ta-nav-link">Process</a>
          <a href="/login" className="ta-nav-link" style={{ color: 'var(--gold)' }}>Enter</a>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '140px 60px 80px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', width: 600, height: 600, borderRadius: '50%', background: 'radial-gradient(circle, rgba(201,168,76,0.12) 0%, transparent 70%)', top: '50%', left: '60%', transform: 'translate(-50%,-50%)', pointerEvents: 'none' }} />

        <p className="fade-in" style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.3em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 32 }}>
          VibeSpace LLC · Miami, FL
        </p>

        <h1 className="fade-in-delay" style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(48px, 7vw, 96px)', lineHeight: 1.05, fontWeight: 700, maxWidth: 800 }}>
          Your AI<br/><em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>talent agent</em><br/>never sleeps.
        </h1>

        <p className="fade-in-delay" style={{ fontSize: 17, color: 'var(--muted)', maxWidth: 480, marginTop: 32, lineHeight: 1.8 }}>
          Discovers opportunities, tailors every application, and manages your entire pipeline — so you close placements, not paperwork.
        </p>

        <div className="fade-in-delay2" style={{ display: 'flex', gap: 20, marginTop: 52, flexWrap: 'wrap' }}>
          <button onClick={() => navigate('/login')} className="btn-primary">Get started →</button>
          <a href="#how" className="btn-ghost">See how it works</a>
        </div>
      </section>

      {/* Marquee */}
      <div style={{ borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: '18px 0', overflow: 'hidden', whiteSpace: 'nowrap', background: 'var(--surface)' }}>
        <div style={{ display: 'inline-block', animation: 'marquee 30s linear infinite' }}>
          {['Discovery Engine', 'Resume Tailoring', 'Company Research', 'Contact Finder', 'Outreach Composer', 'Auto-Apply', 'Pipeline Tracking', 'Placement Analytics',
            'Discovery Engine', 'Resume Tailoring', 'Company Research', 'Contact Finder', 'Outreach Composer', 'Auto-Apply', 'Pipeline Tracking', 'Placement Analytics'
          ].map((t, i) => (
            <span key={i}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--muted)', padding: '0 40px' }}>{t}</span>
              <span style={{ color: 'var(--gold)', padding: '0 8px' }}>·</span>
            </span>
          ))}
        </div>
        <style>{`@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>
      </div>

      {/* Stats */}
      <section style={{ padding: '120px 60px' }}>
        <div className="section-label">Platform</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'start' }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(32px, 4vw, 52px)', lineHeight: 1.15, fontWeight: 400 }}>
            24/7 autonomous<br />talent pipeline<br /><strong style={{ fontWeight: 700 }}>that works.</strong>
          </h2>
          <p style={{ fontSize: 16, color: 'var(--muted)', lineHeight: 1.9 }}>
            Talent Agent is your AI-powered recruiting system. It crawls thousands of sources daily, scores every role across multiple dimensions, tailors resumes, researches companies, finds hiring managers, and composes personalized outreach — all on autopilot. You review and approve. It handles the rest.
          </p>
        </div>

        <div className="grid-border" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginTop: 60 }}>
          {[
            { num: '24/7', label: 'Autonomous pipeline' },
            { num: '10x', label: 'Faster applications' },
            { num: '500+', label: 'Candidates per agency' },
          ].map((s) => (
            <div key={s.label} style={{ padding: '32px 28px' }}>
              <div className="stat-num">{s.num}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ padding: '120px 60px', background: 'var(--surface)' }}>
        <div className="section-label">Features</div>
        <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(36px, 4vw, 56px)', fontWeight: 700, lineHeight: 1.1, marginBottom: 60 }}>
          What it does<br/>for you.
        </h2>

        <div className="grid-border" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          {[
            { num: '01', name: 'AI Discovery Engine', desc: 'Reverse-engineers the web daily to surface roles that match the whole person — skills, philosophy, ambitions — not just a resume title.', tags: ['Playwright', 'Claude', 'Scoring'] },
            { num: '02', name: 'Autonomous Applications', desc: 'Parses JDs, tailors resumes, researches companies, finds hiring managers, composes personalized outreach. Automatically.', tags: ['Resume', 'Outreach', 'Forms'] },
            { num: '03', name: 'Human-in-the-Loop', desc: 'Nothing sends without approval. Every tailored resume, outreach email, and form submission lands in your review queue first.', tags: ['Review', 'Approve', 'Control'] },
            { num: '04', name: 'Multi-Candidate Pipeline', desc: 'Run 50 to 500 candidates simultaneously. Each gets their own isolated AI agent pipeline with real-time tracking.', tags: ['Scale', 'Parallel', 'Pipeline'] },
            { num: '05', name: 'Placement Analytics', desc: 'Track every touchpoint from discovery to placement. Measure ROI per candidate, time-to-place, and conversion rates.', tags: ['Metrics', 'ROI', 'Reports'] },
            { num: '06', name: 'White-Label Ready', desc: "Your brand, your dashboard. Offer the platform under your agency's identity with custom branding and domains.", tags: ['Brand', 'Custom', 'SaaS'] },
          ].map((f) => (
            <div key={f.num} className="card-hover" style={{ padding: '48px 36px', transition: 'background 0.25s' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--gold)', letterSpacing: '0.2em', marginBottom: 28 }}>{f.num}</div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 700, marginBottom: 16, lineHeight: 1.2, color: 'var(--white)' }}>{f.name}</div>
              <p style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.8 }}>{f.desc}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 28 }}>
                {f.tags.map((t) => <span key={t} className="tag">{t}</span>)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" style={{ padding: '120px 60px' }}>
        <div className="section-label">Process</div>
        <div style={{ maxWidth: 680 }}>
          {[
            { title: 'Onboard candidates', desc: 'Upload resumes and context. AI builds multi-dimensional identity profiles — skills, projects, philosophy, ambitions.' },
            { title: 'AI discovers opportunities', desc: 'The engine crawls thousands of sources daily — Greenhouse, Lever, LinkedIn, company career pages — and scores each role.' },
            { title: 'You review & approve', desc: "Ranked daily digest. Approve roles to trigger the Application Engine. Skip what doesn't fit. You stay in control." },
            { title: 'Autonomous applications', desc: 'For each approved role, AI tailors the resume, researches the company, finds the hiring manager, writes outreach, fills the form.' },
            { title: 'Track & place', desc: "Monitor every candidate's pipeline in real-time. From first outreach to interview to placement — full visibility." },
          ].map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: 24, paddingTop: 28, paddingBottom: 28, borderBottom: '1px solid var(--border)', alignItems: 'baseline' }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--gold)', letterSpacing: '0.2em', flexShrink: 0, width: 32 }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <div>
                <h3 style={{ fontFamily: 'var(--serif)', fontSize: 20, fontWeight: 700, marginBottom: 8, lineHeight: 1.3, color: 'var(--white)' }}>
                  {step.title}
                </h3>
                <p style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.8 }}>{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '120px 60px', background: 'var(--surface)' }}>
        <div style={{ maxWidth: 720, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(40px, 6vw, 72px)', fontWeight: 700, lineHeight: 1.1, marginBottom: 24 }}>
            Let's build something<br/><em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>real.</em>
          </h2>
          <p style={{ color: 'var(--muted)', fontSize: 16, marginBottom: 52 }}>
            Your next hire is already out there. Let your AI agent find them.
          </p>
          <button onClick={() => navigate('/login')} className="btn-primary">Get started →</button>
        </div>
      </section>

      {/* Footer */}
      <footer className="ta-footer">
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.15em', color: 'var(--muted)' }}>
          Sean Young · VibeSpace LLC © {new Date().getFullYear()}
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'rgba(244,241,235,0.2)', letterSpacing: '0.1em' }}>
          Miami, FL · Built different.
        </span>
      </footer>
    </div>
  )
}
