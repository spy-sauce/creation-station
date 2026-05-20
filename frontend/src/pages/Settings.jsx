import { Building2, User, Bell, Key } from 'lucide-react'

const sections = [
  { icon: Building2, title: 'Agency Profile', description: 'Manage your agency name, logo, and contact information.', fields: [
    { label: 'Agency Name', value: 'VibeSpace LLC', type: 'text' },
    { label: 'Contact Email', value: 'spy@seanyoung.biz', type: 'email' },
    { label: 'Website', value: 'https://seanyoung.biz', type: 'url' },
  ]},
  { icon: User, title: 'Account', description: 'Your personal account settings.', fields: [
    { label: 'Full Name', value: 'Sean Young', type: 'text' },
    { label: 'Email', value: 'spy@seanyoung.biz', type: 'email' },
    { label: 'Role', value: 'Admin', type: 'text', disabled: true },
  ]},
  { icon: Bell, title: 'Notifications', description: 'Configure when and how you get notified.', toggles: [
    { label: 'New roles discovered', on: true },
    { label: 'Application submitted', on: true },
    { label: 'Interview scheduled', on: true },
    { label: 'Agent failures', on: true },
    { label: 'Weekly digest email', on: false },
  ]},
  { icon: Key, title: 'API Keys', description: 'Manage integration credentials.', fields: [
    { label: 'Anthropic API Key', value: 'sk-ant-•••••••••••••', type: 'password' },
    { label: 'Hunter.io API Key', value: 'Not configured', type: 'password', placeholder: true },
  ]},
]

export default function Settings() {
  return (
    <div className="fade-in" style={{ maxWidth: 700 }}>
      <p className="t-body" style={{ marginBottom: 24 }}>Manage your agency, account, and integration settings.</p>

      {sections.map((s) => (
        <div key={s.title} style={{ background: 'var(--off-black)', border: '1px solid var(--border)', marginBottom: 24 }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 14 }}>
            <s.icon style={{ width: 16, height: 16, color: 'var(--gold)', strokeWidth: 1.5 }} />
            <div>
              <span className="t-label-gold">{s.title}</span>
              <p className="t-body" style={{ marginTop: 2, fontSize: 13 }}>{s.description}</p>
            </div>
          </div>

          <div style={{ padding: 24 }}>
            {s.fields?.map((f) => (
              <div key={f.label} style={{ marginBottom: 16 }}>
                <label className="input-label">{f.label}</label>
                <input type={f.type} defaultValue={f.placeholder ? '' : f.value} placeholder={f.placeholder ? f.value : ''} disabled={f.disabled} className="input" />
              </div>
            ))}

            {s.toggles?.map((t) => (
              <div key={t.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0' }}>
                <span style={{ color: 'var(--white)', fontSize: 14, fontWeight: 300 }}>{t.label}</span>
                <div style={{
                  width: 36, height: 20, borderRadius: 10, position: 'relative', cursor: 'pointer',
                  background: t.on ? 'var(--gold)' : 'var(--surface)',
                  border: t.on ? 'none' : '1px solid var(--border)',
                }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', position: 'absolute', top: 2,
                    left: t.on ? 18 : 2,
                    background: t.on ? 'var(--bg-primary)' : 'var(--text-muted)',
                    transition: 'left 0.2s ease',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button className="btn-primary">Save changes →</button>
      </div>
    </div>
  )
}
