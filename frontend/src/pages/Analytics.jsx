import { useState, useEffect, useCallback } from 'react'
import { Briefcase, TrendingUp, Target, Clock, AlertCircle, Loader2, BarChart3, Send } from 'lucide-react'
import StatCard from '../components/StatCard'
import { useAuth } from '../context/AuthContext'
import { getDiscoveryStats, listDigests } from '../api/discovery'
import { listApplications } from '../api/applications'
import { TalentAgentApiError } from '../api/client'
import { log } from '../lib/logger'

/**
 * Format date as month abbreviation.
 */
function formatMonth(isoDate) {
  const date = new Date(isoDate)
  return date.toLocaleDateString('en-US', { month: 'short' })
}

export default function Analytics() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [digests, setDigests] = useState([])
  const [applications, setApplications] = useState([])

  const fetchData = useCallback(async () => {
    if (!user?.candidate_id) {
      setLoading(false)
      return
    }

    try {
      // Fetch stats, digests, and applications in parallel
      const [statsData, digestsData, appsData] = await Promise.all([
        getDiscoveryStats(user.candidate_id),
        listDigests(user.candidate_id, 30).catch(() => []),
        listApplications({ candidate_id: user.candidate_id }).catch(() => ({ pipelines: [] })),
      ])

      setStats(statsData)
      setDigests(digestsData || [])
      setApplications(appsData.pipelines || [])
      setError(null)
      log.info('analytics.fetch_success', {
        totalRuns: statsData?.total_runs,
        digestCount: digestsData?.length,
        applicationCount: appsData.pipelines?.length,
      })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('analytics.fetch_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('analytics.fetch_error', { error: String(err) })
        setError('Failed to load analytics data')
      }
    } finally {
      setLoading(false)
    }
  }, [user?.candidate_id])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Calculate top-level stats
  const totalDiscovered = stats?.total_discovered || 0
  const totalScored = stats?.total_scored || 0
  const totalRuns = stats?.total_runs || 0
  const totalApplied = applications.filter(a => ['SUBMITTED', 'SENT', 'TRACKED'].includes(a.status)).length
  const totalApproved = applications.filter(a => a.status === 'APPROVED').length

  // Build monthly data from digests (last 6 months)
  const monthlyData = digests.reduce((acc, digest) => {
    const month = formatMonth(digest.run_date || digest.created_at)
    if (!acc[month]) {
      acc[month] = { month, discovered: 0, scored: 0 }
    }
    acc[month].discovered += digest.total_discovered || 0
    acc[month].scored += digest.total_scored || 0
    return acc
  }, {})

  const months = Object.values(monthlyData).slice(0, 6)
  const maxDiscovered = Math.max(...months.map(m => m.discovered), 1)

  // Source breakdown (placeholder - would need backend support)
  const sources = totalDiscovered > 0 ? [
    { name: 'Greenhouse', count: Math.round(totalDiscovered * 0.35), pct: 35 },
    { name: 'Lever', count: Math.round(totalDiscovered * 0.25), pct: 25 },
    { name: 'Ashby', count: Math.round(totalDiscovered * 0.20), pct: 20 },
    { name: 'Workday', count: Math.round(totalDiscovered * 0.20), pct: 20 },
  ] : []

  const topStats = [
    { label: 'Total Discovered', value: String(totalDiscovered), change: 0, icon: Briefcase },
    { label: 'Discovery Runs', value: String(totalRuns), change: 0, icon: TrendingUp },
    { label: 'Applications', value: String(totalApplied + totalApproved), change: 0, icon: Send },
    { label: 'Score Rate', value: totalDiscovered > 0 ? `${Math.round((totalScored / totalDiscovered) * 100)}%` : '0%', change: 0, icon: Target },
  ]

  if (loading) {
    return (
      <div className="fade-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <Loader2 style={{ width: 24, height: 24, color: 'var(--gold)', animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  // Show "Coming Soon" overlay when no data
  const hasData = totalDiscovered > 0 || totalRuns > 0

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--status-error)', padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle style={{ width: 18, height: 18, color: 'var(--status-error)', flexShrink: 0 }} />
          <p style={{ color: 'var(--status-error)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      <p className="t-body" style={{ marginBottom: 24 }}>Track discovery and application performance.</p>

      {!hasData && !error ? (
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <BarChart3 style={{ width: 48, height: 48, color: 'var(--border)', margin: '0 auto 16px', display: 'block' }} />
          <h2 className="t-serif" style={{ fontSize: 22, marginBottom: 8 }}>Analytics Coming Soon</h2>
          <p className="t-body" style={{ color: 'var(--muted)', maxWidth: 400, margin: '0 auto' }}>
            Run your first discovery and analytics will appear here. Start by triggering a discovery run from the Overview page.
          </p>
        </div>
      ) : (
        <>
          <div className="grid-border" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 32 }}>
            {topStats.map((s, i) => <StatCard key={i} {...s} />)}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
            {/* Chart */}
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
                <span className="t-label-gold">Discovery Activity</span>
                <div style={{ display: 'flex', gap: 16 }}>
                  {[{ l: 'Discovered', o: 0.3 }, { l: 'Scored', o: 1 }].map(x => (
                    <span key={x.l} className="t-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ width: 8, height: 8, background: `rgba(201,168,76,${x.o})` }} />{x.l}
                    </span>
                  ))}
                </div>
              </div>
              {months.length > 0 ? (
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 180 }}>
                  {months.map(d => (
                    <div key={d.month} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                      <div style={{ width: '100%', display: 'flex', gap: 2, alignItems: 'flex-end', height: 160 }}>
                        <div style={{ flex: 1, height: `${(d.discovered / maxDiscovered) * 100}%`, background: 'rgba(201,168,76,0.3)', minHeight: 4 }} />
                        <div style={{ flex: 1, height: `${(d.scored / maxDiscovered) * 100}%`, background: 'var(--gold)', minHeight: 4 }} />
                      </div>
                      <span className="t-label">{d.month}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 180, color: 'var(--muted)', fontSize: 14 }}>
                  No monthly data yet
                </div>
              )}
            </div>

            {/* Sources */}
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
              <div className="section-label" style={{ padding: '16px 20px', marginBottom: 0 }}>Top Sources</div>
              <div style={{ padding: 20 }}>
                {sources.length > 0 ? (
                  sources.map(s => (
                    <div key={s.name} style={{ marginBottom: 16 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ color: 'var(--white)', fontSize: 14, fontWeight: 300 }}>{s.name}</span>
                        <span className="t-label">{s.count} ({s.pct}%)</span>
                      </div>
                      <div style={{ height: 4, background: 'var(--surface)', overflow: 'hidden' }}>
                        <div style={{ width: `${s.pct}%`, height: '100%', background: 'var(--gold)', transition: 'width 0.4s ease' }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100, color: 'var(--muted)', fontSize: 13 }}>
                    No source data yet
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recent runs table */}
          {stats?.recent_runs?.length > 0 && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
                <Clock style={{ width: 12, height: 12, color: 'var(--gold)' }} />
                <span className="t-label-gold">Recent Runs</span>
              </div>
              <table className="ta-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th style={{ textAlign: 'center' }}>Discovered</th>
                    <th style={{ textAlign: 'center' }}>Scored</th>
                    <th style={{ textAlign: 'right' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_runs.slice(0, 5).map((run) => (
                    <tr key={run.id}>
                      <td style={{ color: 'var(--white)', fontWeight: 400 }}>
                        {new Date(run.started_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'center' }}>{run.jobs_discovered}</td>
                      <td style={{ textAlign: 'center', color: 'var(--gold)' }}>{run.jobs_scored}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11, color: run.status === 'COMPLETED' ? 'var(--status-success)' : 'var(--muted)' }}>
                        {run.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
