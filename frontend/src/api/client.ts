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
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { routes } from '../lib/routes'

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
      throw new TalentAgentApiError({
        status: 0,
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to server. Please check your connection.',
      })
    }

    // Handle 401 — invalidate JWT, redirect to login
    if (response.status === 401) {
      clearToken()
      // Redirect to login
      window.location.href = routes.login
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
