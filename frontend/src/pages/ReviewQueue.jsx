import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, X, ExternalLink, Building2, MapPin, DollarSign, Sparkles, AlertCircle, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { listApplications, approveApplication, rejectApplication } from '../api/applications'
import { TalentAgentApiError } from '../api/client'
import { log } from '../lib/logger'

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

/**
 * Match breakdown bar component.
 */
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
  const { user } = useAuth()
  const navigate = useNavigate()
  const [queue, setQueue] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [actionLoading, setActionLoading] = useState(null)

  const fetchQueue = useCallback(async () => {
    if (!user?.candidate_id) {
      setLoading(false)
      return
    }

    try {
      const { pipelines } = await listApplications({
        candidate_id: user.candidate_id,
        status: 'AWAITING_REVIEW',
      })
      setQueue(pipelines || [])
      setError(null)
      // Auto-expand first item
      if (pipelines?.length > 0 && !expanded) {
        setExpanded(pipelines[0].id)
      }
      log.info('review_queue.fetch_success', { count: pipelines?.length || 0 })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_queue.fetch_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_queue.fetch_error', { error: String(err) })
        setError('Failed to load review queue')
      }
    } finally {
      setLoading(false)
    }
  }, [user?.candidate_id, expanded])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  const handleApprove = async (pipelineId) => {
    setActionLoading(pipelineId)
    try {
      await approveApplication(pipelineId)
      setQueue(q => q.filter(item => item.id !== pipelineId))
      log.info('review_queue.approved', { pipelineId })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_queue.approve_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_queue.approve_error', { error: String(err) })
        setError('Failed to approve application')
      }
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async (pipelineId) => {
    setActionLoading(pipelineId)
    try {
      await rejectApplication(pipelineId)
      setQueue(q => q.filter(item => item.id !== pipelineId))
      log.info('review_queue.rejected', { pipelineId })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_queue.reject_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_queue.reject_error', { error: String(err) })
        setError('Failed to reject application')
      }
    } finally {
      setActionLoading(null)
    }
  }

  const handleViewDetail = (pipelineId) => {
    navigate(`/review-queue/${pipelineId}`)
  }

  if (loading) {
    return (
      <div className="fade-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <Loader2 style={{ width: 24, height: 24, color: 'var(--gold)', animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  if (queue.length === 0 && !error) {
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
      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--status-error)', padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle style={{ width: 18, height: 18, color: 'var(--status-error)', flexShrink: 0 }} />
          <p style={{ color: 'var(--status-error)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <p className="t-body">Review AI-discovered matches before applications are sent.</p>
        <span className="t-label-gold">{queue.length} pending</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {queue.map((pipeline) => {
          const open = expanded === pipeline.id
          const isLoading = actionLoading === pipeline.id

          // Extract display data from pipeline
          const jd = pipeline.parsed_jd
          const intel = pipeline.company_intel
          const contact = pipeline.contact
          const outreach = pipeline.outreach_email

          const role = jd?.seniority_level || 'Role'
          const company = intel?.company_name || 'Company'
          const location = 'Remote' // Would need to be in job data
          const salary = jd?.compensation_range || 'Not specified'
          const match = 85 // Placeholder - would need scoring

          // Build match breakdown from parsed JD if available
          const matchBreakdown = {
            technical: jd ? 88 : 0,
            culture: intel ? 85 : 0,
            growth: 80,
            compensation: jd?.compensation_range ? 90 : 50,
          }

          // Build highlights from parsed JD
          const highlights = []
          if (jd?.required_skills?.length > 0) {
            highlights.push(`Required skills: ${jd.required_skills.slice(0, 3).join(', ')}`)
          }
          if (intel?.engineering_culture) {
            highlights.push(`Culture: ${intel.engineering_culture.slice(0, 60)}...`)
          }
          if (jd?.tech_stack?.length > 0) {
            highlights.push(`Tech stack: ${jd.tech_stack.slice(0, 3).join(', ')}`)
          }

          // Build concerns from red flags
          const concerns = jd?.red_flags || []

          return (
            <div key={pipeline.id} className="card-hover" style={{ background: 'var(--off-black)', border: `1px solid ${open ? 'rgba(201,168,76,0.2)' : 'var(--border)'}`, transition: 'border-color 0.3s' }}>
              {/* Header */}
              <button onClick={() => setExpanded(open ? null : pipeline.id)} style={{ width: '100%', textAlign: 'left', padding: '24px 28px', display: 'flex', alignItems: 'center', gap: 20, background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>
                <div style={{ width: 52, height: 52, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${match >= 90 ? 'var(--gold)' : 'var(--border)'}`, flexShrink: 0 }}>
                  <span style={{ fontFamily: 'var(--serif)', fontSize: 20, color: match >= 90 ? 'var(--gold)' : 'var(--white)' }}>{match}</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ color: 'var(--white)', fontSize: 15, fontWeight: 400 }}>{role}</span>
                    <span className="tag">{outreach ? 'outreach' : 'role'}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, color: 'var(--muted)', fontSize: 13 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Building2 style={{ width: 12, height: 12 }} />{company}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><MapPin style={{ width: 12, height: 12 }} />{location}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><DollarSign style={{ width: 12, height: 12 }} />{salary}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ color: 'var(--white)', fontSize: 14, fontWeight: 400 }}>{user?.name || 'Candidate'}</p>
                  <p className="t-label" style={{ marginTop: 2 }}>{formatRelativeTime(pipeline.created_at)}</p>
                </div>
              </button>

              {/* Expanded */}
              {open && (
                <div className="fade-in" style={{ padding: '24px 28px', borderTop: '1px solid var(--border)' }}>
                  {/* Match breakdown */}
                  {jd && (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                        <Sparkles style={{ width: 14, height: 14, color: 'var(--gold)' }} />
                        <span className="t-label-gold">Match Breakdown</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
                        {Object.entries(matchBreakdown).map(([k, v]) => <MatchBar key={k} label={k} value={v} />)}
                      </div>
                    </>
                  )}

                  {/* Highlights */}
                  {highlights.length > 0 && (
                    <div style={{ marginBottom: 20 }}>
                      <span className="t-label" style={{ color: 'var(--emerald)', marginBottom: 10, display: 'block' }}>Why this matches</span>
                      {highlights.map((h, i) => (
                        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, color: 'var(--muted)', fontSize: 14 }}>
                          <Check style={{ width: 14, height: 14, color: 'var(--emerald)', flexShrink: 0, marginTop: 3 }} />{h}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Concerns */}
                  {concerns.length > 0 && (
                    <div style={{ marginBottom: 20 }}>
                      <span className="t-label" style={{ color: 'var(--amber)', marginBottom: 10, display: 'block' }}>Concerns</span>
                      {concerns.map((c, i) => (
                        <div key={i} style={{ display: 'flex', gap: 8, color: 'var(--muted)', fontSize: 14 }}>
                          <span style={{ color: 'var(--amber)', flexShrink: 0, width: 14, textAlign: 'center' }}>!</span>{c}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Contact info if available */}
                  {contact && (
                    <div style={{ marginBottom: 20, padding: 16, background: 'var(--surface)', border: '1px solid var(--border)' }}>
                      <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Contact Found</span>
                      <p style={{ color: 'var(--white)', fontSize: 14 }}>{contact.name} — {contact.title}</p>
                      <p className="t-label" style={{ marginTop: 4 }}>{contact.email}</p>
                    </div>
                  )}

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', gap: 20 }}>
                      <span className="t-label">Status: {pipeline.status}</span>
                      <span className="t-label">Created {formatRelativeTime(pipeline.created_at)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                      <button onClick={() => handleViewDetail(pipeline.id)} className="btn-ghost" style={{ padding: '10px 16px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <ExternalLink style={{ width: 12, height: 12 }} /> View
                      </button>
                      <button
                        onClick={() => handleReject(pipeline.id)}
                        disabled={isLoading}
                        className="btn-ghost"
                        style={{ padding: '10px 16px', fontSize: 10, borderColor: 'var(--rose)', color: 'var(--rose)', display: 'flex', alignItems: 'center', gap: 6, opacity: isLoading ? 0.5 : 1 }}
                      >
                        {isLoading ? <Loader2 style={{ width: 12, height: 12, animation: 'spin 1s linear infinite' }} /> : <X style={{ width: 12, height: 12 }} />} Skip
                      </button>
                      <button
                        onClick={() => handleApprove(pipeline.id)}
                        disabled={isLoading}
                        className="btn-primary"
                        style={{ padding: '10px 16px', fontSize: 10, display: 'flex', alignItems: 'center', gap: 6, opacity: isLoading ? 0.5 : 1 }}
                      >
                        {isLoading ? <Loader2 style={{ width: 12, height: 12, animation: 'spin 1s linear infinite' }} /> : <Check style={{ width: 12, height: 12 }} />} Approve
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
