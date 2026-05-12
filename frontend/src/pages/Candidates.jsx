import { useState } from 'react'
import { Search, Plus, MoreHorizontal } from 'lucide-react'
import StatusBadge from '../components/StatusBadge'

const mockCandidates = [
  { id: 1, name: 'Marcus Chen', title: 'Sr. ML Engineer', location: 'San Francisco, CA', status: 'active', roles: 14, applied: 6, interviews: 2, added: 'Mar 15' },
  { id: 2, name: 'Aisha Patel', title: 'VP of Engineering', location: 'New York, NY', status: 'active', roles: 22, applied: 9, interviews: 3, added: 'Mar 12' },
  { id: 3, name: 'Jordan Williams', title: 'Staff Software Engineer', location: 'Austin, TX', status: 'active', roles: 18, applied: 7, interviews: 1, added: 'Mar 10' },
  { id: 4, name: 'Sarah Kim', title: 'Head of AI/ML', location: 'Seattle, WA', status: 'reviewing', roles: 8, applied: 3, interviews: 1, added: 'Mar 8' },
  { id: 5, name: 'Dev Okonkwo', title: 'Platform Lead', location: 'Miami, FL', status: 'active', roles: 11, applied: 4, interviews: 0, added: 'Mar 5' },
  { id: 6, name: 'Lisa Zhang', title: 'Engineering Manager', location: 'Los Angeles, CA', status: 'active', roles: 16, applied: 8, interviews: 2, added: 'Mar 3' },
  { id: 7, name: 'Carlos Rivera', title: 'Principal Engineer', location: 'Chicago, IL', status: 'paused', roles: 5, applied: 2, interviews: 0, added: 'Feb 28' },
  { id: 8, name: 'Emily Nguyen', title: 'Sr. Backend Engineer', location: 'Denver, CO', status: 'active', roles: 20, applied: 10, interviews: 4, added: 'Feb 25' },
  { id: 9, name: 'Raj Krishnamurthy', title: 'CTO / Co-founder', location: 'Boston, MA', status: 'placed', roles: 3, applied: 3, interviews: 2, added: 'Feb 20' },
]

export default function Candidates() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  const filtered = mockCandidates.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(search.toLowerCase()) || c.title.toLowerCase().includes(search.toLowerCase())
    return matchesSearch && (filter === 'all' || c.status === filter)
  })

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <p className="t-body">Manage your talent pipeline</p>
        <button className="btn-primary" style={{ padding: '12px 28px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Plus style={{ width: 14, height: 14 }} /> Add Candidate
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14, color: 'var(--muted)' }} />
          <input type="text" placeholder="Search by name or title..." value={search} onChange={(e) => setSearch(e.target.value)} className="input" style={{ paddingLeft: 38 }} />
        </div>
        {['all', 'active', 'reviewing', 'paused', 'placed'].map((f) => (
          <button key={f} className="tag" onClick={() => setFilter(f)} style={{
            cursor: 'pointer', background: 'transparent',
            borderColor: filter === f ? 'var(--gold)' : undefined,
            color: filter === f ? 'var(--gold)' : undefined,
          }}>
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
        <table className="ta-table">
          <thead>
            <tr>
              <th>Candidate</th><th>Status</th><th style={{ textAlign: 'center' }}>Discovered</th>
              <th style={{ textAlign: 'center' }}>Applied</th><th style={{ textAlign: 'center' }}>Interviews</th><th>Added</th><th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 32, height: 32, borderRadius: '50%', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--gold)' }}>
                        {c.name.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div>
                      <p style={{ color: 'var(--white)', fontWeight: 400 }}>{c.name}</p>
                      <p className="t-label" style={{ marginTop: 1 }}>{c.title} — {c.location}</p>
                    </div>
                  </div>
                </td>
                <td><StatusBadge status={c.status} /></td>
                <td style={{ textAlign: 'center', color: 'var(--white)' }}>{c.roles}</td>
                <td style={{ textAlign: 'center', color: 'var(--white)' }}>{c.applied}</td>
                <td style={{ textAlign: 'center', color: 'var(--white)' }}>{c.interviews}</td>
                <td><span className="t-label">{c.added}</span></td>
                <td><button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}><MoreHorizontal style={{ width: 16, height: 16 }} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <p className="t-body" style={{ textAlign: 'center', padding: 40 }}>No candidates match your search.</p>}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <span className="t-label">Showing {filtered.length} of {mockCandidates.length}</span>
        <span className="t-label">{mockCandidates.filter(c => c.status === 'active').length} active</span>
      </div>
    </div>
  )
}
