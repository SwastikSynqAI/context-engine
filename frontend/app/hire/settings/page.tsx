'use client'

import { useEffect, useState, useCallback } from 'react'
import { getHireConfig, updateHireConfig, HireConfig } from '../../../lib/hire-api'

type FieldDef = { key: keyof HireConfig; label: string; type: 'number' | 'text'; section: string }

const FIELDS: FieldDef[] = [
  { key: 'hr_resume_score_threshold', label: 'Resume score threshold (0–100)', type: 'number', section: 'Pipeline' },
  { key: 'hr_screen_score_threshold', label: 'Screen score threshold (0–100)', type: 'number', section: 'Pipeline' },
  { key: 'hr_test_pass_threshold', label: 'Test pass threshold (0–100)', type: 'number', section: 'Pipeline' },
  { key: 'hiring_email', label: 'Hiring from-email', type: 'text', section: 'Email' },
  { key: 'admin_notify_email', label: 'Admin notify email', type: 'text', section: 'Email' },
  { key: 'frontend_url', label: 'Frontend base URL', type: 'text', section: 'Email' },
  { key: 'hod_bd_email', label: 'HOD — Business Development', type: 'text', section: 'Department Heads' },
  { key: 'hod_ops_email', label: 'HOD — Operations & Admin', type: 'text', section: 'Department Heads' },
  { key: 'hod_it_email', label: 'HOD — IT', type: 'text', section: 'Department Heads' },
  { key: 'hod_ai_email', label: 'HOD — AI / Data', type: 'text', section: 'Department Heads' },
  { key: 'hod_marketing_email', label: 'HOD — Marketing', type: 'text', section: 'Department Heads' },
  { key: 'hod_finance_email', label: 'HOD — Finance', type: 'text', section: 'Department Heads' },
  { key: 'hod_hr_email', label: 'HOD — HR (fallback)', type: 'text', section: 'Department Heads' },
  { key: 'calendly_default_link', label: 'Calendly — Default link', type: 'text', section: 'Calendly' },
  { key: 'calendly_bd_link', label: 'Calendly — BD interviews', type: 'text', section: 'Calendly' },
  { key: 'calendly_ops_link', label: 'Calendly — Ops interviews', type: 'text', section: 'Calendly' },
]

const SECTIONS = ['Pipeline', 'Email', 'Department Heads', 'Calendly']
type SaveStatus = 'idle' | 'saving' | 'success' | 'error'

export default function HireSettingsPage() {
  const [draft, setDraft] = useState<HireConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<SaveStatus>('idle')

  const load = useCallback(async () => {
    setLoading(true)
    try { const cfg = await getHireConfig(); setDraft(cfg) } catch { } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleSave() {
    if (!draft) return
    setStatus('saving')
    try { await updateHireConfig(draft); setStatus('success') } catch { setStatus('error') }
  }

  function handleChange(key: keyof HireConfig, value: string) {
    setStatus('idle')
    setDraft((prev) => {
      if (!prev) return prev
      const field = FIELDS.find((f) => f.key === key)
      return field?.type === 'number' ? { ...prev, [key]: value === '' ? 0 : Number(value) } : { ...prev, [key]: value }
    })
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#ffffff', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ padding: '20px 28px', borderBottom: '1px solid #1f1f1f', background: '#0d0d0d' }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#ffffff' }}>HR Settings</h1>
        <p style={{ margin: '4px 0 0', color: '#555', fontSize: 13 }}>Configure hiring pipeline thresholds and email addresses.</p>
      </div>

      <div style={{ padding: '28px', maxWidth: 560 }}>
        {loading ? (
          <div style={{ color: '#555', fontSize: 14 }}>Loading settings…</div>
        ) : draft ? (
          <div>
            {SECTIONS.map((section) => (
              <div key={section} style={{ background: '#111111', border: '1px solid #1f1f1f', borderRadius: 12, padding: '20px 22px', marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#555', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 16 }}>{section}</div>
                {FIELDS.filter((f) => f.section === section).map((field) => (
                  <div key={field.key} style={{ marginBottom: 14 }}>
                    <label htmlFor={field.key} style={{ display: 'block', fontSize: 12, color: '#888', fontWeight: 600, marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{field.label}</label>
                    <input
                      id={field.key} type={field.type} value={String(draft[field.key] ?? '')}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                      min={field.type === 'number' ? 0 : undefined} max={field.type === 'number' ? 100 : undefined}
                      style={{ width: '100%', background: '#0a0a0a', border: '1px solid #2a2a2a', borderRadius: 8, color: '#ffffff', fontSize: 14, padding: '9px 12px', outline: 'none', boxSizing: 'border-box' }}
                    />
                  </div>
                ))}
              </div>
            ))}

            {status === 'success' ? <div style={{ background: '#052e16', border: '1px solid #10b981', color: '#10b981', borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16 }}>Settings saved.</div> : null}
            {status === 'error' ? <div style={{ background: '#1f0a0a', border: '1px solid #ef4444', color: '#ef4444', borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16 }}>Failed to save.</div> : null}

            <button
              onClick={handleSave} disabled={status === 'saving'}
              style={{ background: status === 'saving' ? '#1f1f1f' : '#ff2d78', color: '#ffffff', border: 'none', borderRadius: 8, padding: '10px 24px', fontSize: 14, fontWeight: 600, cursor: status === 'saving' ? 'not-allowed' : 'pointer', opacity: status === 'saving' ? 0.7 : 1 }}
            >
              {status === 'saving' ? 'Saving…' : 'Save Settings'}
            </button>
          </div>
        ) : (
          <div style={{ color: '#ef4444', fontSize: 14 }}>Failed to load settings.</div>
        )}
      </div>
    </div>
  )
}
