import { useNavigate } from 'react-router-dom'
import { routes } from '../lib/routes'

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div style={{ background: 'var(--black)' }}>
      {/* Nav */}
      <nav className="ta-nav">
        <a href="#" className="ta-nav-logo">Talent Agent</a>
        <div className="ta-nav-links" style={{ listStyle: 'none' }}>
          <a href="#features" className="ta-nav-link">Features</a>
          <a href="#how" className="ta-nav-link">Process</a>
          <a href={routes.login} className="ta-nav-link" style={{ color: 'var(--gold)' }}>Enter</a>
        </div>
      </nav>

      {/* Hero */}
      <section className="spotlight" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '140px 60px 80px', position: 'relative', overflow: 'hidden' }}>
        {/* Folio — top-right registration mark */}
        <div className="folio pulse-gold">
          <span>Vol. I · No. 01 · MMXXVI</span>
        </div>

        {/* Gold halo behind headline */}
        <div style={{ position: 'absolute', width: 720, height: 720, borderRadius: '50%', background: 'radial-gradient(circle, rgba(201,162,39,0.14) 0%, rgba(201,162,39,0.02) 45%, transparent 70%)', top: '42%', left: '62%', transform: 'translate(-50%,-50%)', pointerEvents: 'none', filter: 'blur(8px)' }} />

        <p className="rise rise-1" style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.36em', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 36, display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ display: 'inline-block', width: 28, height: 1, background: 'var(--gold)' }} />
          Autonomous Talent Operations
        </p>

        <h1 className="rise rise-2" style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(52px, 8vw, 116px)', lineHeight: 0.98, fontWeight: 700, maxWidth: 960, letterSpacing: '-0.025em' }}>
          Your AI<br/>
          <span className="gold-italic" style={{ fontSize: '1.02em' }}>talent agent</span><br/>
          never sleeps.
        </h1>

        <p className="rise rise-3" style={{ fontSize: 18, color: 'var(--text-secondary)', maxWidth: 520, marginTop: 40, lineHeight: 1.75, fontWeight: 300 }}>
          Discovers opportunities, tailors every application, and manages your entire pipeline — so you close placements, not paperwork.
        </p>

        <div className="rise rise-4" style={{ display: 'flex', gap: 20, marginTop: 56, flexWrap: 'wrap', alignItems: 'center' }}>
          <button onClick={() => navigate(routes.login)} className="btn-primary">Get started →</button>
          <a href="#how" className="btn-ghost">See how it works</a>
        </div>

        {/* Bottom-edge scroll cue */}
        <div className="rise rise-5" style={{ position: 'absolute', bottom: 40, left: 60, fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.36em', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 14 }}>
          <span style={{ display: 'inline-block', width: 1, height: 32, background: 'var(--gold)', opacity: 0.6 }} />
          Scroll · The agent waits
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

      {/* Manifesto + Stats */}
      <section style={{ padding: '140px 60px 120px', position: 'relative' }}>
        <div className="rule-with-type"><span>§ I · Platform</span></div>

        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 96, alignItems: 'start' }}>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(36px, 4.6vw, 64px)', lineHeight: 1.06, fontWeight: 400, letterSpacing: '-0.02em' }}>
            24/7 autonomous<br />talent pipeline<br />
            <strong style={{ fontWeight: 700, fontStyle: 'italic' }}>that works.</strong>
          </h2>

          <p className="dropcap" style={{ fontSize: 17, color: 'var(--text-secondary)', lineHeight: 1.85, fontWeight: 300, maxWidth: 520 }}>
            Talent Agent is your AI-powered recruiting system. It crawls thousands of sources daily, scores every role across multiple dimensions, tailors resumes, researches companies, finds hiring managers, and composes personalized outreach — all on autopilot. You review and approve. It handles the rest.
          </p>
        </div>

        {/* Pull quote */}
        <blockquote className="pull-quote" style={{ margin: '80px auto 0', maxWidth: 820 }}>
          "The best agents don't replace the recruiter — they buy back the hours that should have been spent connecting with humans."
          <cite>— The operator's principle</cite>
        </blockquote>

        {/* Stats — large italic figure numbers */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 0, marginTop: 100, borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
          {[
            { num: '24', sup: '/ 7', label: 'Autonomous pipeline' },
            { num: '10', sup: '×', label: 'Faster applications' },
            { num: '500', sup: '+', label: 'Candidates per agency' },
          ].map((s, i) => (
            <div key={s.label} style={{ padding: '44px 36px', borderLeft: i === 0 ? 'none' : '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <span className="fig-num">{s.num}<sup>{s.sup}</sup></span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.3em', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                {s.label}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ padding: '140px 60px', background: 'var(--bg-secondary)', position: 'relative' }}>
        <div className="rule-with-type"><span>§ II · Capabilities</span></div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'end', marginBottom: 72, gap: 48 }}>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(40px, 5.2vw, 76px)', fontWeight: 700, lineHeight: 1.0, letterSpacing: '-0.025em' }}>
            What it does<br/><span className="gold-italic">for you.</span>
          </h2>
          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.3em', textTransform: 'uppercase', color: 'var(--text-muted)', maxWidth: 200, lineHeight: 1.9, textAlign: 'right' }}>
            Six concentrated functions<br/>One unattended loop
          </p>
        </div>

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
      <section id="how" style={{ padding: '140px 60px', position: 'relative' }}>
        <div className="rule-with-type"><span>§ III · Process</span></div>
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

      {/* CTA — colophon-style closer */}
      <section className="spotlight" style={{ padding: '160px 60px 140px', background: 'var(--bg-secondary)', position: 'relative', overflow: 'hidden', borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 880, margin: '0 auto', textAlign: 'center' }}>
          <div className="rule-with-type" style={{ justifyContent: 'center', marginBottom: 48 }}>
            <span>§ IV · Colophon</span>
          </div>
          <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'clamp(44px, 7vw, 88px)', fontWeight: 700, lineHeight: 1.0, letterSpacing: '-0.03em', marginBottom: 32 }}>
            Let's build something<br/><span className="gold-italic">real.</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 18, marginBottom: 64, fontWeight: 300, lineHeight: 1.7, maxWidth: 560, marginLeft: 'auto', marginRight: 'auto' }}>
            Your next hire is already out there. Let your AI agent find them — and bring the receipts.
          </p>
          <button onClick={() => navigate(routes.login)} className="btn-primary" style={{ fontSize: 14, padding: '20px 44px' }}>
            Get started →
          </button>
          <p style={{ marginTop: 56, fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '0.36em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Set in Playfair Display & DM Sans
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="ta-footer">
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, letterSpacing: '0.15em', color: 'var(--muted)' }}>
          Talent Agent © {new Date().getFullYear()}
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'rgba(244,241,235,0.2)', letterSpacing: '0.1em' }}>
          Discover · Tailor · Apply · Track
        </span>
      </footer>
    </div>
  )
}
