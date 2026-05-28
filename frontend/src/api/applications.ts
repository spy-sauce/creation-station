/**
 * Applications API client — listApplications, approveApplication, rejectApplication.
 *
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS:
 * - Symbols: listApplications, approveApplication, rejectApplication owned by api-client-agent
 * - File path: frontend/src/api/applications.ts
 *
 * Per HYPHA-API-CLIENT:
 * - listApplications() — fetch application pipelines for a candidate
 * - approveApplication(id) — approve a pipeline for submission
 * - rejectApplication(id, reason) — reject a pipeline
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { apiClient } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Application pipeline status (state machine).
 * Per NUTRIENTS.md §E Allow-listed Identifiers.
 */
export type ApplicationPipelineStatus =
  | 'QUEUED'
  | 'PARSING'
  | 'TAILORING'
  | 'RESEARCHING'
  | 'COMPOSING'
  | 'AWAITING_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUBMITTED'
  | 'SENT'
  | 'TRACKED'
  | 'FAILED'
  | 'REQUIRES_MANUAL'

/**
 * Contact confidence level.
 * Per NUTRIENTS.md DATA_CONTRACTS.
 */
export type ContactConfidence = 'HIGH' | 'MEDIUM' | 'LOW'

/**
 * Outreach email status.
 * Per NUTRIENTS.md DATA_CONTRACTS.
 */
export type OutreachStatus = 'DRAFT' | 'SENT' | 'BOUNCED' | 'REPLIED'

/**
 * Parsed job description.
 * Per NUTRIENTS.md DATA_CONTRACTS.ParsedJD.
 */
export interface ParsedJD {
  id: string
  job_id: string
  required_skills: string[]
  preferred_skills: string[]
  seniority_level: string
  tech_stack: string[]
  culture_signals: string[]
  tone: string
  pain_points: string[]
  compensation_range: string | null
  red_flags: string[]
  application_instructions: string | null
  parsed_at: string
}

/**
 * Tailored resume.
 * Per NUTRIENTS.md DATA_CONTRACTS.TailoredResume.
 */
export interface TailoredResume {
  id: string
  pipeline_id: string
  original_text: string
  tailored_text: string
  change_log: string[]
  gap_analysis: string
  created_at: string
}

/**
 * Company intelligence.
 * Per NUTRIENTS.md DATA_CONTRACTS.CompanyIntel.
 */
export interface CompanyIntel {
  id: string
  pipeline_id: string
  company_name: string
  about: string
  recent_news: string[]
  tech_stack: string[]
  engineering_culture: string
  growth_stage: string
  team_size: string | null
  notable_facts: string[]
  researched_at: string
}

/**
 * Contact information.
 * Per NUTRIENTS.md DATA_CONTRACTS.Contact.
 */
export interface Contact {
  id: string
  pipeline_id: string
  name: string
  title: string
  email: string
  linkedin_url: string | null
  confidence: ContactConfidence
  fallback_email: string | null
  source: string
  found_at: string
}

/**
 * Outreach email.
 * Per NUTRIENTS.md DATA_CONTRACTS.OutreachEmail.
 */
export interface OutreachEmail {
  id: string
  pipeline_id: string
  subject_lines: string[]
  body: string
  status: OutreachStatus
  created_at: string
}

/**
 * Full application pipeline entity.
 * Per NUTRIENTS.md DATA_CONTRACTS.ApplicationPipeline.
 */
export interface ApplicationPipeline {
  id: string
  candidate_id: string
  job_id: string
  status: ApplicationPipelineStatus
  parsed_jd: ParsedJD | null
  tailored_resume: TailoredResume | null
  company_intel: CompanyIntel | null
  contact: Contact | null
  outreach_email: OutreachEmail | null
  approval_timestamp: string | null
  submitted_at: string | null
  screenshots: string[]
  created_at: string
  updated_at: string
}

/**
 * Query params for listing applications.
 * Per NUTRIENTS.md API_CONTRACTS §GET /api/v1/application/list.
 */
export interface ListApplicationsQuery {
  candidate_id?: string
  status?: ApplicationPipelineStatus
  limit?: number
  offset?: number
}

/**
 * Response from listing applications.
 * Per NUTRIENTS.md API_CONTRACTS §GET /api/v1/application/list.
 */
export interface ListApplicationsResponse {
  pipelines: ApplicationPipeline[]
  total: number
}

/**
 * Response from approving a pipeline.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/review/{pipeline_id}/approve.
 */
export interface ApproveResponse {
  pipeline_id: string
  status: 'APPROVED'
  approval_timestamp: string
  message: string
}

/**
 * Request body for rejecting a pipeline.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/review/{pipeline_id}/reject.
 */
export interface RejectRequest {
  reason?: string
}

/**
 * Response from rejecting a pipeline.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/review/{pipeline_id}/reject.
 */
export interface RejectResponse {
  pipeline_id: string
  status: 'REJECTED'
  message: string
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * Get a single application pipeline by ID.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * GET /api/v1/application/{pipeline_id}
 *
 * @param pipelineId - UUID of the application pipeline
 * @returns Full application pipeline with all artifacts
 * @throws TalentAgentApiError on 404 (not found) or other errors
 *
 * @example
 * ```ts
 * const pipeline = await getApplication('pipeline-uuid')
 * // pipeline.parsed_jd, pipeline.company_intel, etc.
 * ```
 */
export async function getApplication(pipelineId: string): Promise<ApplicationPipeline> {
  return apiClient.get<ApplicationPipeline>(`/application/${pipelineId}`)
}

/**
 * List application pipelines for a candidate.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * GET /api/v1/application/list
 *
 * @param query - Optional filter/pagination params
 * @returns List of application pipelines and total count
 * @throws TalentAgentApiError on errors
 *
 * @example
 * ```ts
 * // Get all applications for a candidate
 * const { pipelines, total } = await listApplications({
 *   candidate_id: 'abc-123',
 *   limit: 20,
 *   offset: 0
 * })
 *
 * // Get only those awaiting review
 * const { pipelines } = await listApplications({
 *   candidate_id: 'abc-123',
 *   status: 'AWAITING_REVIEW'
 * })
 * ```
 */
export async function listApplications(
  query: ListApplicationsQuery = {}
): Promise<ListApplicationsResponse> {
  const params = new URLSearchParams()

  if (query.candidate_id !== undefined) {
    params.set('candidate_id', query.candidate_id)
  }
  if (query.status !== undefined) {
    params.set('status', query.status)
  }
  if (query.limit !== undefined) {
    params.set('limit', query.limit.toString())
  }
  if (query.offset !== undefined) {
    params.set('offset', query.offset.toString())
  }

  const queryString = params.toString()
  const path = queryString ? `/application/list?${queryString}` : '/application/list'

  return apiClient.get<ListApplicationsResponse>(path)
}

/**
 * Approve an application pipeline for submission.
 *
 * This transitions the pipeline from AWAITING_REVIEW to APPROVED.
 * The pipeline can then be submitted to the actual job application.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * POST /api/v1/review/{pipeline_id}/approve
 *
 * Error responses:
 * - 404: "Pipeline not found"
 * - 400: "Pipeline is not awaiting review"
 *
 * @param pipelineId - UUID of the application pipeline
 * @returns Approve response with timestamp
 * @throws TalentAgentApiError on 404 (not found) or 400 (wrong status)
 *
 * @example
 * ```ts
 * const result = await approveApplication('pipeline-uuid')
 * // result.status === 'APPROVED'
 * // result.approval_timestamp contains ISO timestamp
 * ```
 */
export async function approveApplication(pipelineId: string): Promise<ApproveResponse> {
  return apiClient.post<ApproveResponse>(`/review/${pipelineId}/approve`)
}

/**
 * Reject an application pipeline.
 *
 * This transitions the pipeline from AWAITING_REVIEW to REJECTED.
 * An optional reason can be provided for tracking purposes.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * POST /api/v1/review/{pipeline_id}/reject
 *
 * Error responses:
 * - 404: "Pipeline not found"
 * - 400: "Pipeline is not awaiting review"
 *
 * @param pipelineId - UUID of the application pipeline
 * @param reason - Optional rejection reason
 * @returns Reject response confirming status change
 * @throws TalentAgentApiError on 404 (not found) or 400 (wrong status)
 *
 * @example
 * ```ts
 * // Reject without reason
 * const result = await rejectApplication('pipeline-uuid')
 *
 * // Reject with reason
 * const result = await rejectApplication('pipeline-uuid', 'Role not aligned with career goals')
 * // result.status === 'REJECTED'
 * ```
 */
export async function rejectApplication(
  pipelineId: string,
  reason?: string
): Promise<RejectResponse> {
  const body: RejectRequest = reason !== undefined ? { reason } : {}
  return apiClient.post<RejectResponse>(`/review/${pipelineId}/reject`, body)
}
