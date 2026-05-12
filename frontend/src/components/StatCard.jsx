export default function StatCard({ label, value, change, icon: Icon }) {
  return (
    <div className="card-hover" style={{ padding: '28px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <Icon style={{ width: 18, height: 18, color: 'var(--gold)', strokeWidth: 1.5 }} />
        {change !== 0 && change !== undefined && (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: change > 0 ? 'var(--emerald)' : 'var(--rose)' }}>
            {change > 0 ? '+' : ''}{change}%
          </span>
        )}
      </div>
      <div className="stat-num" style={{ fontSize: 32 }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
