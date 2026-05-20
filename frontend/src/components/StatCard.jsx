/**
 * StatCard — Primitive card treatment for metrics display
 *
 * Per HYPHA-DESIGN-CORE.md, this encodes the canonical stat card treatment:
 * - card-hover class for gold top-border animation
 * - stat-num class for large serif numbers in gold
 * - stat-label class for monospace labels below
 * - All colors via CSS custom properties (no hex literals)
 *
 * @param {Object} props
 * @param {string} props.label - The metric label (displayed below the value)
 * @param {string|number} props.value - The metric value (large display)
 * @param {number} [props.change] - Optional percentage change (+/- indicator)
 * @param {React.ComponentType} props.icon - Lucide icon component
 */
export default function StatCard({ label, value, change, icon: Icon }) {
  return (
    <div className="card-hover" style={{ padding: '28px 24px' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16
      }}>
        <Icon style={{
          width: 18,
          height: 18,
          color: 'var(--gold)',
          strokeWidth: 1.5
        }} />
        {change !== 0 && change !== undefined && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: change > 0 ? 'var(--status-success)' : 'var(--status-error)'
          }}>
            {change > 0 ? '+' : ''}{change}%
          </span>
        )}
      </div>
      <div className="stat-num" style={{ fontSize: 32 }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
