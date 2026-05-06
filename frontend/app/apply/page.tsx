'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const ROLES = [
  { value: 'bd_manager', label: 'Business Development Manager' },
  { value: 'operations_manager', label: 'Operations Manager — Managed Offices' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'finance', label: 'Finance' },
  { value: 'it', label: 'Information Technology' },
  { value: 'hr', label: 'Human Resources' },
  { value: 'other', label: 'Other / General Application' },
]

function Input({
  label, id, type = 'text', required = false, value, onChange, placeholder, min, step,
}: {
  label: string; id: string; type?: string; required?: boolean
  value: string; onChange: (v: string) => void; placeholder?: string; min?: number; step?: string
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label
        htmlFor={id}
        style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}
      >
        {label}{required ? <span style={{ color: '#ef4444', marginLeft: 3 }}>*</span> : null}
      </label>
      <input
        id={id}
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        min={min}
        step={step}
        style={{
          width: '100%',
          background: '#111118',
          border: '1px solid #1e1e2e',
          borderRadius: 8,
          color: '#f1f5f9',
          fontSize: 14,
          padding: '10px 12px',
          outline: 'none',
          boxSizing: 'border-box',
          fontFamily: 'inherit',
        }}
      />
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#12121a', border: '1px solid #1e1e2e', borderRadius: 12, padding: '22px 24px', marginBottom: 14 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#4b5563', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 18 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function ApplyPageInner() {
  const params = useSearchParams()
  const preRole = params.get('role') ?? ''

  const [form, setForm] = useState({
    name: '', email: '', phone: '', location: '',
    role: ROLES.find((r) => r.value === preRole) ? preRole : '',
    years_experience: '', current_ctc: '', expected_ctc: '',
    notice_period_days: '', linkedin_url: '', application_answer: '',
  })
  const [resume, setResume] = useState<File | null>(null)
  const [phase, setPhase] = useState<'form' | 'submitting' | 'success' | 'error'>('form')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    if (preRole && ROLES.find((r) => r.value === preRole)) {
      setForm((prev) => ({ ...prev, role: preRole }))
    }
  }, [preRole])

  function set(key: keyof typeof form) {
    return (v: string) => setForm((prev) => ({ ...prev, [key]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.role) { setErrorMsg('Please select a role.'); return }
    setPhase('submitting')
    setErrorMsg('')

    const data = new FormData()
    data.append('name', form.name)
    data.append('email', form.email)
    data.append('role', form.role)
    data.append('source', 'careers_form')
    if (form.phone) data.append('phone', form.phone)
    if (form.location) data.append('location', form.location)
    if (form.years_experience) data.append('years_experience', form.years_experience)
    if (form.current_ctc) data.append('current_ctc', String(Math.round(parseFloat(form.current_ctc) * 100000)))
    if (form.expected_ctc) data.append('expected_ctc', String(Math.round(parseFloat(form.expected_ctc) * 100000)))
    if (form.notice_period_days) data.append('notice_period_days', form.notice_period_days)
    if (form.linkedin_url) data.append('linkedin_url', form.linkedin_url)
    if (form.application_answer) data.append('application_answer', form.application_answer)
    if (resume) data.append('resume', resume)

    try {
      const res = await fetch(`${API_URL}/hr/apply`, { method: 'POST', body: data })
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText)
        throw new Error(text)
      }
      setPhase('success')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Submission failed. Please try again.')
      setPhase('error')
    }
  }

  const selectedRoleLabel = ROLES.find((r) => r.value === form.role)?.label ?? ''

  if (phase === 'success') {
    return (
      <div style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div style={{ fontSize: 52, marginBottom: 20 }}>✅</div>
        <h2 style={{ fontSize: 26, fontWeight: 700, color: '#f1f5f9', margin: '0 0 14px' }}>Application Submitted!</h2>
        <p style={{ color: '#94a3b8', fontSize: 15, lineHeight: 1.7, maxWidth: 480, margin: '0 auto 28px' }}>
          Thank you, <strong style={{ color: '#f1f5f9' }}>{form.name.split(' ')[0]}</strong>! We've received your application
          {selectedRoleLabel ? ` for the ${selectedRoleLabel} role` : ''} at YourCompany.
          We'll review it carefully and reach out within 2–3 business days if your profile matches.
        </p>
        <div style={{ color: '#4b5563', fontSize: 13 }}>hiring@example.com · yourcompany.com</div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Section title="Role">
        <div style={{ marginBottom: 0 }}>
          <label htmlFor="role" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Applying for <span style={{ color: '#ef4444', marginLeft: 3 }}>*</span>
          </label>
          <select
            id="role"
            required
            value={form.role}
            onChange={(e) => set('role')(e.target.value)}
            style={{
              width: '100%',
              background: '#111118',
              border: '1px solid #1e1e2e',
              borderRadius: 8,
              color: form.role ? '#f1f5f9' : '#6b7280',
              fontSize: 14,
              padding: '10px 12px',
              outline: 'none',
              boxSizing: 'border-box',
              fontFamily: 'inherit',
              cursor: 'pointer',
            }}
          >
            <option value="" disabled>Select a role…</option>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>
      </Section>

      <Section title="Personal Details">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Input label="Full Name" id="name" required value={form.name} onChange={set('name')} placeholder="Rahul Sharma" />
          <Input label="Email Address" id="email" type="email" required value={form.email} onChange={set('email')} placeholder="rahul@example.com" />
          <Input label="Phone Number" id="phone" type="tel" value={form.phone} onChange={set('phone')} placeholder="+91 98765 43210" />
          <Input label="Current City" id="location" value={form.location} onChange={set('location')} placeholder="Bangalore" />
        </div>
        <Input label="LinkedIn Profile URL" id="linkedin_url" value={form.linkedin_url} onChange={set('linkedin_url')} placeholder="https://linkedin.com/in/yourprofile" />
      </Section>

      <Section title="Experience & Compensation">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0 16px' }}>
          <Input label="Years of Experience" id="years_experience" type="number" min={0} step="0.5" value={form.years_experience} onChange={set('years_experience')} placeholder="5" />
          <Input label="Current CTC (LPA)" id="current_ctc" type="number" min={0} step="0.5" value={form.current_ctc} onChange={set('current_ctc')} placeholder="12" />
          <Input label="Expected CTC (LPA)" id="expected_ctc" type="number" min={0} step="0.5" value={form.expected_ctc} onChange={set('expected_ctc')} placeholder="18" />
        </div>
        <Input label="Notice Period (days)" id="notice_period_days" type="number" min={0} value={form.notice_period_days} onChange={set('notice_period_days')} placeholder="30" />
      </Section>

      <Section title="Your Application">
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="application_answer" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Why YourCompany? What excites you about this role?
          </label>
          <textarea
            id="application_answer"
            value={form.application_answer}
            onChange={(e) => set('application_answer')(e.target.value)}
            rows={4}
            placeholder="Tell us what draws you to YourCompany and why you're a strong fit for this role…"
            style={{
              width: '100%',
              background: '#111118',
              border: '1px solid #1e1e2e',
              borderRadius: 8,
              color: '#f1f5f9',
              fontSize: 14,
              padding: '10px 12px',
              resize: 'vertical',
              outline: 'none',
              boxSizing: 'border-box',
              fontFamily: 'inherit',
              lineHeight: 1.65,
            }}
          />
        </div>

        <div>
          <label htmlFor="resume" style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Resume (PDF or Word)
          </label>
          <div
            style={{
              border: '1px dashed #1e1e2e',
              borderRadius: 8,
              padding: '20px',
              textAlign: 'center',
              cursor: 'pointer',
              position: 'relative',
            }}
            onClick={() => document.getElementById('resume')?.click()}
          >
            <input
              id="resume"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) => setResume(e.target.files?.[0] ?? null)}
              style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer' }}
            />
            {resume ? (
              <div style={{ color: '#10b981', fontSize: 13, fontWeight: 600 }}>
                ✓ {resume.name}
              </div>
            ) : (
              <div>
                <div style={{ color: '#94a3b8', fontSize: 13 }}>Click to upload your resume</div>
                <div style={{ color: '#4b5563', fontSize: 11, marginTop: 4 }}>PDF, DOC, or DOCX</div>
              </div>
            )}
          </div>
        </div>
      </Section>

      {(phase === 'error' && errorMsg) ? (
        <div style={{ background: '#1f0a0a', border: '1px solid #ef4444', color: '#ef4444', borderRadius: 8, padding: '12px 16px', fontSize: 13, marginBottom: 14 }}>
          {errorMsg}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={phase === 'submitting'}
        style={{
          width: '100%',
          background: phase === 'submitting' ? '#052e16' : '#10b981',
          color: '#fff',
          border: 'none',
          borderRadius: 10,
          padding: '14px 0',
          fontSize: 16,
          fontWeight: 700,
          cursor: phase === 'submitting' ? 'not-allowed' : 'pointer',
          opacity: phase === 'submitting' ? 0.7 : 1,
          letterSpacing: '0.01em',
        }}
      >
        {phase === 'submitting' ? 'Submitting…' : 'Submit Application →'}
      </button>

      <p style={{ textAlign: 'center', color: '#374151', fontSize: 12, marginTop: 14 }}>
        We review every application carefully. Expect a response within 2–3 business days.
      </p>
    </form>
  )
}

export default function ApplyPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0f', color: '#f1f5f9', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Top nav */}
      <div style={{ padding: '16px 32px', borderBottom: '1px solid #1e1e2e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #10b981, #059669)', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 2H6V6H2V2Z" fill="white" opacity="0.9" />
              <path d="M8 2H12V6H8V2Z" fill="white" opacity="0.6" />
              <path d="M2 8H6V12H2V8Z" fill="white" opacity="0.6" />
              <path d="M8 8H12V12H8V8Z" fill="white" opacity="0.9" />
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#f1f5f9' }}>YourCompany</div>
            <div style={{ fontSize: 10, color: '#6b7280', letterSpacing: '0.04em' }}>Careers</div>
          </div>
        </div>
        <a href="/careers" style={{ color: '#94a3b8', fontSize: 13, textDecoration: 'none' }}>
          View all openings →
        </a>
      </div>

      {/* Main content */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '40px 24px 60px' }}>
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: '0 0 8px', color: '#f1f5f9' }}>Apply to YourCompany</h1>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: 14, lineHeight: 1.6 }}>
            We're building India's leading managed office platform. If you're driven, detail-oriented, and want to be part of a fast-growing team — we'd love to hear from you.
          </p>
        </div>

        <Suspense fallback={<div style={{ color: '#94a3b8' }}>Loading form…</div>}>
          <ApplyPageInner />
        </Suspense>
      </div>

      <div style={{ borderTop: '1px solid #1e1e2e', padding: '16px 32px', textAlign: 'center', color: '#374151', fontSize: 12 }}>
        Your Company Legal Name · hiring@example.com
      </div>
    </div>
  )
}
