/**
 * API client for Talent Agent backend.
 * Handles auth headers and base URL configuration.
 * Per NUTRIENTS.md API_CONTRACTS — this is the ONLY place to construct fetch URLs.
 */

import { routes } from './routes'
import * as mock from './mock'

// In dev, Vite proxies /api → http://localhost:8000
// In prod, set VITE_API_URL to the full backend URL
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

// Mock mode: when VITE_MOCK=true the client short-circuits all network calls
// with seeded fixture data so the dashboard is navigable without a live backend.
const USE_MOCK = import.meta.env.VITE_MOCK === 'true'

/**
 * Get the stored JWT token.
 */
export function getToken() {
  return localStorage.getItem('ta_token')
}

/**
 * Store a JWT token.
 */
export function setToken(token) {
  localStorage.setItem('ta_token', token)
}

/**
 * Clear stored auth data.
 */
export function clearAuth() {
  localStorage.removeItem('ta_token')
  localStorage.removeItem('ta_user')
}

/**
 * Make an authenticated API request.
 */
async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    clearAuth()
    window.location.href = routes.login
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
// Per NUTRIENTS.md API_CONTRACTS §Auth Endpoints

export async function requestMagicLink(email) {
  if (USE_MOCK) return mock.requestMagicLink(email)
  return request('/auth/request-link', { method: 'POST', body: JSON.stringify({ email }) })
}

export async function verifyMagicLink(token) {
  if (USE_MOCK) return mock.verifyMagicLink(token)
  return request('/auth/verify', { method: 'POST', body: JSON.stringify({ token }) })
}

export async function getMe() {
  if (USE_MOCK) return mock.getMe()
  return request('/auth/me')
}

// ─── Onboarding ───────────────────────────────────────────────────────────────

export async function uploadResume(file) {
  if (USE_MOCK) return mock.uploadResume(file)
  const formData = new FormData()
  formData.append('file', file)
  return request('/onboarding/resume', { method: 'POST', body: formData })
}

export async function saveProfile(profile) {
  if (USE_MOCK) return mock.saveProfile(profile)
  return request('/onboarding/profile', { method: 'POST', body: JSON.stringify(profile) })
}

export async function getOnboardingStatus() {
  if (USE_MOCK) return mock.getOnboardingStatus()
  return request('/onboarding/status')
}

// ─── Discovery ────────────────────────────────────────────────────────────────

export async function triggerDiscovery(candidateId, dryRun = false) {
  if (USE_MOCK) return mock.triggerDiscovery(candidateId, dryRun)
  return request('/discovery/trigger', { method: 'POST', body: JSON.stringify({ candidate_id: candidateId, dry_run: dryRun }) })
}

export async function getDigest(digestId) {
  if (USE_MOCK) return mock.getDigest(digestId)
  return request(`/discovery/digest/${digestId}`)
}

export async function getLatestDigest(candidateId) {
  if (USE_MOCK) return mock.getLatestDigest(candidateId)
  return request(`/discovery/digest/${candidateId}`)
}

export async function getDiscoveryStats(candidateId) {
  if (USE_MOCK) return mock.getDiscoveryStats(candidateId)
  return request(`/discovery/stats/${candidateId}`)
}

export async function triggerDiscoveryRun(candidateId, dryRun = false) {
  if (USE_MOCK) return mock.triggerDiscoveryRun(candidateId, dryRun)
  return request(`/discovery/run/${candidateId}?dry_run=${dryRun}`, { method: 'POST' })
}

// ─── Application ──────────────────────────────────────────────────────────────

export async function startApplication(jobId, candidateId) {
  if (USE_MOCK) return mock.startApplication(jobId, candidateId)
  return request('/application/start', { method: 'POST', body: JSON.stringify({ job_id: jobId, candidate_id: candidateId }) })
}

export async function submitApplication(pipelineId) {
  if (USE_MOCK) return mock.submitApplication(pipelineId)
  return request(`/application/submit/${pipelineId}`, { method: 'POST' })
}

export async function listApplications(opts = {}) {
  if (USE_MOCK) return mock.listApplications(opts)
  const { candidateId, status, limit = 50, offset = 0 } = opts
  const params = new URLSearchParams()
  if (candidateId) params.append('candidate_id', candidateId)
  if (status) params.append('status', status)
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())
  return request(`/application/list?${params}`)
}

export async function getPipeline(pipelineId) {
  if (USE_MOCK) return mock.getPipeline(pipelineId)
  return request(`/application/${pipelineId}`)
}

// ─── Review ───────────────────────────────────────────────────────────────────

export async function getReviewQueue(candidateId = null) {
  if (USE_MOCK) return mock.getReviewQueue(candidateId)
  const params = candidateId ? `?candidate_id=${candidateId}` : ''
  return request(`/review/queue${params}`)
}

export async function approvePipeline(pipelineId) {
  if (USE_MOCK) return mock.approvePipeline(pipelineId)
  return request(`/review/${pipelineId}/approve`, { method: 'POST' })
}

export async function rejectPipeline(pipelineId, reason = null) {
  if (USE_MOCK) return mock.rejectPipeline(pipelineId, reason)
  return request(`/review/${pipelineId}/reject`, { method: 'POST', body: JSON.stringify({ reason }) })
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function getHealth() {
  if (USE_MOCK) return mock.getHealth()
  return request('/health')
}
