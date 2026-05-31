/**
 * Candidates API client — listCandidates (agency pipeline view).
 *
 * Note: the backend does not yet expose a GET /candidates endpoint — the
 * multi-candidate agency view is a forward-looking feature. This function
 * targets the planned route (/api/v1/candidates) and is fully exercised today
 * via mock mode (VITE_MOCK=true). Against a live backend without the endpoint,
 * it will surface a TalentAgentApiError, and Candidates.jsx renders its error
 * state per CLAUDE.md Rule 13.
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { apiClient } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * A candidate row in the agency pipeline table.
 */
export interface CandidateRow {
  id: string
  name: string
  title: string
  location: string
  status: string
  discovered: number
  applied: number
  interviews: number
  added: string
}

/**
 * Query params for listing candidates.
 */
export interface ListCandidatesQuery {
  search?: string
  status?: string
  limit?: number
  offset?: number
}

/**
 * Response from GET /candidates.
 */
export interface ListCandidatesResponse {
  items: CandidateRow[]
  total: number
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * List candidates in the agency pipeline.
 *
 * Per NUTRIENTS.md API_CONTRACTS (planned):
 * GET /api/v1/candidates
 *
 * @param query - Optional search/status/pagination filters
 * @returns Candidate rows and total count
 * @throws TalentAgentApiError on errors (incl. 404 if backend route absent)
 *
 * @example
 * ```ts
 * const { items } = await listCandidates({ status: 'active' })
 * ```
 */
export async function listCandidates(
  query: ListCandidatesQuery = {}
): Promise<ListCandidatesResponse> {
  const params = new URLSearchParams()
  if (query.search) params.set('search', query.search)
  if (query.status && query.status !== 'all') params.set('status', query.status)
  if (query.limit !== undefined) params.set('limit', query.limit.toString())
  if (query.offset !== undefined) params.set('offset', query.offset.toString())

  const qs = params.toString()
  const path = qs ? `/candidates?${qs}` : '/candidates'
  return apiClient.get<ListCandidatesResponse>(path)
}
