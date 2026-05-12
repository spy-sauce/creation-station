import StatusBadge from '../components/StatusBadge'

const stages = [
  { name: 'Discovered', status: 'discovered', count: 24, items: [
    { id: 1, candidate: 'Marcus Chen', role: 'Sr. ML Engineer', company: 'Stripe', match: 94, time: '2h ago' },
    { id: 2, candidate: 'Aisha Patel', role: 'VP Engineering', company: 'Figma', match: 91, time: '3h ago' },
    { id: 3, candidate: 'Lisa Zhang', role: 'Eng Manager', company: 'Linear', match: 89, time: '5h ago' },
  ]},
  { name: 'In Review', status: 'reviewing', count: 12, items: [
    { id: 5, candidate: 'Sarah Kim', role: 'Head of AI', company: 'Notion', match: 92, time: '1d ago' },
    { id: 6, candidate: 'Jordan Williams', role: 'Staff Engineer', company: 'Vercel', match: 88, time: '1d ago' },
  ]},
  { name: 'Approved', status: 'approved', count: 8, items: [
    { id: 8, candidate: 'Marcus Chen', role: 'AI Lead', company: 'Anthropic', match: 96, time: '2d ago' },
  ]},
  { name: 'Applied', status: 'applied', count: 15, items: [
    { id: 10, candidate: 'Aisha Patel', role: 'CTO', company: 'Resend', match: 93, time: '3d ago' },
    { id: 11, candidate: 'Lisa Zhang', role: 'Eng Director', company: 'Clerk', match: 86, time: '4d ago' },
  ]},
  { name: 'Interviewing', status: 'interviewing', count: 6, items: [
    { id: 13, candidate: 'Emily Nguyen', role: 'Staff Engineer', company: 'Planetscale', match: 91, time: '5d ago' },
  ]},
  { name: 'Placed', status: 'placed', count: 6, items: [
    { id: 15, candidate: 'Raj Krishnamurthy', role: 'CTO', company: 'Stealth Startup', match: 97, time: '2w ago' },
  ]},
]

export default function Pipeline() {
  return (
    <div className="fade-in">
      <p className="t-body" style={{ marginBottom: 24 }}>Track candidates across every stage of the placement lifecycle.</p>

      <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16 }}>
        {stages.map((stage) => (
          <div key={stage.name} style={{ flexShrink: 0, width: 280 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, paddingLeft: 4 }}>
              <span className="t-label-gold">{stage.name}</span>
              <span className="tag">{stage.count}</span>
            </div>

            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 12, minHeight: 200 }}>
              {stage.items.map((item) => (
                <div key={item.id} className="card-hover" style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '16px 18px', marginBottom: 8, cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ color: 'var(--white)', fontSize: 13, fontWeight: 400 }}>{item.candidate}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 500, color: item.match >= 90 ? 'var(--gold)' : 'var(--muted)' }}>{item.match}%</span>
                  </div>
                  <p className="t-label" style={{ marginBottom: 10 }}>{item.role} @ {item.company}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <StatusBadge status={stage.status} />
                    <span className="t-label">{item.time}</span>
                  </div>
                </div>
              ))}

              {stage.items.length < stage.count && (
                <button className="t-label" style={{ width: '100%', padding: '10px 0', background: 'none', border: 'none', cursor: 'pointer' }}>
                  + {stage.count - stage.items.length} more
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
