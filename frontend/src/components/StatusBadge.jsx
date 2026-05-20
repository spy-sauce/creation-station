/**
 * StatusBadge — Canonical status-to-color mapping
 *
 * This is the ONLY place status colors are mapped. Per HYPHA-DESIGN-CORE.md,
 * no other component duplicates this logic. All status display flows through
 * this component.
 *
 * Status colors use CSS custom properties from index.css:
 * - --status-success: Completed, approved, active, placed
 * - --status-warning: Reviewing, interviewing, in-progress
 * - --status-error: Failed, rejected, errors
 * - --status-info: Discovered, new, informational
 * - --status-pending: Queued, waiting
 * - --status-hot: Hot picks, urgent opportunities
 * - --gold: Applied, sent (brand accent for positive actions)
 */

/**
 * Canonical status-to-color map
 * Maps status strings to CSS custom property values
 */
const statusColors = {
  // Success states (green)
  active: 'var(--status-success)',
  approved: 'var(--status-success)',
  completed: 'var(--status-success)',
  placed: 'var(--status-success)',
  running: 'var(--status-success)',
  tracked: 'var(--status-success)',

  // Warning states (yellow)
  reviewing: 'var(--status-warning)',
  interviewing: 'var(--status-warning)',
  parsing: 'var(--status-warning)',
  tailoring: 'var(--status-warning)',
  researching: 'var(--status-warning)',
  composing: 'var(--status-warning)',
  retrying: 'var(--status-warning)',

  // Error states (red)
  failed: 'var(--status-error)',
  rejected: 'var(--status-error)',
  dead: 'var(--status-error)',
  bounced: 'var(--status-error)',

  // Info states (blue)
  discovered: 'var(--status-info)',
  new: 'var(--status-info)',
  dispatched: 'var(--status-info)',

  // Pending states (purple)
  queued: 'var(--status-pending)',
  paused: 'var(--status-pending)',
  awaiting_review: 'var(--status-pending)',
  draft: 'var(--status-pending)',

  // Hot states (orange)
  hot: 'var(--status-hot)',
  requires_manual: 'var(--status-hot)',

  // Brand accent states (gold)
  applied: 'var(--gold)',
  sent: 'var(--gold)',
  submitted: 'var(--gold)',
  replied: 'var(--gold)',

  // Muted states (text-muted)
  idle: 'var(--text-muted)',
}

/**
 * StatusBadge component
 *
 * @param {Object} props
 * @param {string} props.status - The status string to display (case-insensitive)
 * @returns {JSX.Element}
 */
export default function StatusBadge({ status }) {
  // Normalize status to lowercase for consistent lookup
  const normalizedStatus = status?.toLowerCase().replace(/-/g, '_')
  const color = statusColors[normalizedStatus] || 'var(--text-muted)'

  // Display the original status (preserving case) or normalized version
  const displayStatus = status?.replace(/_/g, ' ') || 'unknown'

  return (
    <span className="status-badge" style={{ color, borderColor: color }}>
      <span className="dot" />
      {displayStatus}
    </span>
  )
}

/**
 * Export the status colors map for edge cases where components
 * need to access the color directly (e.g., custom charts)
 */
export { statusColors }
