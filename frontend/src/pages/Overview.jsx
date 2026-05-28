import { useState, useEffect, useCallback } from 'react'
import { Users, Briefcase, Send, TrendingUp, Zap, Clock, Rocket, AlertCircle } from 'lucide-react'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { getDiscoveryStats, triggerDiscoveryRun } from '../api/discovery'
import { subscribeDiscoveryEvents } from '../api/events'
import { TalentAgentApiError } from '../api/client'
import { log } from '../lib/logger'

// Agent display configuration - statuses are updated dynamically via SSE
const agentConfig = [
  { key: 'discovery', name: 'Discovery Engine' },
  { key: 'application', name: 'Application Engine' },
  { key: 'contact', name: 'Contact Finder' },
  { key: 'outreach', name: 'Outreach Composer' },
]

export default function Overview() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [runTriggered, setRunTriggered] = useState(false)
  const [triggerLoading, setTriggerLoading] = useState(false)
  const [error, setError] = useState(null)
  const [agentStatuses, setAgentStatuses] = useState({
    discovery: 'idle',
    application: 'idle',
    contact: 'idle',
    outreach: 'idle',
  })

  // Fetch discovery stats
  const fetchStats = useCallback(async () => {
    if (!user?.candidate_id) return
    try {
      const data = await getDiscoveryStats(user.candidate_id)
      setStats(data)
      setError(null)
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('overview.fetch_stats_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('overview.fetch_stats_error', { error: String(err) })
        setError('Failed to load discovery stats')
      }
    }
  }, [user?.candidate_id])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  // Subscribe to real-time discovery events
  useEffect(() => {
    if (!user?.candidate_id) return

    const unsubscribe = subscribeDiscoveryEvents(
      (event) => {
        log.info('overview.discovery_event', { event: event.event, candidateId: event.candidate_id })

        // Update agent status based on event
        switch (event.event) {
          case 'RUN_STARTED':
            setAgentStatuses(prev => ({ ...prev, discovery: 'running' }))
            break
          case 'RUN_COMPLETE':
          case 'DIGEST_READY':
            setAgentStatuses(prev => ({ ...prev, discovery: 'completed' }))
            // Refresh stats when run completes
            fetchStats()
            break
          case 'RUN_FAILED':
            setAgentStatuses(prev => ({ ...prev, discovery: 'failed' }))
            break
          default:
            // Keep running for intermediate events
            if (event.event.startsWith('CRAWL_') || event.event.endsWith('_BUILT') || event.event.endsWith('_LOADED')) {
              setAgentStatuses(prev => ({ ...prev, discovery: 'running' }))
            }
        }
      },
      {
        onError: () => {
          log.warn('overview.sse_connection_error')
        },
      }
    )

    return unsubscribe
  }, [user?.candidate_id, fetchStats])

  const handleTriggerRun = async () => {
    if (!user?.candidate_id) return
    setTriggerLoading(true)
    setError(null)
    try {
      await triggerDiscoveryRun(user.candidate_id, false)
      setRunTriggered(true)
      setAgentStatuses(prev => ({ ...prev, discovery: 'running' }))
      log.info('overview.discovery_run_triggered', { candidateId: user.candidate_id })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('overview.trigger_run_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('overview.trigger_run_error', { error: String(err) })
        setError('Failed to start discovery run')
      }
    } finally {
      setTriggerLoading(false)
    }
  }

  const displayStats = [
    { label: 'Active Candidates', value: '1', change: 0, icon: Users },
    { label: 'Roles Discovered', value: stats ? String(stats.total_discovered) : '0', change: 0, icon: Briefcase },
    { label: 'Applications Sent', value: '0', change: 0, icon: Send },
    { label: 'Discovery Runs', value: stats ? String(stats.total_runs) : '0', change: 0, icon: TrendingUp },
  ]

  // Map dynamic agent statuses
  const agents = agentConfig.map(a => ({ name: a.name, status: agentStatuses[a.key] }))

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--status-error)', padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle style={{ width: 18, height: 18, color: 'var(--status-error)', flexShrink: 0 }} />
          <p style={{ color: 'var(--status-error)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      {/* Welcome */}
      {user && (
        <div className="card-hover" style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: '32px 36px', marginBottom: 32 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24 }}>
            <div>
              <p className="t-label-gold" style={{ marginBottom: 8 }}>Welcome back</p>
              <h2 className="t-serif" style={{ fontSize: 24, marginBottom: 8 }}>{user.name || 'there'}</h2>
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
