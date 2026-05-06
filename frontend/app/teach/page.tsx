'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  createDecision,
  createRule,
  listRules,
  submitFeedback,
  type Rule,
} from '@/lib/api'

const DECISION_TYPES = [
  'lead_approval',
  'lead_rejection',
  'deal_closure',
  'vendor_approval',
  'pricing_override',
  'data_correction',
  'contact_linking',
]

const ACTORS = ['admin', 'member', 'team']

const FEEDBACK_TYPES = [
  { value: 'correction', label: 'Correction' },
  { value: 'missing_context', label: 'Missing context' },
  { value: 'wrong_rule_applied', label: 'Wrong rule applied' },
  { value: 'hallucination', label: 'Hallucination' },
]

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? '#ffde59' : 'transparent',
        color: active ? '#0a0a0a' : '#6b7280',
        border: active ? '1px solid #ffde59' : '1px solid #e8e8e6',
        borderRadius: 8,
        padding: '8px 16px',
        fontSize: 13,
        fontWeight: active ? 600 : 400,
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  )
}

function FormField({
  label,
  children,
  hint,
}: {
  label: string
  children: React.ReactNode
  hint?: string
}) {
  return (
    <div>
      <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 6, fontWeight: 500 }}>
        {label.toUpperCase()}
      </label>
      {children}
      {hint && <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>{hint}</div>}
    </div>
  )
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
  transition: 'border-color 0.15s',
}

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: 'pointer',
}

const textareaStyle: React.CSSProperties = {
  ...inputStyle,
  resize: 'vertical',
  lineHeight: 1.5,
}

const submitBtn = (disabled: boolean): React.CSSProperties => ({
  alignSelf: 'flex-start',
  background: disabled ? '#f0f0ee' : '#0a0a0a',
  color: disabled ? '#9ca3af' : '#fff',
  border: 'none',
  borderRadius: 8,
  padding: '10px 24px',
  fontSize: 13,
  fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
})

// ── Tab 1: Capture Decision ───────────────────────────────────────────────────

function CaptureDecisionTab() {
  const [form, setForm] = useState({
    decision_type: 'lead_approval',
    actor: 'admin',
    primary_entity_id: '',
    human_action: '',
    human_reasoning: '',
    context_snapshot: '{}',
  })
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSuccess(false)

    let contextSnapshot: Record<string, unknown> = {}
    try {
      contextSnapshot = JSON.parse(form.context_snapshot)
    } catch {
      setError('Context snapshot must be valid JSON')
      setSubmitting(false)
      return
    }

    try {
      await createDecision({
        decision_type: form.decision_type,
        actor: form.actor,
        human_action: form.human_action,
        human_reasoning: form.human_reasoning || undefined,
        primary_entity_id: form.primary_entity_id || undefined,
        context_snapshot: contextSnapshot,
      })
      setSuccess(true)
      setForm({
        decision_type: 'lead_approval',
        actor: 'admin',
        primary_entity_id: '',
        human_action: '',
        human_reasoning: '',
        context_snapshot: '{}',
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 680 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <FormField label="Decision type">
          <select value={form.decision_type} onChange={(e) => set('decision_type', e.target.value)} style={selectStyle}>
            {DECISION_TYPES.map((dt) => (
              <option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Actor">
          <select value={form.actor} onChange={(e) => set('actor', e.target.value)} style={selectStyle}>
            {ACTORS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </FormField>
      </div>

      <FormField label="Primary entity ID" hint="Leave blank if not entity-specific">
        <input
          value={form.primary_entity_id}
          onChange={(e) => set('primary_entity_id', e.target.value)}
          placeholder="e.g. ent_abc123"
          style={inputStyle}
        />
      </FormField>

      <FormField label="Human action" hint="Brief one-line summary of what was decided">
        <input
          value={form.human_action}
          onChange={(e) => set('human_action', e.target.value)}
          placeholder="e.g. Approved lead — Series B SaaS, expanding headcount"
          required
          style={inputStyle}
        />
      </FormField>

      <FormField label="Reasoning" hint="Why did you make this decision? Be detailed — this becomes training signal.">
        <textarea
          value={form.human_reasoning}
          onChange={(e) => set('human_reasoning', e.target.value)}
          rows={4}
          placeholder="This company just raised Series B and is rapidly expanding. Strong ICP signal for our enterprise tier..."
          style={textareaStyle}
        />
      </FormField>

      <FormField label="Context snapshot (JSON)" hint="Optional. Paste relevant data that informed this decision.">
        <textarea
          value={form.context_snapshot}
          onChange={(e) => set('context_snapshot', e.target.value)}
          rows={3}
          placeholder="{}"
          style={{ ...textareaStyle, fontFamily: 'monospace', fontSize: 12 }}
        />
      </FormField>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '10px 14px', color: '#dc2626', fontSize: 13 }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '10px 14px', color: '#15803d', fontSize: 13 }}>
          ✓ Decision recorded successfully
        </div>
      )}

      <button type="submit" disabled={submitting} style={submitBtn(submitting)}>
        {submitting ? 'Recording…' : 'Record Decision →'}
      </button>
    </form>
  )
}

// ── Tab 2: Encode Rule ────────────────────────────────────────────────────────

const MOCK_RULES: Rule[] = [
  { id: 'r1', name: 'Enterprise ICP Priority', condition: { company_size: '200+', funding_stage: 'Series B+' }, action: { priority: 'high', icp_signal: 'true' }, created_by: 'admin', fire_count: 14, active: true },
  { id: 'r2', name: 'CRM Source Preference', condition: { entity_type: 'client', field: 'employee_count' }, action: { prefer_source: 'crm' }, created_by: 'member', fire_count: 8, active: true },
  { id: 'r3', name: 'Strategic Accounts Premium', condition: { tier: 'strategic', deal_value_gte: '100000' }, action: { apply_pricing_tier: 'strategic_premium' }, created_by: 'admin', fire_count: 6, active: true },
  { id: 'r4', name: 'Partner Commission Cap', condition: { entity_type: 'partner' }, action: { flag_for: 'finance', note: 'review commission terms' }, created_by: 'admin', fire_count: 3, active: true },
  { id: 'r5', name: 'High-confidence Lead Auto-flag', condition: { confidence_gte: '0.8' }, action: { flag_for: 'admin', priority: 'high' }, created_by: 'member', fire_count: 5, active: true },
  { id: 'r6', name: 'Out-of-scope Query Policy', condition: { question_contains: 'competitor pricing' }, action: { note: 'policy — do not share, redirect to sales' }, created_by: 'admin', fire_count: 2, active: true },
]

function EncodeRuleTab() {
  const [form, setForm] = useState({
    name: '',
    reasoning: '',
    condition: '{"industry": "bfsi"}',
    action: '{"priority": "high"}',
    created_by: 'admin',
  })
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rules, setRules] = useState<Rule[]>(MOCK_RULES)
  const [rulesLoading, setRulesLoading] = useState(false)

  const set = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const loadRules = useCallback(async () => {
    try {
      const r = await listRules(true)
      if (r.length > 0) setRules(r)
    } catch {
      // keep mock data on error
    }
  }, [])

  useEffect(() => {
    loadRules()
  }, [loadRules])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSuccess(false)

    let condition: Record<string, unknown> = {}
    let action: Record<string, unknown> = {}
    try {
      condition = JSON.parse(form.condition)
      action = JSON.parse(form.action)
    } catch {
      setError('Condition and action must be valid JSON')
      setSubmitting(false)
      return
    }

    try {
      await createRule({
        name: form.name,
        reasoning: form.reasoning || undefined,
        condition,
        action,
        created_by: form.created_by,
      })
      setSuccess(true)
      setForm({ name: '', reasoning: '', condition: '{}', action: '{}', created_by: 'admin' })
      loadRules()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rule creation failed')
    } finally {
      setSubmitting(false)
    }
  }

  const conditionSummary = (cond: Record<string, unknown>) =>
    Object.entries(cond)
      .slice(0, 2)
      .map(([k, v]) => `${k}=${v}`)
      .join(', ') + (Object.keys(cond).length > 2 ? '…' : '')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 680 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <FormField label="Rule name">
            <input
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="e.g. Series B funded → high priority"
              required
              style={inputStyle}
            />
          </FormField>
          <FormField label="Created by">
            <select value={form.created_by} onChange={(e) => set('created_by', e.target.value)} style={selectStyle}>
              {ACTORS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </FormField>
        </div>

        <FormField label="Reasoning" hint="Why does this rule exist? This is the expert knowledge being encoded.">
          <textarea
            value={form.reasoning}
            onChange={(e) => set('reasoning', e.target.value)}
            rows={3}
            placeholder="Enterprise companies that recently raised funding are expanding and are prime candidates for our platform..."
            style={textareaStyle}
          />
        </FormField>

        <FormField label="Condition (JSON)" hint="Attributes that must match for this rule to fire">
          <textarea
            value={form.condition}
            onChange={(e) => set('condition', e.target.value)}
            rows={3}
            placeholder='{"industry": "bfsi", "funded_recently": "true"}'
            style={{ ...textareaStyle, fontFamily: 'monospace', fontSize: 12 }}
          />
        </FormField>

        <FormField label="Action (JSON)" hint="What should happen when this rule fires">
          <textarea
            value={form.action}
            onChange={(e) => set('action', e.target.value)}
            rows={3}
            placeholder='{"priority": "high", "flag_for": "admin"}'
            style={{ ...textareaStyle, fontFamily: 'monospace', fontSize: 12 }}
          />
        </FormField>

        {error && (
          <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '10px 14px', color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '10px 14px', color: '#15803d', fontSize: 13 }}>
            ✓ Rule created successfully
          </div>
        )}

        <button type="submit" disabled={submitting} style={submitBtn(submitting)}>
          {submitting ? 'Creating…' : 'Create Rule →'}
        </button>
      </form>

      {/* Active rules table */}
      <div>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#6b7280', margin: '0 0 12px', letterSpacing: '0.05em' }}>
          ACTIVE RULES
        </h3>
        {rulesLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                style={{
                  height: 44,
                  background: 'linear-gradient(90deg, #f0f0ee 25%, #e8e8e6 50%, #f0f0ee 75%)',
                  backgroundSize: '200% 100%',
                  animation: 'pulse 1.5s ease-in-out infinite',
                  borderRadius: 8,
                }}
              />
            ))}
          </div>
        ) : rules.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: 13, padding: '16px 0' }}>No active rules yet</div>
        ) : (
          <div style={{ background: '#fafaf8', border: '1px solid #e8e8e6', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f0f0ee', borderBottom: '1px solid #e8e8e6' }}>
                  {['Name', 'Condition', 'Action', 'Fires', 'By'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '10px 14px',
                        textAlign: 'left',
                        color: '#6b7280',
                        fontWeight: 500,
                        fontSize: 11,
                        letterSpacing: '0.05em',
                      }}
                    >
                      {h.toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rules.map((rule, i) => (
                  <tr
                    key={rule.id}
                    style={{ borderBottom: i < rules.length - 1 ? '1px solid #e8e8e6' : 'none' }}
                  >
                    <td style={{ padding: '10px 14px', color: '#0a0a0a', fontWeight: 500 }}>{rule.name}</td>
                    <td style={{ padding: '10px 14px', color: '#6b7280', fontFamily: 'monospace', fontSize: 11 }}>
                      {conditionSummary(rule.condition)}
                    </td>
                    <td style={{ padding: '10px 14px', color: '#6b7280', fontFamily: 'monospace', fontSize: 11 }}>
                      {conditionSummary(rule.action)}
                    </td>
                    <td style={{ padding: '10px 14px', color: '#0a0a0a', fontWeight: 600 }}>{rule.fire_count}</td>
                    <td style={{ padding: '10px 14px', color: '#9ca3af' }}>{rule.created_by}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tab 3: Submit Correction ──────────────────────────────────────────────────

function SubmitCorrectionTab() {
  const [form, setForm] = useState({
    question: '',
    claude_answer: '',
    correct_answer: '',
    corrected_by: 'admin',
    feedback_type: 'correction',
  })
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSuccess(false)

    try {
      await submitFeedback(
        form.question,
        form.claude_answer,
        form.correct_answer,
        form.corrected_by,
        form.feedback_type
      )
      setSuccess(true)
      setForm({
        question: '',
        claude_answer: '',
        correct_answer: '',
        corrected_by: 'admin',
        feedback_type: 'correction',
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 680 }}>
      <div
        style={{
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 8,
          padding: '12px 16px',
          fontSize: 13,
          color: '#1d4ed8',
        }}
      >
        Use this form to correct any answer the system gave — even outside the Ask page. This feeds directly into RLHF training.
      </div>

      <FormField label="Original question">
        <input
          value={form.question}
          onChange={(e) => set('question', e.target.value)}
          required
          placeholder="What was the question?"
          style={inputStyle}
        />
      </FormField>

      <FormField label="What the system answered" hint="Paste the system's incorrect answer">
        <textarea
          value={form.claude_answer}
          onChange={(e) => set('claude_answer', e.target.value)}
          rows={3}
          placeholder="The system said…"
          style={textareaStyle}
        />
      </FormField>

      <FormField label="Correct answer" hint="What should the answer have been?">
        <textarea
          value={form.correct_answer}
          onChange={(e) => set('correct_answer', e.target.value)}
          rows={3}
          required
          placeholder="The correct answer is…"
          style={textareaStyle}
        />
      </FormField>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <FormField label="Corrected by">
          <select value={form.corrected_by} onChange={(e) => set('corrected_by', e.target.value)} style={selectStyle}>
            {ACTORS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Feedback type">
          <select value={form.feedback_type} onChange={(e) => set('feedback_type', e.target.value)} style={selectStyle}>
            {FEEDBACK_TYPES.map((ft) => (
              <option key={ft.value} value={ft.value}>{ft.label}</option>
            ))}
          </select>
        </FormField>
      </div>

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #fca5a5', borderRadius: 8, padding: '10px 14px', color: '#dc2626', fontSize: 13 }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{ background: '#dcfce7', border: '1px solid #86efac', borderRadius: 8, padding: '10px 14px', color: '#15803d', fontSize: 13 }}>
          ✓ Correction submitted — thank you!
        </div>
      )}

      <button type="submit" disabled={submitting} style={submitBtn(submitting)}>
        {submitting ? 'Submitting…' : 'Submit Correction →'}
      </button>
    </form>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = 'decision' | 'rule' | 'correction'

const TABS: { id: Tab; label: string }[] = [
  { id: 'decision', label: '📋 Capture Decision' },
  { id: 'rule', label: '⚡ Encode Rule' },
  { id: 'correction', label: '✏ Submit Correction' },
]

export default function TeachPage() {
  const [activeTab, setActiveTab] = useState<Tab>('decision')

  return (
    <div style={{ padding: '32px 40px', maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#0a0a0a', margin: 0 }}>
          Teach the System
        </h1>
        <p style={{ fontSize: 14, color: '#6b7280', margin: '4px 0 0' }}>
          Human-in-the-loop reasoning capture · expert knowledge encoding · RLHF corrections
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 28, borderBottom: '1px solid #e8e8e6', paddingBottom: 16 }}>
        {TABS.map((tab) => (
          <TabButton
            key={tab.id}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </TabButton>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'decision' && <CaptureDecisionTab />}
        {activeTab === 'rule' && <EncodeRuleTab />}
        {activeTab === 'correction' && <SubmitCorrectionTab />}
      </div>
    </div>
  )
}
