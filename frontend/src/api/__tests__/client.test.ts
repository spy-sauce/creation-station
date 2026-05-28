/**
 * Tests for API client.
 * Per HYPHA-TESTS scope: vitest, mock fetch, 401 handling.
 *
 * Acceptance criteria from HYPHA-TESTS:
 * - Mocks fetch via vi.mock or direct stubbing
 * - Asserts Authorization: Bearer header injected on requests
 * - Asserts 401 response triggers logout callback (JWT cleared, redirect)
 * - Asserts network error surfaces TalentAgentApiError with correct shape
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  apiClient,
  TalentAgentApiError,
  getToken,
  setToken,
  clearToken,
  dispatchToast,
  TOAST_EVENT,
  type ToastPayload,
} from '../client'

// ─── Test Helpers ──────────────────────────────────────────────────────────────

/**
 * Create a mock Response object.
 */
function mockResponse(
  body: unknown,
  options: { status?: number; ok?: boolean; headers?: Record<string, string> } = {}
): Response {
  const { status = 200, ok = status >= 200 && status < 300, headers = {} } = options
  return {
    ok,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
    headers: new Headers(headers),
  } as Response
}

// ─── Setup ─────────────────────────────────────────────────────────────────────

describe('apiClient', () => {
  let originalFetch: typeof fetch
  let originalLocation: Location

  beforeEach(() => {
    // Store original fetch
    originalFetch = globalThis.fetch

    // Store original location and mock it
    originalLocation = window.location
    // @ts-expect-error - Mocking window.location
    delete window.location
    window.location = { ...originalLocation, href: '' } as Location

    // Clear any stored tokens
    clearToken()

    // Clear all mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    // Restore original fetch
    globalThis.fetch = originalFetch

    // Restore original location
    window.location = originalLocation

    // Clear timers
    vi.useRealTimers()
  })

  // ─── Token Management ──────────────────────────────────────────────────────

  describe('token management', () => {
    it('getToken returns null when no token is stored', () => {
      expect(getToken()).toBeNull()
    })

    it('setToken stores the token in localStorage', () => {
      const token = 'test-jwt-token'
      setToken(token)
      expect(getToken()).toBe(token)
    })

    it('clearToken removes the token from localStorage', () => {
      setToken('test-jwt-token')
      expect(getToken()).not.toBeNull()
      clearToken()
      expect(getToken()).toBeNull()
    })
  })

  // ─── Authorization Header Injection ────────────────────────────────────────

  describe('Authorization header injection', () => {
    it('injects Authorization: Bearer header when token exists', async () => {
      const testToken = 'my-test-jwt-token-12345'
      setToken(testToken)

      let capturedHeaders: Headers | null = null

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedHeaders = init?.headers as Headers
        return mockResponse({ data: 'test' })
      })

      await apiClient.get('/test')

      expect(capturedHeaders).not.toBeNull()
      expect(capturedHeaders!.get('Authorization')).toBe(`Bearer ${testToken}`)
    })

    it('does not inject Authorization header when no token exists', async () => {
      // Ensure no token is set
      clearToken()

      let capturedHeaders: Headers | null = null

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedHeaders = init?.headers as Headers
        return mockResponse({ data: 'test' })
      })

      await apiClient.get('/test')

      expect(capturedHeaders).not.toBeNull()
      expect(capturedHeaders!.get('Authorization')).toBeNull()
    })

    it('skips Authorization header when skipAuth option is true', async () => {
      const testToken = 'my-test-jwt-token'
      setToken(testToken)

      let capturedHeaders: Headers | null = null

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedHeaders = init?.headers as Headers
        return mockResponse({ data: 'test' })
      })

      await apiClient.get('/test', { skipAuth: true })

      expect(capturedHeaders).not.toBeNull()
      expect(capturedHeaders!.get('Authorization')).toBeNull()
    })
  })

  // ─── 401 Handling ──────────────────────────────────────────────────────────

  describe('401 unauthorized handling', () => {
    it('clears JWT token on 401 response', async () => {
      setToken('expired-token')
      expect(getToken()).not.toBeNull()

      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Token expired' }, { status: 401 })
      })

      vi.useFakeTimers()

      await expect(apiClient.get('/protected')).rejects.toThrow(TalentAgentApiError)

      // Token should be cleared
      expect(getToken()).toBeNull()
    })

    it('redirects to /login on 401 response', async () => {
      setToken('expired-token')

      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Token expired' }, { status: 401 })
      })

      vi.useFakeTimers()

      await expect(apiClient.get('/protected')).rejects.toThrow(TalentAgentApiError)

      // Fast-forward past the redirect timeout
      vi.advanceTimersByTime(150)

      // Location should be redirected to /login
      expect(window.location.href).toBe('/login')
    })

    it('dispatches toast notification on 401 response', async () => {
      setToken('expired-token')

      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Token expired' }, { status: 401 })
      })

      const toastHandler = vi.fn()
      window.addEventListener(TOAST_EVENT, toastHandler as EventListener)

      vi.useFakeTimers()

      try {
        await apiClient.get('/protected')
      } catch {
        // Expected to throw
      }

      expect(toastHandler).toHaveBeenCalled()
      const event = toastHandler.mock.calls[0][0] as CustomEvent<ToastPayload>
      expect(event.detail.type).toBe('error')
      expect(event.detail.message).toContain('Session expired')

      window.removeEventListener(TOAST_EVENT, toastHandler as EventListener)
    })

    it('throws TalentAgentApiError with status 401 on unauthorized', async () => {
      setToken('expired-token')

      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Token expired' }, { status: 401 })
      })

      vi.useFakeTimers()

      try {
        await apiClient.get('/protected')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        expect(apiError.status).toBe(401)
        expect(apiError.code).toBe('UNAUTHORIZED')
      }
    })
  })

  // ─── Network Error Handling ────────────────────────────────────────────────

  describe('network error handling', () => {
    it('surfaces TalentAgentApiError with status 0 on network failure', async () => {
      globalThis.fetch = vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      })

      // Suppress toast during test
      const toastHandler = vi.fn()
      window.addEventListener(TOAST_EVENT, toastHandler as EventListener)

      try {
        await apiClient.get('/test')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        expect(apiError.status).toBe(0)
        expect(apiError.code).toBe('NETWORK_ERROR')
        expect(apiError.message).toContain('Unable to connect')
      }

      window.removeEventListener(TOAST_EVENT, toastHandler as EventListener)
    })

    it('dispatches error toast on network failure', async () => {
      globalThis.fetch = vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      })

      const toastHandler = vi.fn()
      window.addEventListener(TOAST_EVENT, toastHandler as EventListener)

      try {
        await apiClient.get('/test')
      } catch {
        // Expected
      }

      expect(toastHandler).toHaveBeenCalled()
      const event = toastHandler.mock.calls[0][0] as CustomEvent<ToastPayload>
      expect(event.detail.type).toBe('error')
      expect(event.detail.message).toContain('Unable to connect')

      window.removeEventListener(TOAST_EVENT, toastHandler as EventListener)
    })

    it('TalentAgentApiError toJSON returns correct shape', async () => {
      globalThis.fetch = vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      })

      // Suppress toast
      const toastHandler = vi.fn()
      window.addEventListener(TOAST_EVENT, toastHandler as EventListener)

      try {
        await apiClient.get('/test')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        const json = apiError.toJSON()

        expect(json).toHaveProperty('status')
        expect(json).toHaveProperty('code')
        expect(json).toHaveProperty('message')
        expect(typeof json.status).toBe('number')
        expect(typeof json.code).toBe('string')
        expect(typeof json.message).toBe('string')
      }

      window.removeEventListener(TOAST_EVENT, toastHandler as EventListener)
    })
  })

  // ─── HTTP Method Shorthands ────────────────────────────────────────────────

  describe('HTTP method shorthands', () => {
    it('get() sends GET request', async () => {
      let capturedMethod: string | undefined

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedMethod = init?.method
        return mockResponse({ data: 'test' })
      })

      await apiClient.get('/test')

      expect(capturedMethod).toBe('GET')
    })

    it('post() sends POST request with JSON body', async () => {
      let capturedMethod: string | undefined
      let capturedBody: string | undefined
      let capturedContentType: string | null = null

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedMethod = init?.method
        capturedBody = init?.body as string
        capturedContentType = (init?.headers as Headers)?.get('Content-Type')
        return mockResponse({ success: true })
      })

      const payload = { name: 'test', value: 123 }
      await apiClient.post('/test', payload)

      expect(capturedMethod).toBe('POST')
      expect(capturedContentType).toBe('application/json')
      expect(JSON.parse(capturedBody!)).toEqual(payload)
    })

    it('put() sends PUT request', async () => {
      let capturedMethod: string | undefined

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedMethod = init?.method
        return mockResponse({ success: true })
      })

      await apiClient.put('/test', { data: 'updated' })

      expect(capturedMethod).toBe('PUT')
    })

    it('patch() sends PATCH request', async () => {
      let capturedMethod: string | undefined

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedMethod = init?.method
        return mockResponse({ success: true })
      })

      await apiClient.patch('/test', { field: 'value' })

      expect(capturedMethod).toBe('PATCH')
    })

    it('delete() sends DELETE request', async () => {
      let capturedMethod: string | undefined

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedMethod = init?.method
        return mockResponse({ success: true })
      })

      await apiClient.delete('/test')

      expect(capturedMethod).toBe('DELETE')
    })
  })

  // ─── FormData Handling ─────────────────────────────────────────────────────

  describe('FormData handling', () => {
    it('does not set Content-Type for FormData (browser sets it)', async () => {
      let capturedContentType: string | null = null
      let capturedBody: BodyInit | undefined

      globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
        capturedContentType = (init?.headers as Headers)?.get('Content-Type')
        capturedBody = init?.body
        return mockResponse({ success: true })
      })

      const formData = new FormData()
      formData.append('file', new Blob(['test']), 'test.pdf')

      await apiClient.post('/upload', formData)

      // Content-Type should NOT be set (browser handles multipart boundary)
      expect(capturedContentType).toBeNull()
      expect(capturedBody).toBeInstanceOf(FormData)
    })
  })

  // ─── Error Response Handling ───────────────────────────────────────────────

  describe('error response handling', () => {
    it('parses error detail from response body', async () => {
      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Resource not found' }, { status: 404 })
      })

      try {
        await apiClient.get('/not-found')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        expect(apiError.status).toBe(404)
        expect(apiError.message).toBe('Resource not found')
      }
    })

    it('parses error code from response body', async () => {
      globalThis.fetch = vi.fn(async () => {
        return mockResponse({ detail: 'Bad request', code: 'VALIDATION_ERROR' }, { status: 400 })
      })

      try {
        await apiClient.post('/validate', { invalid: true })
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        expect(apiError.code).toBe('VALIDATION_ERROR')
      }
    })

    it('handles non-JSON error responses gracefully', async () => {
      globalThis.fetch = vi.fn(async () => {
        return {
          ok: false,
          status: 500,
          json: async () => {
            throw new Error('Not JSON')
          },
          headers: new Headers(),
        } as Response
      })

      try {
        await apiClient.get('/broken')
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(TalentAgentApiError)
        const apiError = error as TalentAgentApiError
        expect(apiError.status).toBe(500)
        expect(apiError.code).toBe('HTTP_500')
      }
    })

    it('handles 204 No Content response', async () => {
      globalThis.fetch = vi.fn(async () => {
        return {
          ok: true,
          status: 204,
          json: async () => {
            throw new Error('No content')
          },
          headers: new Headers(),
        } as Response
      })

      const result = await apiClient.delete('/resource')

      expect(result).toBeUndefined()
    })
  })

  // ─── URL Construction ──────────────────────────────────────────────────────

  describe('URL construction', () => {
    it('prepends base URL to request path', async () => {
      let capturedUrl: string | undefined

      globalThis.fetch = vi.fn(async (url: RequestInfo | URL) => {
        capturedUrl = url.toString()
        return mockResponse({ data: 'test' })
      })

      await apiClient.get('/users/123')

      expect(capturedUrl).toContain('/users/123')
      expect(apiClient.baseUrl).toBeTruthy()
    })
  })

  // ─── Toast Dispatch ────────────────────────────────────────────────────────

  describe('dispatchToast', () => {
    it('dispatches custom event with payload', () => {
      const handler = vi.fn()
      window.addEventListener(TOAST_EVENT, handler as EventListener)

      const payload: ToastPayload = {
        message: 'Test message',
        type: 'success',
        duration: 3000,
      }

      dispatchToast(payload)

      expect(handler).toHaveBeenCalled()
      const event = handler.mock.calls[0][0] as CustomEvent<ToastPayload>
      expect(event.detail).toEqual(payload)

      window.removeEventListener(TOAST_EVENT, handler as EventListener)
    })
  })
})
