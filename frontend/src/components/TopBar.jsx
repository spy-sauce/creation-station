import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, Search, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { routes, pageTitles } from '../lib/routes'

export default function TopBar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [showMenu, setShowMenu] = useState(false)
  const title = pageTitles[pathname] || 'Dashboard'

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() || '??'

  const handleLogout = () => { logout(); navigate(routes.login) }

  return (
    <div className="topbar">
      <h1 className="topbar-title">{title}</h1>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Search */}
        <div style={{ position: 'relative' }} className="hidden md:block">
          <Search style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14, color: 'var(--muted)' }} />
          <input type="text" placeholder="Search..." className="input" style={{ paddingLeft: 36, paddingTop: 10, paddingBottom: 10, width: 220, fontSize: 13 }} />
        </div>

        {/* Notifications */}
        <button style={{ position: 'relative', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 8 }}>
          <Bell style={{ width: 16, height: 16, strokeWidth: 1.5 }} />
          <span style={{ position: 'absolute', top: 6, right: 6, width: 6, height: 6, borderRadius: '50%', background: 'var(--gold)' }} />
        </button>

        {/* Avatar + dropdown */}
        <div style={{ position: 'relative' }}>
          <button className="topbar-avatar" onClick={() => setShowMenu(!showMenu)}>
            {initials}
          </button>

          {showMenu && (
            <>
              <div style={{ position: 'fixed', inset: 0, zIndex: 40 }} onClick={() => setShowMenu(false)} />
              <div className="dropdown">
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
                  <p style={{ color: 'var(--white)', fontSize: 13, fontWeight: 400 }}>{user?.name || 'User'}</p>
                  <p style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>{user?.email}</p>
                </div>
                <button className="dropdown-item" onClick={handleLogout}>
                  <LogOut style={{ width: 14, height: 14, strokeWidth: 1.5 }} />
                  Log out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
