'use client'

import { useState, useEffect, useRef } from 'react'
import {
  queryContext,
  submitFeedback,
  type QueryResult,
  type Citation,
} from '@/lib/api'

const INTENT_COLORS: Record<string, { bg: string; text: string }> = {
  pricing_query: { bg: '#fefce8', text: '#854d0e' },
  lead_evaluation: { bg: '#dcfce7', text: '#15803d' },
  vendor_assessment: { bg: '#fff7ed', text: '#9a3412' },
  policy_check: { bg: '#fee2e2', text: '#dc2626' },
  data_lookup: { bg: '#eff6ff', text: '#1d4ed8' },
  general: { bg: '#f0f0ee', text: '#6b7280' },
}

const FEEDBACK_TYPES = [
  { value: 'correction', label: 'Correction' },
  { value: 'missing_context', label: 'Missing context' },
  { value: 'wrong_rule_applied', label: 'Wrong rule applied' },
  { value: 'hallucination', label: 'Hallucination' },
]

interface StoredQuery {
  question: string
  intent: string
  confidence: number
  timestamp: string
}

const SUGGESTED_QUERIES = [
  { question: 'What is the going rate for 150 seats in Cyber City, Gurgaon?', intent: 'pricing_query' },
  { question: 'Which fintech companies are we tracking in NCR?', intent: 'lead_evaluation' },
  { question: 'Summarise all active deals above 100 seats', intent: 'data_lookup' },
  { question: 'What buildings do we have available above 500 seats?', intent: 'data_lookup' },
  { question: 'What is our ideal customer profile based on recent decisions?', intent: 'lead_evaluation' },
]

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>Confidence</span>
        <span style={{ fontSize: 13, fontWeight: 600, color }}>{pct}%</span>
      </div>
      <div style={{ background: '#e8e8e6', borderRadius: 4, height: 6, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 4,
            transition: 'width 0.6s ease',
          }}
        />
      </div>
    </div>
  )
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div
      style={{
        background: '#ffffff',
        border: '1px solid #e8e8e6',
        borderRadius: 6,
        padding: '8px 12px',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <div
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: '#ffde59',
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: '#0a0a0a', fontWeight: 500 }}>{citation.entity_name}</div>
        <div style={{ fontSize: 11, color: '#9ca3af' }}>
          {citation.entity_type} · {citation.source}
        </div>
      </div>
    </div>
  )
}

export default function QueryPage() {
  const [question, setQuestion] = useState('')
  const [entityId, setEntityId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [feedbackMode, setFeedbackMode] = useState<'none' | 'positive' | 'correct'>('none')
  const [correctAnswer, setCorrectAnswer] = useState('')
  const [correctedBy, setCorrectedBy] = useState('admin')
  const [feedbackType, setFeedbackType] = useState('correction')
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackDone, setFeedbackDone] = useState(false)

  const [history, setHistory] = useState<StoredQuery[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    try {
      const stored = localStorage.getItem('synq_query_history')
      if (stored) setHistory(JSON.parse(stored))
    } catch {
      // ignore
    }
  }, [])

  const saveToHistory = (q: string, r: QueryResult) => {
    const entry: StoredQuery = {
      question: q,
      intent: r.intent,
      confidence: r.confidence,
      timestamp: new Date().toISOString(),
    }
    const updated = [entry, ...history].slice(0, 5)
    setHistory(updated)
    try {
      localStorage.setItem('synq_query_history', JSON.stringify(updated))
    } catch {
      // ignore
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim()) return

    setLoading(true)
    setResult(null)
    setError(null)
    setFeedbackMode('none')
    setFeedbackDone(false)

    try {
      const r = await queryContext(question.trim(), entityId.trim() || undefined)
      setResult(r)
      saveToHistory(question.trim(), r)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!result || !correctAnswer.trim()) return

    setFeedbackSubmitting(true)
    try {
      await submitFeedback(question, result.answer, correctAnswer, correctedBy, feedbackType)
      setFeedbackDone(true)
      setFeedbackMode('none')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Feedback submission failed')
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const intentStyle = result ? (INTENT_COLORS[result.intent] ?? INTENT_COLORS.general) : null

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
    <div style={{ padding: '32px 40px', maxWidth: 900 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#0a0a0a', margin: 0 }}>
          Ask the Intelligence Layer
        </h1>
        <p style={{ fontSize: 14, color: '#6b7280', margin: '4px 0 0' }}>
          Query what the BD agent knows · get cited, policy-checked answers
        </p>
      </div>

      {/* Query Form */}
      <form onSubmit={handleSubmit}>
        <div
          style={{
            background: '#fafaf8',
            border: '1px solid #e8e8e6',
            borderRadius: 12,
            padding: '20px 24px',
            marginBottom: 16,
          }}
        >
          <textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask anything about your enterprise pipeline, leads, pricing, vendors…"
            rows={3}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e as unknown as React.FormEvent)
            }}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#0a0a0a',
              fontSize: 16,
              resize: 'none',
              fontFamily: 'inherit',
              lineHeight: 1.6,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12, paddingTop: 12, borderTop: '1px solid #e8e8e6' }}>
            <input
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="Entity ID (optional)"
              style={{
                ...inputStyle,
                width: 200,
                fontSize: 12,
                padding: '5px 10px',
                color: '#6b7280',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 11, color: '#9ca3af' }}>⌘+Enter to submit</span>
              <button
                type="submit"
                disabled={loading || !question.trim()}
                style={{
                  background: loading || !question.trim() ? '#f0f0ee' : '#0a0a0a',
                  color: loading || !question.trim() ? '#9ca3af' : '#fff',
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 20px',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {loading ? 'Querying…' : 'Ask →'}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div
          style={{
            background: '#fee2e2',
            border: '1px solid #fca5a5',
            borderRadius: 10,
            padding: '14px 18px',
            color: '#dc2626',
            fontSize: 13,
            marginBottom: 16,
          }}
        >
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div
          style={{
            background: '#fafaf8',
            border: '1px solid #e8e8e6',
            borderRadius: 12,
            padding: '24px',
            marginBottom: 16,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                style={{
                  height: i === 0 ? 14 : 20,
                  width: i === 0 ? '30%' : `${70 + Math.random() * 20}%`,
                  background: 'linear-gradient(90deg, #f0f0ee 25%, #e8e8e6 50%, #f0f0ee 75%)',
                  backgroundSize: '200% 100%',
                  animation: 'pulse 1.5s ease-in-out infinite',
                  borderRadius: 4,
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Result */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Answer card */}
          <div
            style={{
              background: '#fafaf8',
              border: '1px solid #e8e8e6',
              borderRadius: 12,
              padding: '24px',
            }}
          >
            {/* Intent + confidence header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {intentStyle && (
                  <span
                    style={{
                      fontSize: 11,
                      padding: '3px 10px',
                      borderRadius: 20,
                      background: intentStyle.bg,
                      color: intentStyle.text,
                      fontWeight: 600,
                      letterSpacing: '0.03em',
                    }}
                  >
                    {result.intent}
                  </span>
                )}
                {result.policy_violations.length > 0 && result.policy_violations.map((v, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: 11,
                      padding: '3px 10px',
                      borderRadius: 20,
                      background: v.severity === 'block' ? '#fee2e2' : '#fff7ed',
                      color: v.severity === 'block' ? '#dc2626' : '#9a3412',
                      fontWeight: 600,
                    }}
                  >
                    ⚠ {v.rule}
                  </span>
                ))}
              </div>
            </div>

            {/* Answer text */}
            <div
              style={{
                fontSize: 15,
                color: '#0a0a0a',
                lineHeight: 1.7,
                marginBottom: 20,
                whiteSpace: 'pre-wrap',
              }}
            >
              {result.answer}
            </div>

            {/* Confidence bar */}
            <ConfidenceBar value={result.confidence} />

            {/* Citations */}
            {result.citations.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8, fontWeight: 500 }}>
                  SOURCES ({result.citations.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.citations.map((c, i) => (
                    <CitationCard key={i} citation={c} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Feedback section */}
          <div
            style={{
              background: '#fafaf8',
              border: '1px solid #e8e8e6',
              borderRadius: 12,
              padding: '20px 24px',
            }}
          >
            {feedbackDone ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontSize: 14 }}>
                <span>✓</span>
                <span>Feedback submitted — thank you!</span>
              </div>
            ) : (
              <>
                <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 14 }}>Was this helpful?</div>
                <div style={{ display: 'flex', gap: 10, marginBottom: feedbackMode === 'correct' ? 20 : 0 }}>
                  <button
                    onClick={() => { setFeedbackMode('positive'); setFeedbackDone(true) }}
                    style={{
                      background: feedbackMode === 'positive' ? '#dcfce7' : '#ffffff',
                      border: `1px solid ${feedbackMode === 'positive' ? '#10b981' : '#e8e8e6'}`,
                      color: '#10b981',
                      borderRadius: 8,
                      padding: '8px 16px',
                      fontSize: 13,
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    👍 Correct
                  </button>
                  <button
                    onClick={() => setFeedbackMode(feedbackMode === 'correct' ? 'none' : 'correct')}
                    style={{
                      background: feedbackMode === 'correct' ? '#fff7ed' : '#ffffff',
                      border: `1px solid ${feedbackMode === 'correct' ? '#f59e0b' : '#e8e8e6'}`,
                      color: '#f59e0b',
                      borderRadius: 8,
                      padding: '8px 16px',
                      fontSize: 13,
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                  >
                    ✏ Correct it
                  </button>
                </div>

                {feedbackMode === 'correct' && (
                  <form onSubmit={handleFeedbackSubmit} style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div>
                      <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 6 }}>
                        Correct answer
                      </label>
                      <textarea
                        value={correctAnswer}
                        onChange={(e) => setCorrectAnswer(e.target.value)}
                        rows={3}
                        required
                        placeholder="What should the answer have been?"
                        style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 6 }}>
                          Corrected by
                        </label>
                        <input
                          value={correctedBy}
                          onChange={(e) => setCorrectedBy(e.target.value)}
                          style={inputStyle}
                        />
                      </div>
                      <div style={{ flex: 1 }}>
                        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 6 }}>
                          Feedback type
                        </label>
                        <select
                          value={feedbackType}
                          onChange={(e) => setFeedbackType(e.target.value)}
                          style={{ ...inputStyle, cursor: 'pointer' }}
                        >
                          {FEEDBACK_TYPES.map((ft) => (
                            <option key={ft.value} value={ft.value}>{ft.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={feedbackSubmitting || !correctAnswer.trim()}
                      style={{
                        alignSelf: 'flex-start',
                        background: feedbackSubmitting ? '#f0f0ee' : '#0a0a0a',
                        color: feedbackSubmitting ? '#9ca3af' : '#fff',
                        border: 'none',
                        borderRadius: 8,
                        padding: '8px 20px',
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: feedbackSubmitting ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {feedbackSubmitting ? 'Submitting…' : 'Submit Correction'}
                    </button>
                  </form>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* History + Suggested Queries */}
      <div style={{ marginTop: 32 }}>
        {history.length > 0 && (
          <>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: '#6b7280', marginBottom: 12, letterSpacing: '0.05em' }}>
              RECENT QUERIES
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 24 }}>
              {history.map((h, i) => (
                <button
                  key={i}
                  onClick={() => setQuestion(h.question)}
                  style={{
                    background: '#fafaf8',
                    border: '1px solid #e8e8e6',
                    borderRadius: 8,
                    padding: '10px 14px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                    transition: 'border-color 0.15s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#ffde59')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#e8e8e6')}
                >
                  <span style={{ fontSize: 13, color: '#404852', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {h.question}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                    <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: '#fefce8', color: '#854d0e' }}>
                      {h.intent}
                    </span>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>
                      {new Date(h.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}

        <h2 style={{ fontSize: 14, fontWeight: 600, color: '#6b7280', marginBottom: 12, letterSpacing: '0.05em' }}>
          SUGGESTED QUERIES
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {SUGGESTED_QUERIES.map((s, i) => (
            <button
              key={i}
              onClick={() => setQuestion(s.question)}
              style={{
                background: '#fafaf8',
                border: '1px solid #e8e8e6',
                borderRadius: 8,
                padding: '10px 14px',
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                transition: 'border-color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#ffde59')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#e8e8e6')}
            >
              <span style={{ fontSize: 13, color: '#404852', flex: 1 }}>
                {s.question}
              </span>
              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: '#fefce8', color: '#854d0e', flexShrink: 0 }}>
                {s.intent.replace(/_/g, ' ')}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
