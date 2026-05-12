import { useState, useEffect } from 'react'
import { Users, Briefcase, Send, TrendingUp, Zap, Clock, Rocket } from 'lucide-react'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { getDiscoveryStats, triggerDiscoveryRun } from '../lib/api'

const agents = [
  { name: 'Discovery Engine', status: 'idle' },
  { name: 'Application Engine', status: 'idle' },
  { name: 'Contact Finder', status: 'idle' },
  { name: 'Outreach Composer', status: 'idle' },
]

export default function Overview() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [runTriggered, setRunTriggered] = useState(false)
  const [triggerLoading, setTriggerLoading] = useState(false)

  useEffect(() => {
    if (user?.candidate_id) {
      getDiscoveryStats(user.candidate_id).then(setStats).catch(() => {})
    }
  }, [user?.candidate_id])

  const handleTriggerRun = async () => {
    if (!user?.candidate_id) return
    setTriggerLoading(true)
    try { await triggerDiscoveryRun(user.candidate_id, true); setRunTriggered(true) }
    catch {} finally { setTriggerLoading(false) }
  }

  const displayStats = [
    { label: 'Active Candidates', value: '1', change: 0, icon: Users },
    { label: 'Roles Discovered', value: stats ? String(stats.total_discovered) : '0', change: 0, icon: Briefcase },
    { label: 'Applications Sent', value: '0', change: 0, icon: Send },
    { label: 'Discovery Runs', value: stats ? String(stats.total_runs) : '0', change: 0, icon: TrendingUp },
  ]

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      {/* Welcome */}
      {user && (
        <div className="card-hover" style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: '32px 36px', marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24 }}>
            <div>
              <p className="t-label-gold" style={{ marginBottom: 8 }}>Welcome back</p>
              <h2 className="t-serif" style={{ fontSize: 24, marginBottom: 8 }}>{user.name || 'Space Cowboy'}</h2>
              <p className="t-body">
                {stats?.total_runs > 0
                  ? `Your agent has completed ${stats.total_runs} discovery runs and found ${stats.total_discovered} roles.`
                  : 'Your AI talent agent is ready. Trigger a discovery run to start finding opportunities.'}
              </p>
            </div>
            {user.candidate_id && !runTriggered && (
              <button onClick={handleTriggerRun} disabled={triggerLoading} className="btn-primary" style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Rocket style={{ width: 14, height: 14 }} />
                {triggerLoading ? 'Starting...' : 'Run Discovery'}
              </button>
            )}
            {runTriggered && (
              <span className="t-label-gold" style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2" style={{ width: 14, height: 14 }}><path d="M20 6 9 17l-5-5" /></svg>
                Discovery started
              </span>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid-border" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 32 }}>
        {displayStats.map((s, i) => <StatCard key={i} {...s} />)}
      </div>

      {/* Two columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
        {/* Activity */}
        <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
          <div className="section-label" style={{ padding: '16px 24px', marginBottom: 0 }}>Recent Activity</div>
          <div style={{ padding: '24px' }}>
            {stats?.recent_runs?.length > 0 ? (
              stats.recent_runs.map((run) => (
                <div key={run.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
                  <Briefcase style={{ width: 14, height: 14, color: 'var(--gold)', strokeWidth: 1.5, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <p style={{ color: 'var(--white)', fontSize: 14, fontWeight: 400 }}>Discovery run <span style={{ color: 'var(--muted)' }}>— {run.status}</span></p>
                    <p className="t-label" style={{ marginTop: 2 }}>{run.jobs_discovered} discovered · {run.jobs_scored} scored</p>
                  </div>
                  <span className="t-label">{new Date(run.started_at).toLocaleDateString()}</span>
                </div>
              ))
            ) : (
              <div style={{ textAlign: 'center', padding: '32px 0' }}>
                <Briefcase style={{ width: 28, height: 28, color: 'var(--border)', strokeWidth: 1, margin: '0 auto 12px', display: 'block' }} />
                <p style={{ color: 'var(--muted)', fontSize: 14, fontWeight: 300 }}>No activity yet</p>
                <p className="t-label" style={{ marginTop: 4 }}>Trigger a discovery run to start</p>
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Agents */}
          <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <Zap style={{ width: 12, height: 12, color: 'var(--gold)' }} />
              <span className="t-label-gold">Agents</span>
            </div>
            {agents.map((a, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', borderBottom: i < agents.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <span style={{ color: 'var(--white)', fontSize: 13, fontWeight: 300 }}>{a.name}</span>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>

          {/* Profile */}
          <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <Clock style={{ width: 12, height: 12, color: 'var(--gold)' }} />
              <span className="t-label-gold">Your Profile</span>
            </div>
            <div style={{ padding: 20 }}>
              {[
                { l: 'Email', v: user?.email },
                { l: 'Candidate', v: user?.candidate_id ? user.candidate_id.slice(0, 8) + '...' : '—', mono: true },
                { l: 'Last Run', v: stats?.last_run ? new Date(stats.last_run).toLocaleDateString() : 'Never' },
              ].map((r, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: i < 2 ? '1px solid var(--border)' : 'none' }}>
                  <span className="t-label">{r.l}</span>
                  <span style={{ color: 'var(--white)', fontSize: r.mono ? 11 : 14, fontWeight: 300, fontFamily: r.mono ? 'var(--mono)' : 'var(--sans)' }}>{r.v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
