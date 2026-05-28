/**
 * Discovery API client — getTodayDigest, triggerDiscoveryRun, getJob.
 *
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS:
 * - Symbols: getTodayDigest, triggerDiscoveryRun, getJob owned by api-client-agent
 * - File path: frontend/src/api/discovery.ts
 *
 * Per HYPHA-API-CLIENT:
 * - getTodayDigest() — fetch latest digest for current user's candidate
 * - triggerDiscoveryRun() — kick off a new discovery run
 * - getJob(id) — fetch full job detail
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { apiClient } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Score breakdown per dimension (0-100).
 * Per NUTRIENTS.md DATA_CONTRACTS.ScoreBreakdown.
 */
export interface ScoreBreakdown {
  technical_match: number
  level_match: number
  culture_match: number
  industry_match: number
  growth_potential: number
  compensation_match: number
  /** Computed weighted composite score */
  composite?: number
}

/**
 * A scored job with full scoring breakdown.
 * Per NUTRIENTS.md DATA_CONTRACTS.ScoredJob.
 */
export interface ScoredJob {
  id: string
  discovered_job_id: string
  candidate_id: string
  score_breakdown: ScoreBreakdown
  composite_score: number
  is_hot: boolean
  reasoning: string
  scored_at: string | null
  /** Denormalized job fields for display */
  title: string
  company: string
  location: string | null
  url: string
}

/**
 * Daily digest response from GET /discovery/digest/{candidate_id}.
 * Per backend/api/discovery.py DailyDigestSchema.
 */
export interface DailyDigest {
  id?: string
  candidate_id: string
  run_date: string
  top_picks: ScoredJob[]
  hot_picks: ScoredJob[]
  new_companies: string[]
  total_jobs_discovered: number
  total_jobs_scored: number
  digest_summary?: string
  created_at?: string
}

/**
 * Response from POST /discovery/run/{candidate_id}.
 * Per backend/api/discovery.py RunResponse.
 */
export interface TriggerRunResponse {
  message: string
  candidate_id: string
  dry_run: boolean
}

/**
 * Job source type.
 * Per NUTRIENTS.md DATA_CONTRACTS.
 */
export type JobSource = 'greenhouse' | 'lever' | 'ashby' | 'workday'

/**
 * Full job detail from GET /discovery/job/{job_id}.
 * Per backend/api/discovery.py get_job response.
 */
export interface DiscoveredJob {
  id: string
  title: string
  company: string
  location: string | null
  url: string
  description: string | null
  source: JobSource
  posted_date: string | null
  status: string
  created_at: string
}

/**
 * Discovery stats response from GET /discovery/stats/{candidate_id}.
 * Per backend/api/discovery.py StatsResponse.
 */
export interface DiscoveryStats {
  candidate_id: string
  total_runs: number
  total_discovered: number
  total_scored: number
  last_run: string | null
  recent_runs: RecentRun[]
}

/**
 * Individual crawl run entry in stats.
 */
export interface RecentRun {
  id: string
  started_at: string
  completed_at: string | null
  status: string
  jobs_discovered: number
  jobs_scored: number
}

/**
 * Digest summary for list view.
 * Per backend/api/discovery.py DigestSummary.
 */
export interface DigestSummary {
  id: string
  run_date: string
  total_discovered: number
  total_scored: number
  digest_summary: string | null
  created_at: string
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * Get today's digest for a candidate.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * GET /api/v1/discovery/digest/{candidate_id}
 *
 * @param candidateId - UUID of the candidate
 * @returns The latest daily digest
 * @throws TalentAgentApiError on 404 (no digest found) or other errors
 */
export async function getTodayDigest(candidateId: string): Promise<DailyDigest> {
  return apiClient.get<DailyDigest>(`/discovery/digest/${candidateId}`)
}

/**
 * Trigger a discovery run for a candidate.
 *
 * The run executes in the background — monitor progress via stats endpoint
 * or SSE event stream on agent.status.discovery channel.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * POST /api/v1/discovery/trigger (legacy)
 * POST /api/v1/discovery/run/{candidate_id} (actual backend)
 *
 * @param candidateId - UUID of the candidate
 * @param dryRun - If true, run without persisting results
 * @returns Run trigger response with status
 * @throws TalentAgentApiError on errors
 */
export async function triggerDiscoveryRun(
  candidateId: string,
  dryRun: boolean = false
): Promise<TriggerRunResponse> {
  return apiClient.post<TriggerRunResponse>(
    `/discovery/run/${candidateId}?dry_run=${dryRun}`
  )
}

/**
 * Get full detail for a specific discovered job.
 *
 * Per backend/api/discovery.py:
 * GET /api/v1/discovery/job/{job_id}
 *
 * @param jobId - UUID of the discovered job
 * @returns Full job detail including description
 * @throws TalentAgentApiError on 404 (job not found) or other errors
 */
export async function getJob(jobId: string): Promise<DiscoveredJob> {
  return apiClient.get<DiscoveredJob>(`/discovery/job/${jobId}`)
}

/**
 * Get discovery stats for a candidate.
 *
 * Per backend/api/discovery.py:
 * GET /api/v1/discovery/stats/{candidate_id}
 *
 * @param candidateId - UUID of the candidate
 * @returns Run history and aggregate metrics
 * @throws TalentAgentApiError on errors
 */
export async function getDiscoveryStats(candidateId: string): Promise<DiscoveryStats> {
  return apiClient.get<DiscoveryStats>(`/discovery/stats/${candidateId}`)
}

/**
 * List all digests for a candidate, newest first.
 *
 * Per backend/api/discovery.py:
 * GET /api/v1/discovery/digests/{candidate_id}
 *
 * @param candidateId - UUID of the candidate
 * @param limit - Max number of digests to return (default 30, max 100)
 * @param offset - Pagination offset (default 0)
 * @returns Array of digest summaries
 * @throws TalentAgentApiError on errors
 */
export async function listDigests(
  candidateId: string,
  limit: number = 30,
  offset: number = 0
): Promise<DigestSummary[]> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  })
  return apiClient.get<DigestSummary[]>(`/discovery/digests/${candidateId}?${params}`)
}

/**
 * Update status of a discovered job.
 *
 * Per backend/api/discovery.py:
 * PATCH /api/v1/discovery/job/{job_id}/status
 *
 * Valid statuses: APPROVED, SKIPPED, APPLIED, INTERVIEWING, OFFERED, REJECTED
 *
 * @param jobId - UUID of the discovered job
 * @param status - New status value
 * @returns Updated job status
 * @throws TalentAgentApiError on 404 or 422 (invalid status)
 */
export async function updateJobStatus(
  jobId: string,
  status: 'APPROVED' | 'SKIPPED' | 'APPLIED' | 'INTERVIEWING' | 'OFFERED' | 'REJECTED'
): Promise<{ job_id: string; status: string }> {
  return apiClient.patch<{ job_id: string; status: string }>(
    `/discovery/job/${jobId}/status`,
    { status }
  )
}
