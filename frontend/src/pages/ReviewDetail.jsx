import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Check,
  X,
  Building2,
  User,
  FileText,
  Mail,
  Globe,
  AlertCircle,
  Loader2,
  ExternalLink,
  Code,
  Briefcase,
  AlertTriangle,
} from 'lucide-react'
import { routes } from '../lib/routes'
import { getApplication, approveApplication, rejectApplication } from '../api/applications'
import { TalentAgentApiError } from '../api/client'
import { log } from '../lib/logger'

/**
 * Section header component.
 */
function SectionHeader(props) {
  const Icon = props.icon
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Icon style={{ width: 16, height: 16, color: 'var(--gold)' }} />
        <span className="t-label-gold">{props.title}</span>
      </div>
      {props.status && <span className="tag">{props.status}</span>}
    </div>
  )
}

/**
 * Info row component for displaying key-value pairs.
 */
function InfoRow({ label, value, mono = false }) {
  if (!value) return null
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
      <span className="t-label">{label}</span>
      <span style={{ color: 'var(--white)', fontSize: 13, fontFamily: mono ? 'var(--mono)' : 'inherit' }}>
        {value}
      </span>
    </div>
  )
}

/**
 * Tag list component for displaying arrays of strings.
 */
function TagList({ items, color = 'var(--muted)' }) {
  if (!items || items.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {items.map((item, i) => (
        <span key={i} style={{ padding: '4px 10px', background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 11, color }}>
          {item}
        </span>
      ))}
    </div>
  )
}

export default function ReviewDetail() {
  const { pipelineId } = useParams()
  const navigate = useNavigate()
  const [pipeline, setPipeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  const fetchPipeline = useCallback(async () => {
    if (!pipelineId) {
      setError('No pipeline ID provided')
      setLoading(false)
      return
    }

    try {
      const data = await getApplication(pipelineId)
      setPipeline(data)
      setError(null)
      log.info('review_detail.fetch_success', { pipelineId })
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_detail.fetch_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_detail.fetch_error', { error: String(err) })
        setError('Failed to load application')
      }
    } finally {
      setLoading(false)
    }
  }, [pipelineId])

  useEffect(() => {
    fetchPipeline()
  }, [fetchPipeline])

  const handleApprove = async () => {
    setActionLoading(true)
    try {
      await approveApplication(pipelineId)
      log.info('review_detail.approved', { pipelineId })
      navigate(routes.reviewQueue)
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_detail.approve_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_detail.approve_error', { error: String(err) })
        setError('Failed to approve application')
      }
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async () => {
    setActionLoading(true)
    try {
      await rejectApplication(pipelineId)
      log.info('review_detail.rejected', { pipelineId })
      navigate(routes.reviewQueue)
    } catch (err) {
      if (err instanceof TalentAgentApiError) {
        log.error('review_detail.reject_error', { status: err.status, message: err.message })
        setError(err.message)
      } else {
        log.error('review_detail.reject_error', { error: String(err) })
        setError('Failed to reject application')
      }
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="fade-in" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
        <Loader2 style={{ width: 24, height: 24, color: 'var(--gold)', animation: 'spin 1s linear infinite' }} />
      </div>
    )
  }

  if (error && !pipeline) {
    return (
      <div className="fade-in" style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center', paddingTop: 80 }}>
        <AlertCircle style={{ width: 48, height: 48, color: 'var(--status-error)', margin: '0 auto 16px', display: 'block' }} />
        <h2 className="t-serif" style={{ fontSize: 22, marginBottom: 8 }}>Error Loading Application</h2>
        <p className="t-body" style={{ color: 'var(--muted)', marginBottom: 24 }}>{error}</p>
        <button onClick={() => navigate(routes.reviewQueue)} className="btn-ghost" style={{ padding: '12px 24px' }}>
          <ArrowLeft style={{ width: 14, height: 14, marginRight: 8 }} />
          Back to Review Queue
        </button>
      </div>
    )
  }

  const { parsed_jd: jd, tailored_resume: resume, company_intel: intel, contact, outreach_email: outreach } = pipeline

  const isAwaitingReview = pipeline.status === 'AWAITING_REVIEW'

  return (
    <div className="fade-in" style={{ maxWidth: 1000 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <button
          onClick={() => navigate(routes.reviewQueue)}
          style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 14 }}
        >
          <ArrowLeft style={{ width: 16, height: 16 }} />
          Back to Review Queue
        </button>

        {isAwaitingReview && (
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleReject}
              disabled={actionLoading}
              className="btn-ghost"
              style={{ padding: '10px 20px', borderColor: 'var(--rose)', color: 'var(--rose)', display: 'flex', alignItems: 'center', gap: 6, opacity: actionLoading ? 0.5 : 1 }}
            >
              {actionLoading ? <Loader2 style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} /> : <X style={{ width: 14, height: 14 }} />}
              Reject
            </button>
            <button
              onClick={handleApprove}
              disabled={actionLoading}
              className="btn-primary"
              style={{ padding: '10px 20px', display: 'flex', alignItems: 'center', gap: 6, opacity: actionLoading ? 0.5 : 1 }}
            >
              {actionLoading ? <Loader2 style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }} /> : <Check style={{ width: 14, height: 14 }} />}
              Approve
            </button>
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--status-error)', padding: '16px 24px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle style={{ width: 18, height: 18, color: 'var(--status-error)', flexShrink: 0 }} />
          <p style={{ color: 'var(--status-error)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      {/* Pipeline info */}
      <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h1 className="t-serif" style={{ fontSize: 24 }}>
            {jd?.seniority_level || 'Role'} @ {intel?.company_name || 'Company'}
          </h1>
          <span className="tag" style={{ textTransform: 'uppercase' }}>{pipeline.status}</span>
        </div>
        <div style={{ display: 'flex', gap: 24, color: 'var(--muted)', fontSize: 13 }}>
          <span>Pipeline ID: {pipeline.id.slice(0, 8)}...</span>
          <span>Created: {new Date(pipeline.created_at).toLocaleDateString()}</span>
          {pipeline.approval_timestamp && <span>Approved: {new Date(pipeline.approval_timestamp).toLocaleDateString()}</span>}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Parsed JD */}
          {jd && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24 }}>
              <SectionHeader icon={Briefcase} title="Parsed Job Description" status={jd.parsed_at ? 'Parsed' : 'Pending'} />

              <InfoRow label="Seniority" value={jd.seniority_level} />
              <InfoRow label="Tone" value={jd.tone} />
              <InfoRow label="Compensation" value={jd.compensation_range} />

              {jd.required_skills?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Required Skills</span>
                  <TagList items={jd.required_skills} color="var(--emerald)" />
                </div>
              )}

              {jd.preferred_skills?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Preferred Skills</span>
                  <TagList items={jd.preferred_skills} />
                </div>
              )}

              {jd.tech_stack?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Tech Stack</span>
                  <TagList items={jd.tech_stack} color="var(--gold)" />
                </div>
              )}

              {jd.red_flags?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block', color: 'var(--amber)' }}>
                    <AlertTriangle style={{ width: 12, height: 12, marginRight: 6, verticalAlign: 'middle' }} />
                    Red Flags
                  </span>
                  <TagList items={jd.red_flags} color="var(--amber)" />
                </div>
              )}

              {jd.application_instructions && (
                <div style={{ marginTop: 16, padding: 12, background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Application Instructions</span>
                  <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5 }}>{jd.application_instructions}</p>
                </div>
              )}
            </div>
          )}

          {/* Company Intel */}
          {intel && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24 }}>
              <SectionHeader icon={Building2} title="Company Intelligence" status={intel.researched_at ? 'Researched' : 'Pending'} />

              <InfoRow label="Company" value={intel.company_name} />
              <InfoRow label="Growth Stage" value={intel.growth_stage} />
              <InfoRow label="Team Size" value={intel.team_size} />

              {intel.about && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>About</span>
                  <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5 }}>{intel.about}</p>
                </div>
              )}

              {intel.engineering_culture && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Engineering Culture</span>
                  <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5 }}>{intel.engineering_culture}</p>
                </div>
              )}

              {intel.tech_stack?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Company Tech Stack</span>
                  <TagList items={intel.tech_stack} color="var(--gold)" />
                </div>
              )}

              {intel.recent_news?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Recent News</span>
                  {intel.recent_news.map((news, i) => (
                    <p key={i} style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 6 }}>• {news}</p>
                  ))}
                </div>
              )}

              {intel.notable_facts?.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Notable Facts</span>
                  {intel.notable_facts.map((fact, i) => (
                    <p key={i} style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 6 }}>• {fact}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Tailored Resume */}
          {resume && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24 }}>
              <SectionHeader icon={FileText} title="Tailored Resume" status="Ready" />

              {resume.change_log?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Changes Made</span>
                  {resume.change_log.map((change, i) => (
                    <p key={i} style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 4 }}>• {change}</p>
                  ))}
                </div>
              )}

              {resume.gap_analysis && (
                <div style={{ marginBottom: 16, padding: 12, background: 'var(--surface)', border: '1px solid var(--border)' }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Gap Analysis</span>
                  <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.5 }}>{resume.gap_analysis}</p>
                </div>
              )}

              <details style={{ marginTop: 16 }}>
                <summary style={{ cursor: 'pointer', color: 'var(--gold)', fontSize: 13, marginBottom: 12 }}>
                  <Code style={{ width: 12, height: 12, marginRight: 6, verticalAlign: 'middle' }} />
                  View Tailored Resume Text
                </summary>
                <pre style={{ background: 'var(--surface)', padding: 16, fontSize: 11, color: 'var(--muted)', overflow: 'auto', maxHeight: 300, whiteSpace: 'pre-wrap' }}>
                  {resume.tailored_text}
                </pre>
              </details>
            </div>
          )}

          {/* Contact */}
          {contact && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24 }}>
              <SectionHeader icon={User} title="Contact Found" status={contact.confidence} />

              <InfoRow label="Name" value={contact.name} />
              <InfoRow label="Title" value={contact.title} />
              <InfoRow label="Email" value={contact.email} mono />
              {contact.fallback_email && <InfoRow label="Fallback" value={contact.fallback_email} mono />}
              <InfoRow label="Source" value={contact.source} />

              {contact.linkedin_url && (
                <a
                  href={contact.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-ghost"
                  style={{ marginTop: 16, padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11 }}
                >
                  <Globe style={{ width: 12, height: 12 }} />
                  LinkedIn Profile
                  <ExternalLink style={{ width: 10, height: 10 }} />
                </a>
              )}
            </div>
          )}

          {/* Outreach Email */}
          {outreach && (
            <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 24 }}>
              <SectionHeader icon={Mail} title="Outreach Email" status={outreach.status} />

              {outreach.subject_lines?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Subject Line Options</span>
                  {outreach.subject_lines.map((subject, i) => (
                    <div key={i} style={{ padding: '8px 12px', background: 'var(--surface)', border: '1px solid var(--border)', marginBottom: 6 }}>
                      <span style={{ color: 'var(--white)', fontSize: 13 }}>{i + 1}. {subject}</span>
                    </div>
                  ))}
                </div>
              )}

              {outreach.body && (
                <div>
                  <span className="t-label" style={{ marginBottom: 8, display: 'block' }}>Email Body</span>
                  <div style={{ padding: 16, background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                    {outreach.body}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* No artifacts message */}
      {!jd && !resume && !intel && !contact && !outreach && (
        <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 48, textAlign: 'center' }}>
          <AlertCircle style={{ width: 32, height: 32, color: 'var(--muted)', margin: '0 auto 16px', display: 'block' }} />
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>No artifacts generated yet for this application.</p>
          <p className="t-label" style={{ marginTop: 8 }}>Status: {pipeline.status}</p>
        </div>
      )}
    </div>
  )
}
