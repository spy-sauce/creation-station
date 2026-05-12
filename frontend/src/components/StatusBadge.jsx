const colors = {
  active: 'var(--emerald)', placed: 'var(--gold)', reviewing: 'var(--amber)',
  paused: 'var(--muted)', idle: 'var(--muted)', new: 'var(--gold-light)',
  applied: 'var(--gold)', interviewing: 'var(--amber)', rejected: 'var(--rose)',
  discovered: 'var(--gold-light)', approved: 'var(--emerald)', sent: 'var(--gold)',
  running: 'var(--emerald)', queued: 'var(--muted)', failed: 'var(--rose)',
}

export default function StatusBadge({ status }) {
  const c = colors[status] || 'var(--muted)'
  return (
    <span className="status-badge" style={{ color: c, borderColor: c }}>
      <span className="dot" />
      {status}
    </span>
  )
}
