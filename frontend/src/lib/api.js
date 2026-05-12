/**
 * API client for Talent Agent backend.
 * Handles auth headers and base URL configuration.
 */

// In dev, Vite proxies /api → http://localhost:8000
// In prod, set VITE_API_URL to the full backend URL
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

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
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function requestMagicLink(email) {
  return request('/auth/request-link', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function verifyMagicLink(token) {
  return request('/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function getMe() {
  return request('/auth/me')
}

// ─── Onboarding ───────────────────────────────────────────────────────────────

export async function uploadResume(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/onboarding/resume', {
    method: 'POST',
    body: formData,
  })
}

export async function saveProfile(profile) {
  return request('/onboarding/profile', {
    method: 'POST',
    body: JSON.stringify(profile),
  })
}

export async function getOnboardingStatus() {
  return request('/onboarding/status')
}

// ─── Discovery ────────────────────────────────────────────────────────────────

export async function getLatestDigest(candidateId) {
  return request(`/discovery/digest/${candidateId}`)
}

export async function getDiscoveryStats(candidateId) {
  return request(`/discovery/stats/${candidateId}`)
}

export async function triggerDiscoveryRun(candidateId, dryRun = false) {
  return request(`/discovery/run/${candidateId}?dry_run=${dryRun}`, {
    method: 'POST',
  })
}
