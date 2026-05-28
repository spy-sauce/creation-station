/**
 * Frontend logging utility.
 *
 * Per CLAUDE.md: No console.log — use frontend logging utility.
 * This module wraps console methods with structured output for consistency.
 * In production, these logs can be piped to an observability service.
 *
 * @license Apache-2.0
 * @copyright VibeSpace LLC
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogPayload {
  [key: string]: unknown
}

/**
 * Check if debug logging is enabled.
 * Per NUTRIENTS.md: Env vars use VITE_* prefix.
 */
const DEBUG_ENABLED = import.meta.env.DEV || import.meta.env.VITE_DEBUG === 'true'

/**
 * Format a log message with timestamp and structured payload.
 */
function formatLog(level: LogLevel, event: string, payload?: LogPayload): string {
  const timestamp = new Date().toISOString()
  const payloadStr = payload ? ` ${JSON.stringify(payload)}` : ''
  return `[${timestamp}] ${level.toUpperCase()} ${event}${payloadStr}`
}

/**
 * Structured logger for frontend code.
 *
 * Usage:
 * ```ts
 * import { log } from '../lib/logger'
 *
 * log.info('sse.connected', { channel: 'agent.status.discovery' })
 * log.error('sse.parse_error', { error: 'Invalid JSON' })
 * ```
 */
export const log = {
  /**
   * Log debug-level message.
   * Only outputs in development or when VITE_DEBUG=true.
   */
  debug(event: string, payload?: LogPayload): void {
    if (DEBUG_ENABLED) {
      // eslint-disable-next-line no-console
      console.debug(formatLog('debug', event, payload))
    }
  },

  /**
   * Log info-level message.
   */
  info(event: string, payload?: LogPayload): void {
    // eslint-disable-next-line no-console
    console.info(formatLog('info', event, payload))
  },

  /**
   * Log warning-level message.
   */
  warn(event: string, payload?: LogPayload): void {
    // eslint-disable-next-line no-console
    console.warn(formatLog('warn', event, payload))
  },

  /**
   * Log error-level message.
   */
  error(event: string, payload?: LogPayload): void {
    // eslint-disable-next-line no-console
    console.error(formatLog('error', event, payload))
  },
}

export default log
