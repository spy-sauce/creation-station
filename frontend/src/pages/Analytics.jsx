import { Users, Briefcase, Send, TrendingUp, Target, Clock } from 'lucide-react'
import StatCard from '../components/StatCard'

const topStats = [
  { label: 'Total Placements', value: '23', change: 15, icon: TrendingUp },
  { label: 'Avg Time to Place', value: '18d', change: -12, icon: Clock },
  { label: 'App → Interview', value: '34%', change: 8, icon: Target },
  { label: 'Interview → Place', value: '41%', change: 5, icon: Users },
]

const months = [
  { month: 'Oct', discovered: 180, applied: 45, interviews: 12, placed: 2 },
  { month: 'Nov', discovered: 220, applied: 58, interviews: 18, placed: 3 },
  { month: 'Dec', discovered: 195, applied: 52, interviews: 15, placed: 4 },
  { month: 'Jan', discovered: 280, applied: 72, interviews: 24, placed: 5 },
  { month: 'Feb', discovered: 310, applied: 85, interviews: 28, placed: 5 },
  { month: 'Mar', discovered: 340, applied: 98, interviews: 32, placed: 6 },
]

const sources = [
  { name: 'Greenhouse', count: 124, pct: 35 },
  { name: 'Lever', count: 89, pct: 25 },
  { name: 'LinkedIn', count: 71, pct: 20 },
  { name: 'Company websites', count: 46, pct: 13 },
  { name: 'Other', count: 25, pct: 7 },
]

export default function Analytics() {
  const max = Math.max(...months.map(d => d.discovered))

  return (
    <div className="fade-in" style={{ maxWidth: 1100 }}>
      <p className="t-body" style={{ marginBottom: 24 }}>Track placement performance and pipeline health.</p>

      <div className="grid-border" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 32 }}>
        {topStats.map((s, i) => <StatCard key={i} {...s} />)}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Chart */}
        <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)', padding: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
            <span className="t-label-gold">Pipeline Activity (6 Months)</span>
            <div style={{ display: 'flex', gap: 16 }}>
              {[{ l: 'Discovered', o: 0.15 }, { l: 'Applied', o: 0.3 }, { l: 'Interviews', o: 0.5 }, { l: 'Placed', o: 1 }].map(x => (
                <span key={x.l} className="t-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 8, height: 8, background: `rgba(201,168,76,${x.o})` }} />{x.l}
                </span>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, height: 180 }}>
            {months.map(d => (
              <div key={d.month} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <div style={{ width: '100%', display: 'flex', gap: 2, alignItems: 'flex-end', height: 160 }}>
                  <div style={{ flex: 1, height: `${(d.discovered / max) * 100}%`, background: 'rgba(201,168,76,0.15)' }} />
                  <div style={{ flex: 1, height: `${(d.applied / max) * 100}%`, background: 'rgba(201,168,76,0.3)' }} />
                  <div style={{ flex: 1, height: `${(d.interviews / max) * 100}%`, background: 'rgba(201,168,76,0.5)' }} />
                  <div style={{ flex: 1, height: `${(d.placed / max) * 100}%`, background: 'var(--gold)' }} />
                </div>
                <span className="t-label">{d.month}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sources */}
        <div style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
          <div className="section-label" style={{ padding: '16px 20px', marginBottom: 0 }}>Top Sources</div>
          <div style={{ padding: 20 }}>
            {sources.map(s => (
              <div key={s.name} style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ color: 'var(--white)', fontSize: 14, fontWeight: 300 }}>{s.name}</span>
                  <span className="t-label">{s.count} ({s.pct}%)</span>
                </div>
                <div style={{ height: 4, background: 'var(--surface)', overflow: 'hidden' }}>
                  <div style={{ width: `${s.pct}%`, height: '100%', background: 'var(--gold)', transition: 'width 0.4s ease' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tables */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {[
          { title: 'Top Companies', icon: Briefcase, rows: [
            ['Stripe', 12, 3, '25%'], ['Vercel', 8, 2, '25%'], ['Figma', 10, 2, '20%'], ['Anthropic', 6, 2, '33%'], ['Linear', 5, 1, '20%'],
          ]},
          { title: 'Top Candidates', icon: Send, rows: [
            ['Emily Nguyen', 10, 4, '40%'], ['Raj K.', 3, 3, '100%'], ['Aisha Patel', 9, 2, '22%'], ['Marcus Chen', 6, 2, '33%'], ['Lisa Zhang', 8, 1, '13%'],
          ]},
        ].map(t => (
          <div key={t.title} style={{ background: 'var(--off-black)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <t.icon style={{ width: 12, height: 12, color: 'var(--gold)' }} />
              <span className="t-label-gold">{t.title}</span>
            </div>
            <table className="ta-table">
              <thead><tr><th>Name</th><th style={{ textAlign: 'center' }}>Applied</th><th style={{ textAlign: 'center' }}>Placed</th><th style={{ textAlign: 'right' }}>Rate</th></tr></thead>
              <tbody>
                {t.rows.map((r, i) => (
                  <tr key={i}>
                    <td style={{ color: 'var(--white)', fontWeight: 400 }}>{r[0]}</td>
                    <td style={{ textAlign: 'center' }}>{r[1]}</td>
                    <td style={{ textAlign: 'center', color: 'var(--gold)' }}>{r[2]}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 11 }}>{r[3]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  )
}
