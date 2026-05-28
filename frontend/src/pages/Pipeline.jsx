import { useState, useEffect, useCallback } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'
import { useAuth } from '../context/AuthContext'
import { listApplications } from '../api/applications'
import { TalentAgentApiError } from '../api/client'
import { log } from '../lib/logger'

/**
 * Pipeline stage configuration.
 * Maps application status to display stage.
 */
const stageConfig = [
  { name: 'Discovered', status: 'discovered', statusMatch: ['QUEUED'] },
  { name: 'In Review', status: 'reviewing', statusMatch: ['AWAITING_REVIEW', 'PARSING', 'TAILORING', 'RESEARCHING', 'COMPOSING'] },
  { name: 'Approved', status: 'approved', statusMatch: ['APPROVED'] },
  { name: 'Applied', status: 'applied', statusMatch: ['SUBMITTED', 'SENT'] },
  { name: 'Tracking', status: 'tracking', statusMatch: ['TRACKED'] },
  { name: 'Rejected', status: 'rejected', statusMatch: ['REJECTED', 'FAILED', 'REQUIRES_MANUAL'] },
]

/**
 * Format relative time from ISO date string.
 */
function formatRelativeTime(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  const now = new Date()
  const diffMs = now - date
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return 'just now'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
  return `${Math.floor(diffDays / 30)}mo ago`
}

export default function Pipeline() {
  const { user } = useAuth()
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchApplications = useCallback(async () => {
    if (!user?.candidate_id) {
      setLoading(false)
      return
    }

    try {
      const { pipelines } = await listApplications({ candidate_id: user.candidate_id })
      setApplications(pipelines || [])
      setError(null)
      log.info('pipeline.fetch_success', { count: pipelines?.length || 0 })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('pipeline.fetch_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('pipeline.fetch_error', { error: String(err) })
        setError('Failed to load applications')
      }
    } finally {
      setLoading(false)
    }
  }, [user?.candidate_id])

  useEffect(() => {
    fetchApplications()
  }, [fetchApplications])

  // Group applications by stage
  const stages = stageConfig.map(stage => {
    const items = applications.filter(app => stage.statusMatch.includes(app.status))
    return {
      ...stage,
      count: items.length,
      items: items.map(app => ({
        id: app.id,
        role: app.parsed_jd?.seniority_level
          ? `${app.parsed_jd.seniority_level} Engineer`
          : 'Role',
        company: app.company_intel?.company_name || 'Company',
        match: app.parsed_jd ? 85 : 0, // Placeholder until we have scoring on pipelines
        time: formatRelativeTime(app.updated_at || app.created_at),
        status: app.status,
      })),
    }
  })

  if (loading) {
    return (
      <div className="fade-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <Loader2 style={{ width: 24, height: 24, color: 'var(--gold)', animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  return (
    <div className="fade-in">
      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--status-error)', padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle style={{ width: 18, height: 18, color: 'var(--status-error)', flexShrink: 0 }} />
          <p style={{ color: 'var(--status-error)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      <p className="t-body" style={{ marginBottom: 24 }}>Track applications across every stage of the pipeline.</p>

      {applications.length === 0 && !error ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>No applications yet.</p>
          <p className="t-label" style={{ marginTop: 8 }}>Approve jobs from the Review Queue to start your pipeline.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 16 }}>
          {stages.map((stage) => (
            <div key={stage.name} style={{ flexShrink: 0, width: 280 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, paddingLeft: 4 }}>
                <span className="t-label-gold">{stage.name}</span>
                <span className="tag">{stage.count}</span>
              </div>

              <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 12, minHeight: 200 }}>
                {stage.items.length === 0 ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100, color: 'var(--muted)', fontSize: 13 }}>
                    No items
                  </div>
                ) : (
                  stage.items.map((item) => (
                    <div key={item.id} className="card-hover" style={{ background: 'var(--surface)', border: '1px solid var(--border)', padding: '16px 18px', marginBottom: 8, cursor: 'pointer' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ color: 'var(--white)', fontSize: 13, fontWeight: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 150 }}>{item.role}</span>
                        {item.match > 0 && (
                          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 500, color: item.match >= 90 ? 'var(--gold)' : 'var(--muted)' }}>{item.match}%</span>
                        )}
                      </div>
                      <p className="t-label" style={{ marginBottom: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>@ {item.company}</p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <StatusBadge status={stage.status} />
                        <span className="t-label">{item.time}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
