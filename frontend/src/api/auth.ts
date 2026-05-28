/**
 * Auth API client for Talent Agent backend.
 * Handles magic link authentication flow and session management.
 *
 * Per NUTRIENTS.md §API_CONTRACTS Auth Endpoints:
 * - POST /api/v1/auth/request-link — Request magic link
 * - POST /api/v1/auth/verify — Verify magic link, return JWT
 * - GET /api/v1/auth/me — Get current authenticated user
 *
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS:
 * - Symbol: requestMagicLink, verifyToken, refreshSession owned by api-client-agent
 * - File: frontend/src/api/auth.ts
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { apiClient, setToken, clearToken, getToken } from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Request body for magic link request.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/auth/request-link
 */
interface RequestLinkRequest {
  email: string
}

/**
 * Response from magic link request.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/auth/request-link
 */
interface RequestLinkResponse {
  message: string
  /** Only present in DEBUG=true mode */
  magic_link?: string
  /** Only present in DEBUG=true mode */
  token?: string
}

/**
 * Request body for token verification.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/auth/verify
 */
interface VerifyRequest {
  token: string
}

/**
 * Response from token verification.
 * Per NUTRIENTS.md API_CONTRACTS §POST /api/v1/auth/verify
 */
interface VerifyResponse {
  access_token: string
  token_type: 'bearer'
  user_id: string
  email: string
  is_onboarded: boolean
}

/**
 * User data from /auth/me endpoint.
 * Per NUTRIENTS.md API_CONTRACTS §GET /api/v1/auth/me
 */
export interface AuthUser {
  id: string
  email: string
  name: string | null
  is_onboarded: boolean
  candidate_id: string | null
  created_at: string
}

/**
 * Result from verifyToken including both user data and the raw response.
 */
export interface VerifyResult {
  user: AuthUser
  accessToken: string
  isOnboarded: boolean
}

// ─── Auth API Functions ───────────────────────────────────────────────────────

/**
 * Request a magic link for email authentication.
 *
 * Sends a magic link to the provided email address. The user clicks
 * the link to complete authentication.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * - Endpoint: POST /api/v1/auth/request-link
 * - Error 400: Invalid email format
 * - Error 429: Rate limited (3/hour/email)
 *
 * @param email - The email address to send the magic link to
 * @returns Response with confirmation message
 * @throws TalentAgentApiError on API errors
 *
 * @example
 * ```ts
 * const result = await requestMagicLink('user@example.com')
 * // result.message === 'Check your email for a magic link'
 * ```
 */
export async function requestMagicLink(email: string): Promise<RequestLinkResponse> {
  const body: RequestLinkRequest = { email }

  return apiClient.post<RequestLinkResponse>('/auth/request-link', body, {
    skipAuth: true, // No auth required for login request
  })
}

/**
 * Verify a magic link token and establish a session.
 *
 * Called when user clicks the magic link. Validates the token,
 * issues a JWT, and stores it in localStorage.
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * - Endpoint: POST /api/v1/auth/verify
 * - Error 401: "This link has already been used"
 * - Error 401: "This link has expired"
 * - Error 401: "Invalid or expired link"
 *
 * Per NUTRIENTS.md STACK-CANON OVERRIDE:
 * - JWT storage is localStorage per iter-2's resolved decision
 * - Storage key: 'talent-agent-jwt'
 *
 * @param token - The magic link token from the URL
 * @returns Verify result with user data and access token
 * @throws TalentAgentApiError on API errors
 *
 * @example
 * ```ts
 * // Extract token from URL: /auth/verify?token=abc123
 * const token = new URLSearchParams(location.search).get('token')
 * const result = await verifyToken(token)
 * // JWT is now stored in localStorage
 * // result.user contains user data
 * ```
 */
export async function verifyToken(token: string): Promise<VerifyResult> {
  const body: VerifyRequest = { token }

  const response = await apiClient.post<VerifyResponse>('/auth/verify', body, {
    skipAuth: true, // No auth required for verification
  })

  // Store the JWT in localStorage
  // Per NUTRIENTS.md: JWT HS256, 7d, stored in localStorage
  setToken(response.access_token)

  // Build user object from response
  // Note: /auth/verify returns minimal user data
  // Full user data is fetched via refreshSession/getMe
  const user: AuthUser = {
    id: response.user_id,
    email: response.email,
    name: null, // Not provided in verify response
    is_onboarded: response.is_onboarded,
    candidate_id: null, // Not provided in verify response
    created_at: new Date().toISOString(), // Approximate
  }

  return {
    user,
    accessToken: response.access_token,
    isOnboarded: response.is_onboarded,
  }
}

/**
 * Refresh the current session by fetching fresh user data.
 *
 * Used to validate that the stored JWT is still valid and to
 * get updated user information (e.g., after onboarding).
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * - Endpoint: GET /api/v1/auth/me
 * - Error 401: "Not authenticated" — JWT missing or invalid
 * - Error 401: "Token expired" — JWT has expired
 * - Error 401: "User not found or inactive"
 *
 * On 401, the apiClient automatically:
 * - Clears the JWT from localStorage
 * - Redirects to /login
 *
 * @returns Current user data if session is valid
 * @returns null if no JWT is stored (user not logged in)
 * @throws TalentAgentApiError on API errors (except 401 which triggers redirect)
 *
 * @example
 * ```ts
 * // On app load, validate the session
 * const user = await refreshSession()
 * if (user) {
 *   // User is authenticated, show dashboard
 * } else {
 *   // No session, show login
 * }
 * ```
 */
export async function refreshSession(): Promise<AuthUser | null> {
  // Check if we have a token before making the request
  const token = getToken()
  if (!token) {
    return null
  }

  // Fetch current user data
  // 401 handling is automatic via apiClient
  return apiClient.get<AuthUser>('/auth/me')
}

/**
 * Log out the current user.
 *
 * Clears the JWT from localStorage. The server does not need
 * to be notified since JWTs are stateless.
 *
 * @example
 * ```ts
 * logout()
 * // JWT is cleared, redirect to login page
 * window.location.href = '/login'
 * ```
 */
export function logout(): void {
  clearToken()
}

/**
 * Check if a user is currently authenticated.
 *
 * This is a synchronous check that only verifies a JWT exists.
 * It does NOT validate the JWT with the server. Use refreshSession()
 * for server-validated authentication.
 *
 * @returns true if a JWT is stored, false otherwise
 *
 * @example
 * ```ts
 * // Quick check for UI rendering
 * if (isAuthenticated()) {
 *   showDashboard()
 * } else {
 *   showLogin()
 * }
 * ```
 */
export function isAuthenticated(): boolean {
  return getToken() !== null
}
