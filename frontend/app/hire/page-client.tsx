'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { getPipeline, CandidateCard, PipelineResponse } from '../../lib/hire-api'

const STAGES = [
  { key: 'applied', label: 'Applied', color: '#888888' },
  { key: 'pre_screening', label: 'Pre-screening', color: '#ff6ea8' },
  { key: 'pre_screened', label: 'Pre-screened', color: '#ff2d78' },
  { key: 'test_invited', label: 'Test Invited', color: '#f59e0b' },
  { key: 'screened', label: 'Screened', color: '#10b981' },
  { key: 'hr_approved', label: 'HR Approved', color: '#06b6d4' },
  { key: 'shortlisted', label: 'Shortlisted', color: '#10b981' },
  { key: 'offer_sent', label: 'Offer Sent', color: '#ff2d78' },
  { key: 'hired', label: 'Hired', color: '#10b981' },
  { key: 'rejected', label: 'Rejected', color: '#ef4444' },
]

function scoreColor(score: number | null): string {
  if (score === null) return '#555'
  if (score >= 70) return '#10b981'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}

function ScorePill({ label, score }: { label: string; score: number | null }) {
  if (score === null) return null
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: 999,
      fontSize: 11, fontWeight: 600,
      background: scoreColor(score) + '22', color: scoreColor(score), marginRight: 4,
    }}>
      {label} {score}
    </span>
  )
}

function CandidateCardComp({ card, onClick }: { card: CandidateCard; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: '#191919', border: '1px solid #2a2a2a', borderRadius: 8,
        padding: '8px 10px', marginBottom: 6, cursor: 'pointer', transition: 'border-color 0.15s',
      }}
      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#ff2d78' }}
      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#2a2a2a' }}
    >
      <div style={{ fontWeight: 600, color: '#ffffff', fontSize: 13, marginBottom: 2 }}>{card.name}</div>
      <div style={{ color: '#666', fontSize: 12, marginBottom: 6 }}>{card.role}</div>
      <div>
        <ScorePill label="R" score={card.resume_score} />
        <ScorePill label="S" score={card.screen_score} />
      </div>
    </div>
  )
}

function KanbanColumn({ stageKey, label, color, cards, onCardClick }: {
  stageKey: string; label: string; color: string; cards: CandidateCard[]; onCardClick: (id: string) => void
}) {
  return (
    <div style={{
      width: 190, flexShrink: 0, display: 'flex', flexDirection: 'column',
      background: '#111111', border: '1px solid #1f1f1f', borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 10px', borderBottom: '1px solid #1f1f1f',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontWeight: 700, color, fontSize: 13 }}>{label}</span>
        <span style={{ background: color + '22', color, borderRadius: 999, fontSize: 11, fontWeight: 700, padding: '1px 8px' }}>
          {cards.length}
        </span>
      </div>
      <div style={{ padding: '10px 10px', overflowY: 'auto', flex: 1 }}>
        {cards.map((card) => (
          <CandidateCardComp key={card.id} card={card} onClick={() => onCardClick(card.id)} />
        ))}
        {cards.length === 0 ? (
          <div style={{ color: '#444', fontSize: 12, textAlign: 'center', marginTop: 16 }}>No candidates</div>
        ) : null}
      </div>
    </div>
  )
}

export default function PipelineClient() {
  const router = useRouter()
  const [data, setData] = useState<PipelineResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getPipeline()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load pipeline')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const totalCandidates = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#ffffff', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{
        padding: '20px 28px', borderBottom: '1px solid #1f1f1f',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#0d0d0d',
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#ffffff' }}>Hiring Pipeline</h1>
          {data ? <span style={{ color: '#555', fontSize: 13 }}>{totalCandidates} total candidates</span> : null}
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {error ? <span style={{ color: '#ef4444', fontSize: 13 }}>{error}</span> : null}
          <button
            onClick={load} disabled={loading}
            style={{
              background: '#191919', color: '#ffffff', border: '1px solid #2a2a2a',
              borderRadius: 8, padding: '7px 16px', fontSize: 13,
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      <div style={{
        overflowX: 'auto', overflowY: 'visible', padding: '16px 20px 24px',
        display: 'flex', gap: 10, alignItems: 'flex-start',
        minHeight: 'calc(100vh - 80px)', width: '100%', boxSizing: 'border-box',
        WebkitOverflowScrolling: 'touch',
      }}>
        {STAGES.map((stage) => (
          <KanbanColumn
            key={stage.key} stageKey={stage.key} label={stage.label} color={stage.color}
            cards={data ? (data.by_stage[stage.key] ?? []) : []}
            onCardClick={(id) => router.push(`/hire/candidates/${id}`)}
          />
        ))}
      </div>
    </div>
  )
}
