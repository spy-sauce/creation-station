/**
 * SSE Event Stream client — subscribeAgentStatus via EventSource.
 *
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS:
 * - Symbol: subscribeAgentStatus owned by api-client-agent
 * - File path: frontend/src/api/events.ts
 *
 * Per HYPHA-API-CLIENT:
 * - subscribeAgentStatus(channel, onMessage) via EventSource
 * - Returns a cleanup function that calls eventSource.close()
 * - EventSource auto-reconnects on connection loss (browser native behavior)
 *
 * SSE endpoint contract (GET /events/stream):
 * - Query param: channel (agent.status.discovery | agent.status.application)
 * - Headers: Authorization: Bearer <jwt>
 * - Response: text/event-stream
 * - Format: data: {json}\n\n for each message
 * - Heartbeat: :ping\n\n every 15s
 * - Backpressure: event: slow_client\ndata: {"dropped": N}\n\n
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

import { getToken } from './client'
import { log } from '../lib/logger'

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * Allowed SSE channels.
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS.
 */
export type AllowedSSEChannel =
  | 'agent.status.discovery'
  | 'agent.status.application'

/**
 * Job source type (for CRAWL_SOURCE_COMPLETE events).
 * Per NUTRIENTS.md DATA_CONTRACTS.
 */
export type JobSource = 'greenhouse' | 'lever' | 'ashby' | 'workday'

/**
 * Discovery event types published to agent.status.discovery.
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS.
 */
export type DiscoveryEventType =
  | 'RUN_STARTED'
  | 'CANDIDATE_LOADED'
  | 'PROFILE_BUILT'
  | 'MANIFEST_BUILT'
  | 'CRAWL_SOURCE_COMPLETE'
  | 'CRAWL_COMPLETE'
  | 'SCORING_COMPLETE'
  | 'RUN_COMPLETE'
  | 'RUN_FAILED'
  | 'DAILY_TASK_DEAD'
  | 'CRAWL_STATUS'
  | 'DIGEST_READY'

/**
 * Discovery status event payload.
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS.
 */
export interface DiscoveryStatusEvent {
  /** Event type (SCREAMING_SNAKE_CASE) */
  event: DiscoveryEventType
  /** Candidate UUID */
  candidate_id: string
  /** ISO-8601 UTC timestamp */
  timestamp: string
  /** Present for CRAWL_SOURCE_COMPLETE */
  source?: JobSource
  /** Present for CRAWL_SOURCE_COMPLETE, CRAWL_STATUS */
  jobs_found?: number
  jobs_discovered?: number
  jobs_scored?: number
  /** Present for RUN_FAILED, DAILY_TASK_DEAD, CRAWL_STATUS */
  error?: string
  /** Present for CRAWL_STATUS */
  crawl_run_id?: string
  status?: string
  /** Present for DIGEST_READY */
  digest_id?: string
  run_date?: string
  total_discovered?: number
  total_scored?: number
  top_picks_count?: number
  hot_picks_count?: number
}

/**
 * Application event types published to agent.status.application.
 */
export type ApplicationEventType =
  | 'APPLICATION_STATUS'
  | 'PIPELINE_STATUS'
  | 'APPLICATION_STARTED'
  | 'JD_PARSED'
  | 'RESUME_TAILORED'
  | 'COMPANY_RESEARCHED'
  | 'CONTACT_FOUND'
  | 'EMAIL_DRAFTED'
  | 'APPROVED_FOR_SUBMISSION'
  | 'SUBMITTED'
  | 'EMAIL_SENT'
  | 'REJECTED'
  | 'PIPELINE_FAILED'

/**
 * Application status event payload.
 */
export interface ApplicationStatusEvent {
  /** Event type (SCREAMING_SNAKE_CASE) */
  event: ApplicationEventType
  /** Pipeline UUID */
  pipeline_id: string
  /** Candidate UUID */
  candidate_id?: string
  /** Pipeline status string */
  status: string
  /** ISO-8601 UTC timestamp */
  timestamp: string
  /** Additional details */
  details?: Record<string, unknown>
}

/**
 * Union type for all SSE event payloads.
 */
export type SSEEventPayload = DiscoveryStatusEvent | ApplicationStatusEvent

/**
 * Slow client warning event.
 * Per NUTRIENTS.md §ITER-4 CONTRACT EXTENSIONS.
 */
export interface SlowClientEvent {
  /** Number of messages dropped due to slow client */
  dropped: number
}

/**
 * Cleanup function returned by subscribeAgentStatus.
 */
export type UnsubscribeFn = () => void

/**
 * Callback for SSE messages.
 */
export type SSEMessageCallback<T = SSEEventPayload> = (event: T) => void

/**
 * Callback for SSE errors.
 */
export type SSEErrorCallback = (error: Event) => void

/**
 * Callback for slow client warnings.
 */
export type SlowClientCallback = (event: SlowClientEvent) => void

/**
 * Options for subscribeAgentStatus.
 */
export interface SubscribeOptions {
  /** Callback when a slow_client event is received */
  onSlowClient?: SlowClientCallback
  /** Callback when connection errors occur */
  onError?: SSEErrorCallback
  /** Callback when connection opens */
  onOpen?: () => void
}

// ─── Constants ────────────────────────────────────────────────────────────────

/**
 * Base URL for SSE endpoint.
 * Per NUTRIENTS.md: Env vars use VITE_* prefix per Vite's import.meta.env convention.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/**
 * SSE endpoint path.
 * Per backend/api/events.py: GET /events/stream?channel=...
 */
const SSE_ENDPOINT = '/events/stream'

// ─── SSE Client ───────────────────────────────────────────────────────────────

/**
 * Subscribe to real-time agent status events via Server-Sent Events.
 *
 * Uses native EventSource for automatic reconnection on connection loss.
 * The browser handles reconnection transparently — no manual retry logic needed.
 *
 * Per HYPHA-API-CLIENT acceptance criteria:
 * - subscribeAgentStatus('agent.status.discovery', callback) opens EventSource
 * - Calls callback on each SSE data frame
 * - EventSource auto-reconnects on connection loss (browser native behavior)
 * - Returns cleanup function that calls eventSource.close()
 *
 * Per NUTRIENTS.md API_CONTRACTS:
 * - Endpoint: GET /events/stream?channel=...
 * - Headers: Authorization: Bearer <jwt>
 * - Allowed channels: agent.status.discovery, agent.status.application
 *
 * @param channel - SSE channel to subscribe to
 * @param onMessage - Callback invoked with parsed event payload on each message
 * @param options - Optional callbacks for errors, slow client warnings, and connection open
 * @returns Cleanup function that closes the EventSource connection
 *
 * @example
 * ```ts
 * // Subscribe to discovery events
 * const unsubscribe = subscribeAgentStatus(
 *   'agent.status.discovery',
 *   (event) => {
 *     console.log('Discovery event:', event.event, event.candidate_id)
 *   },
 *   {
 *     onSlowClient: ({ dropped }) => {
 *       console.warn(`Slow client: ${dropped} messages dropped`)
 *     },
 *     onError: (error) => {
 *       console.error('SSE connection error:', error)
 *     },
 *   }
 * )
 *
 * // Later, cleanup
 * unsubscribe()
 * ```
 */
export function subscribeAgentStatus<T = SSEEventPayload>(
  channel: AllowedSSEChannel,
  onMessage: SSEMessageCallback<T>,
  options: SubscribeOptions = {}
): UnsubscribeFn {
  const { onSlowClient, onError, onOpen } = options

  // Build SSE URL with channel parameter
  const url = new URL(`${API_BASE_URL}${SSE_ENDPOINT}`, window.location.origin)
  url.searchParams.set('channel', channel)

  // Get JWT for authorization
  const token = getToken()

  // NOTE: Native EventSource does not support custom headers.
  // The backend must accept the token via query param OR
  // we use EventSourcePolyfill/fetch-based SSE for auth.
  // Per the backend implementation, it uses Depends(get_current_user)
  // which reads from Authorization header.
  //
  // Solution: Use EventSource with polyfill pattern via query param fallback
  // or use fetch-based SSE. For now, we append token as query param
  // and the backend should support both header and query param auth.
  //
  // Per HYPHA-API-CLIENT notes: uses native EventSource.
  // If auth via header is required, consider @microsoft/fetch-event-source.
  // For MVP, we use query param token.
  if (token) {
    url.searchParams.set('token', token)
  }

  log.info('sse.subscribing', { channel, url: url.toString() })

  // Create EventSource connection
  const eventSource = new EventSource(url.toString())

  // Handle connection open
  eventSource.onopen = () => {
    log.info('sse.connected', { channel })
    onOpen?.()
  }

  // Handle incoming messages (default event type)
  eventSource.onmessage = (messageEvent: MessageEvent) => {
    try {
      const data = JSON.parse(messageEvent.data) as T
      onMessage(data)
    } catch (parseError) {
      log.error('sse.parse_error', {
        channel,
        error: String(parseError),
        data: messageEvent.data,
      })
    }
  }

  // Handle slow_client event (custom event type)
  eventSource.addEventListener('slow_client', (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data) as SlowClientEvent
      log.warn('sse.slow_client', { channel, dropped: data.dropped })
      onSlowClient?.(data)
    } catch (parseError) {
      log.error('sse.slow_client_parse_error', {
        channel,
        error: String(parseError),
      })
    }
  })

  // Handle connection errors
  eventSource.onerror = (error: Event) => {
    // EventSource auto-reconnects, so this may fire during reconnection attempts
    // ReadyState: 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
    if (eventSource.readyState === EventSource.CLOSED) {
      log.error('sse.connection_closed', { channel })
    } else {
      log.warn('sse.connection_error', {
        channel,
        readyState: eventSource.readyState,
      })
    }
    onError?.(error)
  }

  // Return cleanup function
  return () => {
    log.info('sse.unsubscribing', { channel })
    eventSource.close()
  }
}

/**
 * Subscribe to discovery engine status events.
 *
 * Convenience wrapper for subscribeAgentStatus with the discovery channel.
 *
 * @param onMessage - Callback invoked with DiscoveryStatusEvent on each message
 * @param options - Optional callbacks for errors and slow client warnings
 * @returns Cleanup function that closes the EventSource connection
 *
 * @example
 * ```ts
 * const unsubscribe = subscribeDiscoveryEvents((event) => {
 *   switch (event.event) {
 *     case 'RUN_STARTED':
 *       showToast('Discovery run started')
 *       break
 *     case 'RUN_COMPLETE':
 *       showToast('Discovery complete!')
 *       refreshDigest()
 *       break
 *     case 'RUN_FAILED':
 *       showError(`Discovery failed: ${event.error}`)
 *       break
 *   }
 * })
 * ```
 */
export function subscribeDiscoveryEvents(
  onMessage: SSEMessageCallback<DiscoveryStatusEvent>,
  options?: SubscribeOptions
): UnsubscribeFn {
  return subscribeAgentStatus<DiscoveryStatusEvent>(
    'agent.status.discovery',
    onMessage,
    options
  )
}

/**
 * Subscribe to application pipeline status events.
 *
 * Convenience wrapper for subscribeAgentStatus with the application channel.
 *
 * @param onMessage - Callback invoked with ApplicationStatusEvent on each message
 * @param options - Optional callbacks for errors and slow client warnings
 * @returns Cleanup function that closes the EventSource connection
 *
 * @example
 * ```ts
 * const unsubscribe = subscribeApplicationEvents((event) => {
 *   if (event.pipeline_id === currentPipelineId) {
 *     updatePipelineStatus(event.status)
 *   }
 * })
 * ```
 */
export function subscribeApplicationEvents(
  onMessage: SSEMessageCallback<ApplicationStatusEvent>,
  options?: SubscribeOptions
): UnsubscribeFn {
  return subscribeAgentStatus<ApplicationStatusEvent>(
    'agent.status.application',
    onMessage,
    options
  )
}
