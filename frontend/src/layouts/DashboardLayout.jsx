import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import TopBar from '../components/TopBar'

export default function DashboardLayout() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--black)' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar />
        <main style={{ flex: 1, overflowY: 'auto', padding: 32 }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
