'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  getApplication,
  advanceApplication,
  rejectApplication,
  generateOffer,
  offerDownloadUrl,
  sendOfferEmail,
  scheduleInterview,
  hrDecision,
  ApplicationDetail,
} from '../../../../lib/hire-api'

function scoreColor(score: number | null): string {
  if (score === null) return '#6b7280'
  if (score >= 70) return '#10b981'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  const color = scoreColor(score)
  const pct = score !== null ? Math.min(100, Math.max(0, score)) : 0
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: '#94a3b8' }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color }}>
          {score !== null ? score : '—'}
        </span>
      </div>
      <div style={{ height: 6, background: '#1f1f1f', borderRadius: 999, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 999,
            transition: 'width 0.4s',
          }}
        />
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 14, color: '#f1f5f9' }}>{value !== null && value !== undefined && value !== '' ? value : <span style={{ color: '#6b7280' }}>—</span>}</div>
    </div>
  )
}

function Toast({ message, type, onDone }: { message: string; type: 'success' | 'error'; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        background: type === 'success' ? '#052e16' : '#1f0a0a',
        border: `1px solid ${type === 'success' ? '#10b981' : '#ef4444'}`,
        color: type === 'success' ? '#10b981' : '#ef4444',
        padding: '12px 20px',
        borderRadius: 10,
        fontSize: 14,
        fontWeight: 500,
        zIndex: 1000,
        boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
      }}
    >
      {message}
    </div>
  )
}

function formatCTC(val: string | number | null): string {
  if (val === null || val === undefined || val === '') return '—'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return String(val)
  return `₹${(n / 100000).toFixed(1)}L`
}

function stageColor(stage: string): string {
  const map: Record<string, string> = {
    applied: '#94a3b8',
    pre_screening: '#ff6ea8',
    pre_screened: '#ff2d78',
    test_invited: '#f59e0b',
    screened: '#10b981',
    hr_approved: '#06b6d4',
    shortlisted: '#10b981',
    offer_sent: '#ff2d78',
    hired: '#06b6d4',
    rejected: '#ef4444',
  }
  return map[stage] ?? '#94a3b8'
}

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    applied: 'Applied',
    pre_screening: 'Pre-screening',
    pre_screened: 'Pre-screened',
    test_invited: 'Test Invited',
    screened: 'Screened',
    hr_approved: 'HR Approved',
    shortlisted: 'Shortlisted',
    offer_sent: 'Offer Sent',
    hired: 'Hired',
    rejected: 'Rejected',
  }
  return map[stage] ?? stage
}

function fmtDate(d: string | null): string {
  if (!d) return '—'
  return new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

const CARD_STYLE: React.CSSProperties = {
  background: '#111111',
  border: '1px solid #1f1f1f',
  borderRadius: 12,
  padding: '20px 22px',
  marginBottom: 16,
}

const SECTION_TITLE: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 700,
  color: '#666666',
  textTransform: 'uppercase',
  letterSpacing: '0.07em',
  marginBottom: 16,
  marginTop: 0,
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const id = params.id

  const [app, setApp] = useState<ApplicationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [working, setWorking] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [hrFeedback, setHrFeedback] = useState('')

  useEffect(() => {
    setLoading(true)
    getApplication(id)
      .then(setApp)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [id])

  async function handleAdvance() {
    if (!app || working) return
    setWorking(true)
    try {
      const res = await advanceApplication(app.id)
      setApp((prev) => (prev ? { ...prev, stage: res.new_stage } : prev))
      setToast({ message: `Advanced to ${stageLabel(res.new_stage)}`, type: 'success' })
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed to advance', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  async function handleReject() {
    if (!app || working) return
    setWorking(true)
    try {
      await rejectApplication(app.id, 'Rejected by HR')
      setApp((prev) => (prev ? { ...prev, stage: 'rejected', rejection_reason: 'Rejected by HR' } : prev))
      setToast({ message: 'Candidate rejected', type: 'success' })
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed to reject', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  async function handleHRDecision(decision: 'yes' | 'no') {
    if (!app || working) return
    const verb = decision === 'yes' ? 'approve and send to 2nd round' : 'reject'
    if (!window.confirm(`Are you sure you want to ${verb} ${app.name}?`)) return
    setWorking(true)
    try {
      const res = await hrDecision(app.id, { decision, feedback: hrFeedback })
      setApp((prev) => (prev ? { ...prev, stage: res.stage } : prev))
      if (decision === 'yes') {
        const link = res.calendly_link ? ` Calendly sent.` : ''
        setToast({ message: `HR approved. HOD notified at ${res.hod_notified}.${link}`, type: 'success' })
      } else {
        setToast({ message: 'Candidate rejected and notified.', type: 'success' })
      }
      setHrFeedback('')
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  async function handleScheduleInterview() {
    if (!app || working) return

    const startRaw = window.prompt(
      'Interview start (YYYY-MM-DDTHH:MM+05:30, e.g. 2026-05-15T10:00:00+05:30):'
    )
    if (startRaw === null) return

    const endRaw = window.prompt(
      'Interview end (YYYY-MM-DDTHH:MM+05:30, e.g. 2026-05-15T11:00:00+05:30):'
    )
    if (endRaw === null) return

    setWorking(true)
    try {
      const res = await scheduleInterview(app.id, { start_iso: startRaw, end_iso: endRaw })
      const meetMsg = res.meet_link ? ` Meet: ${res.meet_link}` : ''
      setToast({
        message: `Interview invite sent to ${res.candidate_email}.${meetMsg}`,
        type: 'success',
      })
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed to schedule interview', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  async function handleSendOffer() {
    if (!app || working) return
    if (!window.confirm(`Send offer letter to ${app.email}?`)) return
    setWorking(true)
    try {
      const res = await sendOfferEmail(app.id)
      setToast({ message: `Offer email sent to ${res.to}`, type: 'success' })
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed to send offer email', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  async function handleGenerateOffer() {
    if (!app || working) return

    const ctcRaw = window.prompt('CTC (LPA):')
    if (ctcRaw === null) return
    const ctc_lpa = parseFloat(ctcRaw)
    if (isNaN(ctc_lpa)) {
      setToast({ message: 'Invalid CTC value', type: 'error' })
      return
    }

    const joining_date = window.prompt('Joining date (YYYY-MM-DD):')
    if (joining_date === null) return

    const reporting_to = window.prompt('Reporting to:')
    if (reporting_to === null) return

    const location = window.prompt('Location:')
    if (location === null) return

    setWorking(true)
    try {
      await generateOffer(app.id, { ctc_lpa, joining_date, reporting_to, location })
      setApp((prev) => (prev ? { ...prev, stage: 'offer_sent' } : prev))
      setToast({ message: 'Offer letter generated!', type: 'success' })
    } catch (e) {
      setToast({ message: e instanceof Error ? e.message : 'Failed to generate offer', type: 'error' })
    } finally {
      setWorking(false)
    }
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>
        Loading…
      </div>
    )
  }

  if (error || !app) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>
        {error ?? 'Not found'}
      </div>
    )
  }

  const isTerminal = app.stage === 'rejected' || app.stage === 'hired'
  const color = stageColor(app.stage)

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#f1f5f9', fontFamily: 'system-ui, sans-serif' }}>
      {/* Top bar */}
      <div style={{ padding: '16px 28px', borderBottom: '1px solid #1f1f1f', background: '#0d0d0d', display: 'flex', alignItems: 'center', gap: 16 }}>
        <button
          onClick={() => router.push('/hire')}
          style={{ background: 'none', border: 'none', color: '#666666', cursor: 'pointer', fontSize: 14, padding: 0 }}
        >
          ← Pipeline
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{app.name}</h1>
            <span
              style={{
                background: color + '22',
                color,
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 700,
                padding: '2px 10px',
              }}
            >
              {stageLabel(app.stage)}
            </span>
          </div>
          <div style={{ color: '#666666', fontSize: 13, marginTop: 2 }}>
            {app.role} &middot; {app.email}
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '24px 28px', display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, maxWidth: 1100 }}>
        {/* Left column */}
        <div>
          {/* Candidate Info */}
          <div style={CARD_STYLE}>
            <p style={SECTION_TITLE}>Candidate Info</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
              <Field label="Phone" value={app.phone} />
              <Field label="Location" value={app.location} />
              <Field label="Years Experience" value={app.years_experience !== null ? `${app.years_experience} yrs` : null} />
              <Field label="Notice Period" value={app.notice_period_days !== null ? `${app.notice_period_days} days` : null} />
              <Field label="Current CTC" value={formatCTC(app.current_ctc)} />
              <Field label="Expected CTC" value={formatCTC(app.expected_ctc)} />
              <Field label="Source" value={app.source} />
              <Field
                label="LinkedIn"
                value={
                  app.linkedin_url ? (
                    <a href={app.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ color: '#ff6ea8', textDecoration: 'none' }}>
                      View Profile
                    </a>
                  ) : null
                }
              />
            </div>
            {app.application_answer ? (
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Application Answer</div>
                <div style={{ background: '#0a0a0a', border: '1px solid #1f1f1f', borderRadius: 8, padding: '12px 14px', fontSize: 13, color: '#94a3b8', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {app.application_answer}
                </div>
              </div>
            ) : null}
          </div>

          {/* Scores */}
          <div style={CARD_STYLE}>
            <p style={SECTION_TITLE}>Scores</p>
            <ScoreBar label="Resume Score" score={app.resume_score} />
            <ScoreBar label="Screen Score" score={app.screen_score} />
            {app.test_session ? (
              <>
                <ScoreBar label="Aptitude Score" score={app.test_session.aptitude_score} />
                <ScoreBar label="English Score" score={app.test_session.english_score} />
                <ScoreBar label="Overall Score" score={app.test_session.overall_score} />
              </>
            ) : null}
          </div>

          {/* Pre-screen Session */}
          {app.screen_session ? (
            <div style={CARD_STYLE}>
              <p style={SECTION_TITLE}>Pre-screen Session</p>
              {(() => {
                const state = (app.screen_session.state ?? {}) as { current_question_index?: number; completed?: boolean }
                const qIndex = typeof state.current_question_index === 'number' ? state.current_question_index + 1 : null
                const completed = Boolean(state.completed)
                return (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 20px' }}>
                    <Field label="Question" value={qIndex !== null ? `Q${qIndex}/5` : '—'} />
                    <Field label="Completed" value={completed ? 'Yes' : 'No'} />
                    <Field label="Started" value={fmtDate(app.screen_session.started_at)} />
                    <Field label="Completed At" value={fmtDate(app.screen_session.completed_at)} />
                  </div>
                )
              })()}
            </div>
          ) : null}
        </div>

        {/* Right column */}
        <div>
          {/* Actions */}
          <div style={CARD_STYLE}>
            <p style={SECTION_TITLE}>Actions</p>
            {app.stage === 'rejected' ? (
              <div style={{ color: '#ef4444', fontSize: 13 }}>
                Rejected{app.rejection_reason ? ` — ${app.rejection_reason}` : ''}
              </div>
            ) : (
              <>
                {!isTerminal && app.stage !== 'shortlisted' ? (
                  <button
                    onClick={handleAdvance}
                    disabled={working}
                    style={{
                      width: '100%',
                      background: working ? '#052e16' : '#10b981',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 8,
                      padding: '10px 0',
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: working ? 'not-allowed' : 'pointer',
                      marginBottom: 10,
                      opacity: working ? 0.7 : 1,
                    }}
                  >
                    {working ? 'Working…' : 'Advance Stage →'}
                  </button>
                ) : null}

                {app.stage === 'screened' ? (
                  <button
                    onClick={handleScheduleInterview}
                    disabled={working}
                    style={{
                      width: '100%',
                      background: working ? '#1f1f1f' : '#0f766e',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 8,
                      padding: '10px 0',
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: working ? 'not-allowed' : 'pointer',
                      marginBottom: 10,
                      opacity: working ? 0.7 : 1,
                    }}
                  >
                    {working ? 'Scheduling…' : 'Schedule Interview'}
                  </button>
                ) : null}

                {app.stage === 'shortlisted' ? (
                  <button
                    onClick={handleGenerateOffer}
                    disabled={working}
                    style={{
                      width: '100%',
                      background: working ? '#1f1f1f' : '#ff2d78',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 8,
                      padding: '10px 0',
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: working ? 'not-allowed' : 'pointer',
                      marginBottom: 10,
                      opacity: working ? 0.7 : 1,
                    }}
                  >
                    {working ? 'Generating…' : 'Generate Offer Letter'}
                  </button>
                ) : null}

                {(app.stage === 'offer_sent' || app.stage === 'hired') ? (
                  <>
                    <button
                      onClick={handleSendOffer}
                      disabled={working}
                      style={{
                        width: '100%',
                        background: working ? '#1f1f1f' : '#ff2d78',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 8,
                        padding: '10px 0',
                        fontSize: 14,
                        fontWeight: 600,
                        cursor: working ? 'not-allowed' : 'pointer',
                        marginBottom: 10,
                        opacity: working ? 0.7 : 1,
                      }}
                    >
                      {working ? 'Sending…' : 'Send Offer Email'}
                    </button>
                    <a
                      href={offerDownloadUrl(app.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'block',
                        width: '100%',
                        background: '#0a0a0a',
                        color: '#ff2d78',
                        border: '1px solid #ff2d78',
                        borderRadius: 8,
                        padding: '9px 0',
                        fontSize: 14,
                        fontWeight: 600,
                        textAlign: 'center',
                        textDecoration: 'none',
                        marginBottom: 10,
                        boxSizing: 'border-box',
                      }}
                    >
                      Download Offer Letter
                    </a>
                  </>
                ) : null}

                {app.stage !== 'offer_sent' && app.stage !== 'hired' ? (
                  <button
                    onClick={handleReject}
                    disabled={working}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      color: '#ef4444',
                      border: '1px solid #ef4444',
                      borderRadius: 8,
                      padding: '9px 0',
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: working ? 'not-allowed' : 'pointer',
                      opacity: working ? 0.6 : 1,
                    }}
                  >
                    Reject
                  </button>
                ) : null}
              </>
            )}
          </div>

          {/* HR Decision — only for screened candidates */}
          {app.stage === 'screened' ? (
            <div style={CARD_STYLE}>
              <p style={SECTION_TITLE}>HR Decision</p>
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
                  Feedback / Notes
                </label>
                <textarea
                  value={hrFeedback}
                  onChange={(e) => setHrFeedback(e.target.value)}
                  rows={3}
                  placeholder="Optional: write interview notes here"
                  style={{
                    width: '100%',
                    background: '#0a0a0a',
                    border: '1px solid #1f1f1f',
                    borderRadius: 8,
                    color: '#f1f5f9',
                    fontSize: 13,
                    padding: '8px 10px',
                    resize: 'vertical',
                    outline: 'none',
                    boxSizing: 'border-box',
                    fontFamily: 'inherit',
                  }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <button
                  onClick={() => handleHRDecision('yes')}
                  disabled={working}
                  style={{
                    background: working ? '#052e16' : '#10b981',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 8,
                    padding: '9px 0',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: working ? 'not-allowed' : 'pointer',
                    opacity: working ? 0.7 : 1,
                  }}
                >
                  ✓ Pass — 2nd Round
                </button>
                <button
                  onClick={() => handleHRDecision('no')}
                  disabled={working}
                  style={{
                    background: 'transparent',
                    color: '#ef4444',
                    border: '1px solid #ef4444',
                    borderRadius: 8,
                    padding: '9px 0',
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: working ? 'not-allowed' : 'pointer',
                    opacity: working ? 0.6 : 1,
                  }}
                >
                  ✗ Reject
                </button>
              </div>
            </div>
          ) : null}

          {/* Timeline */}
          <div style={CARD_STYLE}>
            <p style={SECTION_TITLE}>Timeline</p>
            <Field label="Applied" value={fmtDate(app.created_at)} />
            <Field label="Last Update" value={fmtDate(app.updated_at)} />
          </div>
        </div>
      </div>

      {toast ? (
        <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />
      ) : null}
    </div>
  )
}
