import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Users, GitPullRequestArrow, ClipboardCheck, BarChart3, Settings, Zap } from 'lucide-react'

const nav = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Overview', end: true },
  { to: '/dashboard/candidates', icon: Users, label: 'Candidates' },
  { to: '/dashboard/pipeline', icon: GitPullRequestArrow, label: 'Pipeline' },
  { to: '/dashboard/review', icon: ClipboardCheck, label: 'Review Queue' },
  { to: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <a href="/dashboard" className="t-label-gold" style={{ textDecoration: 'none' }}>Talent Agent</a>
      </div>

      <nav className="sidebar-nav">
        {nav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
            <item.icon />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/dashboard/settings" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Settings />
          Settings
        </NavLink>
        <div style={{ margin: '16px 16px 0', padding: '14px 16px', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Zap style={{ width: 12, height: 12, color: 'var(--gold)' }} />
            <span className="t-label-gold">Agent Status</span>
          </div>
          <p style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>System ready</p>
        </div>
      </div>
    </aside>
  )
}
