/**
 * API client for Talent Agent backend.
 * Single apiClient instance with auth header injection and error normalization.
 *
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS:
 * - Symbol: apiClient owned by api-client-agent
 * - Symbol: TalentAgentApiError owned by api-client-agent
 * - JWT storage key: talent-agent-jwt
 * - Base URL: VITE_API_BASE_URL
 *
 * Error handling (api-client-agent.error-handling scope):
 * - 401 responses invalidate JWT, redirect to /login, and surface toast notification
 * - Network errors surface TalentAgentApiError with status 0
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { routes } from '../lib/routes'

// ─── Toast Event System ──────────────────────────────────────────────────────
// Custom event pattern for toast notifications. The UI layer (frontend-agent)
// subscribes to these events and renders the actual toast UI.

/**
 * Toast notification payload.
 */
export interface ToastPayload {
  /** Toast message */
  message: string
  /** Toast type for styling */
  type: 'error' | 'warning' | 'success' | 'info'
  /** Auto-dismiss duration in ms (0 = manual dismiss) */
  duration?: number
}

/**
 * Custom event name for toast notifications.
 * UI components can listen: window.addEventListener('talent-agent:toast', handler)
 */
export const TOAST_EVENT = 'talent-agent:toast' as const

/**
 * Dispatch a toast notification event.
 * The UI layer is responsible for rendering the toast.
 *
 * @param payload - Toast notification payload
 */
export function dispatchToast(payload: ToastPayload): void {
  const event = new CustomEvent<ToastPayload>(TOAST_EVENT, {
    detail: payload,
    bubbles: true,
  })
  window.dispatchEvent(event)
}

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Storage key for JWT in localStorage.
 * Per NUTRIENTS.md DATA_CONTRACTS: storageKey: 'talent-agent-jwt'
 */
const JWT_STORAGE_KEY = 'talent-agent-jwt'

/**
 * Base URL for API requests.
 * Per NUTRIENTS.md: Env vars use VITE_* prefix per Vite's import.meta.env convention.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Error data structure for API errors.
 * Per NUTRIENTS.md DATA_CONTRACTS §API Client Domain.
 */
export interface TalentAgentApiErrorData {
  /** HTTP status code */
  status: number
  /** Backend error code if present */
  code: string
  /** User-facing message */
  message: string
}

/**
 * Request options for API client.
 */
interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  /** Request body — will be JSON.stringify'd unless FormData */
  body?: unknown
  /** Skip auth header injection */
  skipAuth?: boolean
}

// ─── Error Class ──────────────────────────────────────────────────────────────

/**
 * Custom error class for API errors.
 * Per HYPHA-API-CLIENT: includes status, code, message.
 */
export class TalentAgentApiError extends Error {
  public readonly status: number
  public readonly code: string

  constructor(data: TalentAgentApiErrorData) {
    super(data.message)
    this.name = 'TalentAgentApiError'
    this.status = data.status
    this.code = data.code
  }

  /**
   * Get error data as plain object.
   */
  toJSON(): TalentAgentApiErrorData {
    return {
      status: this.status,
      code: this.code,
      message: this.message,
    }
  }
}

// ─── JWT Helpers ──────────────────────────────────────────────────────────────

/**
 * Get the stored JWT token.
 */
export function getToken(): string | null {
  return localStorage.getItem(JWT_STORAGE_KEY)
}

/**
 * Store a JWT token.
 */
export function setToken(token: string): void {
  localStorage.setItem(JWT_STORAGE_KEY, token)
}

/**
 * Clear stored JWT.
 * Per HYPHA-API-CLIENT: 401 handling invalidates JWT.
 */
export function clearToken(): void {
  localStorage.removeItem(JWT_STORAGE_KEY)
}

// ─── API Client ───────────────────────────────────────────────────────────────

/**
 * Single API client instance for all backend requests.
 * Per NUTRIENTS.md: All API calls go through this client.
 */
export const apiClient = {
  /**
   * Get the base URL for API requests.
   */
  get baseUrl(): string {
    return API_BASE_URL
  },

  /**
   * Make an authenticated request to the API.
   *
   * Features:
   * - Auto-injects Authorization: Bearer header if JWT exists
   * - Handles 401 by invalidating JWT and redirecting to /login
   * - Normalizes errors to TalentAgentApiError
   * - Handles FormData bodies correctly (no JSON.stringify, no Content-Type)
   *
   * @param path - API path (e.g., '/auth/me')
   * @param options - Request options
   * @returns Parsed JSON response
   * @throws TalentAgentApiError on API errors
   */
  async request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const { body, skipAuth = false, ...fetchOptions } = options

    // Build headers
    const headers = new Headers(fetchOptions.headers)

    // Inject auth header if token exists and not skipped
    if (!skipAuth) {
      const token = getToken()
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
    }

    // Prepare body
    let requestBody: BodyInit | undefined

    if (body !== undefined) {
      if (body instanceof FormData) {
        // FormData: browser sets Content-Type with boundary
        requestBody = body
      } else {
        // JSON body
        headers.set('Content-Type', 'application/json')
        requestBody = JSON.stringify(body)
      }
    }

    // Make request
    const url = `${API_BASE_URL}${path}`
    let response: Response

    try {
      response = await fetch(url, {
        ...fetchOptions,
        headers,
        body: requestBody,
      })
    } catch (error) {
      // Network error (backend down, CORS, etc.)
      // Per HYPHA-API-CLIENT: "Killing the backend mid-session triggers an error toast"
      const networkError = new TalentAgentApiError({
        status: 0,
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to server. Please check your connection.',
      })

      dispatchToast({
        message: networkError.message,
        type: 'error',
        duration: 5000,
      })

      throw networkError
    }

    // Handle 401 — invalidate JWT, redirect to login, surface toast
    // Per HYPHA-API-CLIENT acceptance criteria: "401 response invalidates JWT,
    // redirects to /login, shows toast 'Session expired'"
    if (response.status === 401) {
      clearToken()

      // Dispatch toast notification before redirect
      // The UI layer (ToastProvider) will render the message
      dispatchToast({
        message: 'Session expired. Please log in again.',
        type: 'error',
        duration: 5000,
      })

      // Redirect to login after a brief delay to allow toast to render
      // Using setTimeout ensures the toast event is processed before navigation
      setTimeout(() => {
        window.location.href = routes.login
      }, 100)

      throw new TalentAgentApiError({
        status: 401,
        code: 'UNAUTHORIZED',
        message: 'Session expired. Please log in again.',
      })
    }

    // Handle error responses
    if (!response.ok) {
      let errorData: { detail?: string; code?: string } = {}
      try {
        errorData = await response.json()
      } catch {
        // Response body is not JSON
      }

      throw new TalentAgentApiError({
        status: response.status,
        code: errorData.code || `HTTP_${response.status}`,
        message: errorData.detail || `Request failed with status ${response.status}`,
      })
    }

    // Parse successful response
    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T
    }

    return response.json()
  },

  /**
   * GET request shorthand.
   */
  async get<T>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  },

  /**
   * POST request shorthand.
   */
  async post<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body })
  },

  /**
   * PUT request shorthand.
   */
  async put<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PUT', body })
  },

  /**
   * DELETE request shorthand.
   */
  async delete<T>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' })
  },

  /**
   * PATCH request shorthand.
   */
  async patch<T>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PATCH', body })
  },
}

// ─── Default Export ───────────────────────────────────────────────────────────

export default apiClient
