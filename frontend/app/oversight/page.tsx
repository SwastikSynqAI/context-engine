'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  listEvalRuns,
  triggerEvalRun,
  listPolicies,
  runQualityCheck,
  listEvalCases,
  createEvalCase,
  type EvalRun,
  type Policy,
  type QualityReport,
  type EvalCase,
} from '@/lib/api'

const MOCK_EVAL_RUNS: EvalRun[] = [
  { id: 'r3', triggered_by: 'admin', started_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.83, cases_passed: 7, cases_run: 8 },
  { id: 'r2', triggered_by: 'admin', started_at: new Date(Date.now() - 9 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.74, cases_passed: 6, cases_run: 8 },
  { id: 'r1', triggered_by: 'member', started_at: new Date(Date.now() - 16 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.64, cases_passed: 5, cases_run: 8 },
]

const MOCK_POLICIES: Policy[] = [
  { id: 'p1', name: 'Minimum Deal Value Guard', severity: 'block', fire_count: 3, description: 'Blocks any response referencing deal values below configured floor' },
  { id: 'p2', name: 'PII Data Protection', severity: 'flag', fire_count: 7, description: 'Flags queries that may expose candidate personal data' },
  { id: 'p3', name: 'Competitor Intelligence Gate', severity: 'warn', fire_count: 2, description: 'Warns when competitor data (WeWork, Smartworks) is queried' },
  { id: 'p4', name: 'Discount Approval Gate', severity: 'flag', fire_count: 5, description: 'Flags discount queries for finance approval before proceeding' },
]

const MOCK_EVAL_CASES: EvalCase[] = [
  { id: 'c1', question: 'What is the standard pricing for our enterprise tier?', expected_themes: ['pricing', 'enterprise', 'comparable deals'], min_expected_score: 0.7, created_by: 'admin' },
  { id: 'c2', question: 'Which SaaS clients are currently in our portfolio?', expected_themes: ['saas', 'clients', 'portfolio'], min_expected_score: 0.75, created_by: 'admin' },
  { id: 'c3', question: 'Summarise the Acme Corp deal', expected_themes: ['Acme', 'contract value', 'terms'], min_expected_score: 0.8, created_by: 'member' },
  { id: 'c4', question: 'What products do we currently offer?', expected_themes: ['products', 'features', 'tiers'], min_expected_score: 0.75, created_by: 'admin' },
  { id: 'c5', question: 'Who are our active channel partners?', expected_themes: ['partner', 'channel', 'commission'], min_expected_score: 0.7, created_by: 'member' },
  { id: 'c6', question: 'What is our ideal customer profile?', expected_themes: ['ICP', 'company size', 'industry', 'funding stage'], min_expected_score: 0.8, created_by: 'admin' },
  { id: 'c7', question: 'What is our SLA for enterprise support?', expected_themes: ['support', 'SLA', 'enterprise', 'response time'], min_expected_score: 0.7, created_by: 'member' },
  { id: 'c8', question: 'Show me all deals closed in the last quarter', expected_themes: ['closed deals', 'revenue', 'client'], min_expected_score: 0.75, created_by: 'admin' },
]

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, { bg: string; color: string }> = {
    block: { bg: '#fee2e2', color: '#dc2626' },
    warn: { bg: '#fff7ed', color: '#9a3412' },
    flag: { bg: '#f0f0ee', color: '#6b7280' },
  }
  const s = styles[severity] ?? styles.flag
  return (
    <span
      style={{
        fontSize: 11,
        padding: '2px 8px',
        borderRadius: 4,
        background: s.bg,
        color: s.color,
        fontWeight: 600,
      }}
    >
      {severity}
    </span>
  )
}

function ScoreDelta({ delta }: { delta: number | null }) {
  if (delta === null) return <span style={{ color: '#9ca3af', fontSize: 13 }}>—</span>
  const positive = delta >= 0
  return (
    <span style={{ color: positive ? '#10b981' : '#ef4444', fontWeight: 600, fontSize: 13 }}>
      {positive ? '+' : ''}{delta.toFixed(1)}%
    </span>
  )
}

const cardStyle: React.CSSProperties = {
  background: '#fafaf8',
  border: '1px solid #e8e8e6',
  borderRadius: 12,
  padding: '20px 24px',
  marginBottom: 24,
}

const skeletonStyle: React.CSSProperties = {
  background: 'linear-gradient(90deg, #f0f0ee 25%, #e8e8e6 50%, #f0f0ee 75%)',
  backgroundSize: '200% 100%',
  animation: 'pulse 1.5s ease-in-out infinite',
  borderRadius: 8,
}

// ── Section 1: Eval Health ────────────────────────────────────────────────────

function EvalHealthSection() {
  const [runs, setRuns] = useState<EvalRun[]>(MOCK_EVAL_RUNS)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runSuccess, setRunSuccess] = useState(false)

  const load = useCallback(async () => {
    try {
      const r = await listEvalRuns(3)
      if (r.length > 0) setRuns(r)
    } catch {
      // keep mock data
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleRunEvals = async () => {
    setRunning(true)
    setRunSuccess(false)
    try {
      await triggerEvalRun('admin')
      setRunSuccess(true)
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Eval run failed')
    } finally {
      setRunning(false)
    }
  }

  const getDelta = (runs: EvalRun[], index: number): number | null => {
    if (index >= runs.length - 1) return null
    return (runs[index].avg_score - runs[index + 1].avg_score) * 100
  }

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>Eval Health</h2>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>Last 3 evaluation runs</p>
        </div>
        <button
          onClick={handleRunEvals}
          disabled={running}
          style={{
            background: running ? '#f0f0ee' : '#0a0a0a',
            color: running ? '#9ca3af' : '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '8px 16px',
            fontSize: 12,
            fontWeight: 500,
            cursor: running ? 'not-allowed' : 'pointer',
          }}
        >
          {running ? 'Running…' : '▶ Run Evals Now'}
        </button>
      </div>

      {runSuccess && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '8px 12px', color: '#15803d', fontSize: 12, marginBottom: 12 }}>
          ✓ Eval run triggered
        </div>
      )}

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '8px 12px', color: '#dc2626', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} style={{ ...skeletonStyle, height: 40 }} />
          ))}
        </div>
      ) : runs.length === 0 ? (
        <div style={{ color: '#9ca3af', fontSize: 13, padding: '16px 0' }}>No eval runs yet. Run evals to see results.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e8e8e6' }}>
              {['Date', 'Avg Score', 'Cases Passed', 'Delta'].map((h) => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#6b7280', fontWeight: 500, fontSize: 11, letterSpacing: '0.05em' }}>
                  {h.toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((run, i) => (
              <tr key={run.id} style={{ borderBottom: i < runs.length - 1 ? '1px solid #e8e8e6' : 'none' }}>
                <td style={{ padding: '10px 12px', color: '#6b7280' }}>
                  {new Date(run.started_at).toLocaleDateString()} {new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ background: '#e8e8e6', borderRadius: 3, height: 5, width: 80, overflow: 'hidden' }}>
                      <div
                        style={{
                          height: '100%',
                          width: `${Math.round(run.avg_score * 100)}%`,
                          background: '#ffde59',
                          borderRadius: 3,
                        }}
                      />
                    </div>
                    <span style={{ color: '#0a0a0a', fontWeight: 600 }}>{Math.round(run.avg_score * 100)}%</span>
                  </div>
                </td>
                <td style={{ padding: '10px 12px', color: '#0a0a0a' }}>
                  {run.cases_passed}/{run.cases_run}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <ScoreDelta delta={getDelta(runs, i)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Section 2: Active Policies ────────────────────────────────────────────────

function PoliciesSection() {
  const [policies, setPolicies] = useState<Policy[]>(MOCK_POLICIES)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listPolicies()
      .then((r) => { if (r.length > 0) setPolicies(r) })
      .catch(() => { /* keep mock */ })
  }, [])

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>Active Policies</h2>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>Guardrails applied to all responses</p>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '8px 12px', color: '#dc2626', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} style={{ ...skeletonStyle, height: 40 }} />
          ))}
        </div>
      ) : policies.length === 0 ? (
        <div style={{ color: '#9ca3af', fontSize: 13, padding: '16px 0' }}>No active policies configured.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e8e8e6' }}>
              {['Name', 'Severity', 'Description', 'Fires'].map((h) => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#6b7280', fontWeight: 500, fontSize: 11, letterSpacing: '0.05em' }}>
                  {h.toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {policies.map((policy, i) => (
              <tr key={policy.id} style={{ borderBottom: i < policies.length - 1 ? '1px solid #e8e8e6' : 'none' }}>
                <td style={{ padding: '10px 12px', color: '#0a0a0a', fontWeight: 500 }}>{policy.name}</td>
                <td style={{ padding: '10px 12px' }}>
                  <SeverityBadge severity={policy.severity} />
                </td>
                <td style={{ padding: '10px 12px', color: '#6b7280' }}>{policy.description}</td>
                <td style={{ padding: '10px 12px', color: '#0a0a0a', fontWeight: 600 }}>{policy.fire_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── Section 3: Quality Report ─────────────────────────────────────────────────

function QualitySection() {
  const [report, setReport] = useState<QualityReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await runQualityCheck()
      setReport(r)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Quality check failed')
    } finally {
      setLoading(false)
    }
  }

  const severityColor = (s: string) => {
    if (s === 'critical' || s === 'high') return '#dc2626'
    if (s === 'medium' || s === 'warn') return '#f59e0b'
    return '#9ca3af'
  }

  const severityBg = (s: string) => {
    if (s === 'critical' || s === 'high') return '#fee2e2'
    if (s === 'medium' || s === 'warn') return '#fff7ed'
    return '#f0f0ee'
  }

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>Quality Report</h2>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>Detect stale data, coverage gaps, consistency issues</p>
        </div>
        <button
          onClick={handleRun}
          disabled={loading}
          style={{
            background: loading ? '#f0f0ee' : '#fafaf8',
            color: loading ? '#9ca3af' : '#0a0a0a',
            border: `1px solid ${loading ? '#e8e8e6' : '#d1d1ce'}`,
            borderRadius: 8,
            padding: '8px 16px',
            fontSize: 12,
            fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Running…' : '⟳ Run Quality Check'}
        </button>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '8px 12px', color: '#dc2626', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!report && !loading && (
        <div style={{ color: '#9ca3af', fontSize: 13, padding: '16px 0' }}>
          Click "Run Quality Check" to analyse the intelligence layer.
        </div>
      )}

      {report && (
        <div>
          {/* Score */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <div
              style={{
                fontSize: 36,
                fontWeight: 700,
                color: report.score >= 80 ? '#10b981' : report.score >= 50 ? '#f59e0b' : '#ef4444',
              }}
            >
              {Math.round(report.score)}%
            </div>
            <div>
              <div style={{ fontSize: 13, color: '#0a0a0a', fontWeight: 500 }}>Overall Quality Score</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{report.issues.length} issues found</div>
            </div>
          </div>

          {/* Score bar */}
          <div style={{ background: '#e8e8e6', borderRadius: 4, height: 8, overflow: 'hidden', marginBottom: 16 }}>
            <div
              style={{
                height: '100%',
                width: `${Math.round(report.score)}%`,
                background: '#ffde59',
                borderRadius: 4,
                transition: 'width 0.6s ease',
              }}
            />
          </div>

          {/* Issues */}
          {report.issues.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {report.issues.map((issue, i) => (
                <div
                  key={i}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #e8e8e6',
                    borderRadius: 8,
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: severityColor(issue.severity),
                      marginTop: 4,
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 3,
                          background: severityBg(issue.severity),
                          color: severityColor(issue.severity),
                          fontWeight: 600,
                        }}
                      >
                        {issue.severity.toUpperCase()}
                      </span>
                      {issue.entity_name && (
                        <span style={{ fontSize: 11, color: '#9ca3af' }}>{issue.entity_name}</span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: '#404852' }}>{issue.message}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {report.issues.length === 0 && (
            <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '10px 14px', color: '#15803d', fontSize: 13 }}>
              ✓ No issues found — intelligence layer looks healthy
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Section 4: Eval Cases ─────────────────────────────────────────────────────

function EvalCasesSection() {
  const [cases, setCases] = useState<EvalCase[]>(MOCK_EVAL_CASES)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    question: '',
    expected_themes: '',
    min_expected_score: '0.7',
    created_by: 'admin',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  const load = useCallback(async () => {
    try {
      const c = await listEvalCases()
      if (c.length > 0) setCases(c)
    } catch {
      // keep mock data
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const setField = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitSuccess(false)

    try {
      await createEvalCase({
        question: form.question,
        expected_themes: form.expected_themes.split(',').map((s) => s.trim()).filter(Boolean),
        min_expected_score: parseFloat(form.min_expected_score),
        created_by: form.created_by,
      })
      setSubmitSuccess(true)
      setForm({ question: '', expected_themes: '', min_expected_score: '0.7', created_by: 'admin' })
      setShowForm(false)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create eval case')
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: '#ffffff',
    border: '1px solid #e8e8e6',
    borderRadius: 8,
    color: '#0a0a0a',
    fontSize: 13,
    padding: '8px 12px',
    outline: 'none',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
  }

  return (
    <div style={{ ...cardStyle, marginBottom: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>Eval Cases</h2>
          <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>Test questions that benchmark the intelligence layer</p>
        </div>
        <button
          onClick={() => { setShowForm(!showForm); setSubmitSuccess(false) }}
          style={{
            background: showForm ? '#f0f0ee' : '#ffde59',
            color: '#0a0a0a',
            border: 'none',
            borderRadius: 8,
            padding: '8px 16px',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          {showForm ? '✕ Cancel' : '+ Add Case'}
        </button>
      </div>

      {submitSuccess && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '8px 12px', color: '#15803d', fontSize: 12, marginBottom: 12 }}>
          ✓ Eval case added
        </div>
      )}

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '8px 12px', color: '#dc2626', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: '#ffffff', border: '1px solid #e8e8e6', borderRadius: 10, padding: '16px 20px', marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 5 }}>QUESTION</label>
            <input
              value={form.question}
              onChange={(e) => setField('question', e.target.value)}
              required
              placeholder="What should the system know about enterprise leads?"
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 5 }}>
              EXPECTED THEMES <span style={{ color: '#9ca3af' }}>(comma-separated)</span>
            </label>
            <input
              value={form.expected_themes}
              onChange={(e) => setField('expected_themes', e.target.value)}
              placeholder="enterprise, saas, b2b, north-america"
              style={inputStyle}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 5 }}>MIN EXPECTED SCORE (0–1)</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={form.min_expected_score}
                onChange={(e) => setField('min_expected_score', e.target.value)}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ fontSize: 11, color: '#6b7280', display: 'block', marginBottom: 5 }}>CREATED BY</label>
              <select value={form.created_by} onChange={(e) => setField('created_by', e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                {['admin', 'member', 'team'].map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            style={{
              alignSelf: 'flex-start',
              background: submitting ? '#f0f0ee' : '#0a0a0a',
              color: submitting ? '#9ca3af' : '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '8px 18px',
              fontSize: 12,
              fontWeight: 600,
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? 'Adding…' : 'Add Case →'}
          </button>
        </form>
      )}

      {/* Cases list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[...Array(3)].map((_, i) => (
            <div key={i} style={{ ...skeletonStyle, height: 52 }} />
          ))}
        </div>
      ) : cases.length === 0 ? (
        <div style={{ color: '#9ca3af', fontSize: 13, padding: '16px 0' }}>No eval cases yet. Add one above to start benchmarking.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {cases.map((c) => (
            <div
              key={c.id}
              style={{
                background: '#ffffff',
                border: '1px solid #e8e8e6',
                borderRadius: 8,
                padding: '12px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: '#0a0a0a', marginBottom: 6 }}>{c.question}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {c.expected_themes.map((theme) => (
                      <span
                        key={theme}
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 3,
                          background: '#fefce8',
                          color: '#854d0e',
                        }}
                      >
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ flexShrink: 0, textAlign: 'right' }}>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>Min score</div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#10b981' }}>
                    {Math.round(c.min_expected_score * 100)}%
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>by {c.created_by}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function OversightPage() {
  return (
    <div style={{ padding: '32px 40px', maxWidth: 1000 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#0a0a0a', margin: 0 }}>
          Oversight & Quality
        </h1>
        <p style={{ fontSize: 14, color: '#6b7280', margin: '4px 0 0' }}>
          Eval runs · policy enforcement · quality analysis · benchmark cases
        </p>
      </div>

      <EvalHealthSection />
      <PoliciesSection />
      <QualitySection />
      <EvalCasesSection />
    </div>
  )
}
