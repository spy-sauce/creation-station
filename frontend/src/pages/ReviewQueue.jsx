import { useState } from 'react'
import { Check, X, ExternalLink, Building2, MapPin, DollarSign, Sparkles } from 'lucide-react'

const mockQueue = [
  {
    id: 1, candidate: 'Marcus Chen', candidateTitle: 'Sr. ML Engineer',
    role: 'Sr. Machine Learning Engineer', company: 'Stripe', location: 'San Francisco, CA (Hybrid)',
    salary: '$220K–$290K', match: 94,
    matchBreakdown: { technical: 96, culture: 91, growth: 93, compensation: 95 },
    highlights: ['Direct ML infrastructure — matches 5yr PyTorch exp', 'Team size (8-12) aligns with preference', 'Ships to production weekly — fast iteration'],
    concerns: ['Hybrid — candidate prefers full remote'],
    source: 'Greenhouse', discovered: '2h ago', type: 'role',
  },
  {
    id: 2, candidate: 'Aisha Patel', candidateTitle: 'VP of Engineering',
    role: 'VP of Engineering', company: 'Figma', location: 'New York, NY (Remote OK)',
    salary: '$300K–$400K + equity', match: 91,
    matchBreakdown: { technical: 88, culture: 94, growth: 95, compensation: 87 },
    highlights: ['Reporting to CTO — direct strategic influence', 'Scaling 80→200 matches prior exp', 'Design-engineering culture overlap'],
    concerns: ['Equity-heavy comp'],
    source: 'Lever', discovered: '3h ago', type: 'role',
  },
  {
    id: 3, candidate: 'Jordan Williams', candidateTitle: 'Staff Software Engineer',
    role: 'Staff Engineer, Developer Platform', company: 'Vercel', location: 'Remote (US)',
    salary: '$240K–$310K', match: 88,
    matchBreakdown: { technical: 92, culture: 86, growth: 88, compensation: 85 },
    highlights: ['Developer tooling — built internal platform', 'Open source valued — 2K+ GitHub stars', 'Fully remote matches pref'],
    concerns: ['Smaller company — candidate prefers larger orgs'],
    source: 'Company website', discovered: '5h ago', type: 'outreach',
  },
]

function MatchBar({ label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span className="t-label" style={{ width: 80, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 4, background: 'var(--surface)', overflow: 'hidden' }}>
        <div style={{ width: `${value}%`, height: '100%', background: value >= 90 ? 'var(--gold)' : value >= 80 ? 'var(--gold-light)' : 'var(--muted)', transition: 'width 0.4s ease' }} />
      </div>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--white)', width: 32, textAlign: 'right' }}>{value}%</span>
    </div>
  )
}

export default function ReviewQueue() {
  const [queue, setQueue] = useState(mockQueue)
  const [expanded, setExpanded] = useState(queue[0]?.id || null)

  const remove = (id) => setQueue(q => q.filter(item => item.id !== id))

  if (queue.length === 0) {
    return (
      <div className="fade-in" style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center', paddingTop: 80 }}>
        <div style={{ width: 56, height: 56, borderRadius: '50%', border: '1px solid var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
          <Check style={{ width: 22, height: 22, color: 'var(--gold)' }} />
        </div>
        <h2 className="t-serif" style={{ fontSize: 22, marginBottom: 8 }}>All caught up</h2>
        <p className="t-body">No items pending review. The Discovery Engine will find more soon.</p>
      </div>
    )
  }

  return (
    <div className="fade-in" style={{ maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <p className="t-body">Review AI-discovered matches before applications are sent.</p>
        <span className="t-label-gold">{queue.length} pending</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {queue.map((item) => {
          const open = expanded === item.id
          return (
            <div key={item.id} className="card-hover" style={{ background: 'var(--off-black)', border: `1px solid ${open ? 'rgba(201,168,76,0.2)' : 'var(--border)'}`, transition: 'border-color 0.3s' }}>
              {/* Header */}
              <button onClick={() => setExpanded(open ? null : item.id)} style={{ width: '100%', textAlign: 'left', padding: '24px 28px', display: 'flex', alignItems: 'center', gap: 20, background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>
                <div style={{ width: 52, height: 52, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${item.match >= 90 ? 'var(--gold)' : 'var(--border)'}`, flexShrink: 0 }}>
                  <span style={{ fontFamily: 'var(--serif)', fontSize: 20, color: item.match >= 90 ? 'var(--gold)' : 'var(--white)' }}>{item.match}</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ color: 'var(--white)', fontSize: 15, fontWeight: 400 }}>{item.role}</span>
                    <span className="tag">{item.type}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, color: 'var(--muted)', fontSize: 13 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Building2 style={{ width: 12, height: 12 }} />{item.company}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><MapPin style={{ width: 12, height: 12 }} />{item.location}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><DollarSign style={{ width: 12, height: 12 }} />{item.salary}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ color: 'var(--white)', fontSize: 14, fontWeight: 400 }}>{item.candidate}</p>
                  <p className="t-label" style={{ marginTop: 2 }}>{item.candidateTitle}</p>
                </div>
              </button>

              {/* Expanded */}
              {open && (
                <div className="fade-in" style={{ padding: '24px 28px', borderTop: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                    <Sparkles style={{ width: 14, height: 14, color: 'var(--gold)' }} />
                    <span className="t-label-gold">Match Breakdown</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
                    {Object.entries(item.matchBreakdown).map(([k, v]) => <MatchBar key={k} label={k} value={v} />)}
                  </div>

                  <div style={{ marginBottom: 20 }}>
                    <span className="t-label" style={{ color: 'var(--emerald)', marginBottom: 10, display: 'block' }}>Why this matches</span>
                    {item.highlights.map((h, i) => (
                      <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, color: 'var(--muted)', fontSize: 14 }}>
                        <Check style={{ width: 14, height: 14, color: 'var(--emerald)', flexShrink: 0, marginTop: 3 }} />{h}
                      </div>
                    ))}
                  </div>

                  {item.concerns.length > 0 && (
                    <div style={{ marginBottom: 20 }}>
                      <span className="t-label" style={{ color: 'var(--amber)', marginBottom: 10, display: 'block' }}>Concerns</span>
                      {item.concerns.map((c, i) => (
                        <div key={i} style={{ display: 'flex', gap: 8, color: 'var(--muted)', fontSize: 14 }}>
                          <span style={{ color: 'var(--amber)', flexShrink: 0, width: 14, textAlign: 'center' }}>!</span>{c}
                        </div>
                      ))}
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', gap: 20 }}>
                      <span className="t-label">Source: {item.source}</span>
                      <span className="t-label">Found {item.discovered}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <a href="#" className="btn-ghost" style={{ padding: '10px 16px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <ExternalLink style={{ width: 12, height: 12 }} /> View
                      </a>
                      <button onClick={() => remove(item.id)} className="btn-ghost" style={{ padding: '10px 16px', fontSize: 10, borderColor: 'var(--rose)', color: 'var(--rose)', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <X style={{ width: 12, height: 12 }} /> Skip
                      </button>
                      <button onClick={() => remove(item.id)} className="btn-primary" style={{ padding: '10px 16px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Check style={{ width: 12, height: 12 }} /> Approve
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
