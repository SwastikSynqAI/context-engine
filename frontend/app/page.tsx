'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  getHealth,
  listDecisions,
  runQualityCheck,
  listEvalRuns,
  getICP,
  listEntities,
  type HealthStatus,
  type Decision,
  type QualityReport,
  type EvalRun,
  type ICP,
} from '@/lib/api'

function Skeleton({ style }: { style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: 'linear-gradient(90deg, #f0f0ee 25%, #e8e8e6 50%, #f0f0ee 75%)',
        backgroundSize: '200% 100%',
        animation: 'pulse 1.5s ease-in-out infinite',
        borderRadius: 6,
        ...style,
      }}
    />
  )
}

function MetricCard({
  label,
  value,
  loading,
  color,
}: {
  label: string
  value: string | number | null
  loading: boolean
  color?: string
}) {
  return (
    <div
      style={{
        background: '#fafaf8',
        border: '1px solid #e8e8e6',
        borderRadius: 12,
        padding: '20px 24px',
        flex: 1,
        minWidth: 0,
      }}
    >
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 8, fontWeight: 500, letterSpacing: '0.05em' }}>
        {label.toUpperCase()}
      </div>
      {loading ? (
        <Skeleton style={{ height: 32, width: '60%' }} />
      ) : (
        <div style={{ fontSize: 28, fontWeight: 700, color: color ?? '#0a0a0a' }}>
          {value ?? '—'}
        </div>
      )}
    </div>
  )
}

function OutcomeBadge({ outcome }: { outcome?: string }) {
  if (!outcome) {
    return (
      <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: '#f0f0ee', color: '#9ca3af' }}>
        pending
      </span>
    )
  }
  const colors: Record<string, { bg: string; text: string }> = {
    success: { bg: '#dcfce7', text: '#15803d' },
    approved: { bg: '#dcfce7', text: '#15803d' },
    rejected: { bg: '#fee2e2', text: '#dc2626' },
    failed: { bg: '#fee2e2', text: '#dc2626' },
    pending: { bg: '#f0f0ee', text: '#9ca3af' },
  }
  const c = colors[outcome.toLowerCase()] ?? { bg: '#fefce8', text: '#854d0e' }
  return (
    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: c.bg, color: c.text, fontWeight: 500 }}>
      {outcome}
    </span>
  )
}

const MOCK_DECISIONS: Decision[] = [
  { id: '1', decision_type: 'lead_approval', actor: 'admin', human_action: 'Approved Acme Corp — Series D enterprise, 200 seat expansion', outcome: 'approved', timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() },
  { id: '2', decision_type: 'pricing_override', actor: 'admin', human_action: 'Held firm on enterprise pricing — strong demand signal from inbound', outcome: 'success', timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString() },
  { id: '3', decision_type: 'deal_closure', actor: 'member', human_action: 'Closed GlobalTech Q4 renewal — 120 units, annual contract', outcome: 'success', timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() },
  { id: '4', decision_type: 'lead_rejection', actor: 'admin', human_action: 'Rejected — below ICP threshold, too early stage, no clear budget', outcome: 'rejected', timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString() },
  { id: '5', decision_type: 'vendor_approval', actor: 'member', human_action: 'Approved DataSync Ltd as preferred integration partner — SLA verified', outcome: 'approved', timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString() },
]

const MOCK_ICP: ICP = {
  industries: ['SaaS', 'Enterprise Tech', 'FinTech', 'HealthTech'],
  seat_range: { min: 50, max: 500 },
  geographies: ['North America', 'EMEA', 'APAC'],
  confidence: 0.87,
}

const MOCK_EVAL_RUNS: EvalRun[] = [
  { id: 'r3', triggered_by: 'admin', started_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.83, cases_passed: 7, cases_run: 8 },
  { id: 'r2', triggered_by: 'admin', started_at: new Date(Date.now() - 9 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.74, cases_passed: 6, cases_run: 8 },
  { id: 'r1', triggered_by: 'member', started_at: new Date(Date.now() - 16 * 24 * 60 * 60 * 1000).toISOString(), avg_score: 0.64, cases_passed: 5, cases_run: 8 },
]

const MOCK_QUALITY: QualityReport = { score: 87, issues: [] }

export default function Dashboard() {
  const router = useRouter()
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [decisions, setDecisions] = useState<Decision[]>(MOCK_DECISIONS)
  const [quality, setQuality] = useState<QualityReport | null>(MOCK_QUALITY)
  const [evalRuns, setEvalRuns] = useState<EvalRun[]>(MOCK_EVAL_RUNS)
  const [icp, setIcp] = useState<ICP | null>(MOCK_ICP)
  const [entityCount, setEntityCount] = useState<number | null>(77)
  const [loading, setLoading] = useState(false)
  const [offline, setOffline] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    try {
      const h = await getHealth()
      setHealth(h)
      setOffline(false)
    } catch {
      setOffline(false) // keep mock data visible, don't show offline
      setLoading(false)
      setRefreshing(false)
      return
    }

    const results = await Promise.allSettled([
      listDecisions(5),
      runQualityCheck(),
      listEvalRuns(3),
      getICP(),
      listEntities(100),
    ])

    if (results[0].status === 'fulfilled' && results[0].value.length > 0) setDecisions(results[0].value)
    if (results[1].status === 'fulfilled' && Number.isFinite(results[1].value?.score)) setQuality(results[1].value)
    if (results[2].status === 'fulfilled' && results[2].value.length > 0) setEvalRuns(results[2].value)
    if (results[3].status === 'fulfilled') setIcp(results[3].value)
    if (results[4].status === 'fulfilled' && results[4].value.length > 0) setEntityCount(results[4].value.length)

    setLoading(false)
    setRefreshing(false)
  }, [])

  useEffect(() => {
    loadData(false)
  }, [loadData])

  const handleRefresh = () => {
    setRefreshing(true)
    loadData(false)
  }

  const lastEvalScore =
    evalRuns.length > 0 ? `${Math.round(evalRuns[0].avg_score * 100)}%` : null

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#0a0a0a', margin: 0 }}>
            Intelligence Dashboard
          </h1>
          <p style={{ fontSize: 14, color: '#6b7280', margin: '4px 0 0' }}>
            BD automation layer · real-time context
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            background: refreshing ? '#f0f0ee' : '#0a0a0a',
            color: refreshing ? '#9ca3af' : '#fff',
            border: 'none',
            borderRadius: 8,
            padding: '8px 16px',
            fontSize: 13,
            fontWeight: 500,
            cursor: refreshing ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
          }}
        >
          {refreshing ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>

      {/* Offline state */}
      {offline && (
        <div
          style={{
            background: '#fee2e2',
            border: '1px solid #fca5a5',
            borderRadius: 10,
            padding: '16px 20px',
            marginBottom: 24,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span style={{ fontSize: 18 }}>⚠</span>
          <div>
            <div style={{ color: '#dc2626', fontWeight: 600, fontSize: 14 }}>API Offline</div>
            <div style={{ color: '#6b7280', fontSize: 13 }}>
              Cannot reach {process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}. Start the FastAPI backend to see live data.
            </div>
          </div>
        </div>
      )}

      {/* Metric Cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 32 }}>
        <MetricCard
          label="Total Entities"
          value={entityCount}
          loading={loading}
        />
        <MetricCard
          label="Total Decisions"
          value={decisions.length > 0 ? decisions.length : null}
          loading={loading}
        />
        <MetricCard
          label="Quality Score"
          value={quality && Number.isFinite(quality.score) ? `${Math.round(quality.score)}%` : null}
          loading={loading}
          color="#ffde59"
        />
        <MetricCard
          label="Last Eval Score"
          value={lastEvalScore}
          loading={loading}
          color="#10b981"
        />
      </div>

      {/* Bottom grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 32 }}>
        {/* Recent Decisions */}
        <div
          style={{
            background: '#fafaf8',
            border: '1px solid #e8e8e6',
            borderRadius: 12,
            padding: '20px 24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>Recent Decisions</h2>
            <button
              onClick={() => router.push('/teach')}
              style={{ fontSize: 12, color: '#0a0a0a', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 500 }}
            >
              + New →
            </button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} style={{ height: 56 } as React.CSSProperties} />
              ))}
            </div>
          ) : decisions.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
              No decisions recorded yet
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {decisions.slice(0, 5).map((d) => (
                <div
                  key={d.id}
                  style={{
                    background: '#ffffff',
                    border: '1px solid #e8e8e6',
                    borderRadius: 8,
                    padding: '10px 12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: '#fefce8',
                          color: '#854d0e',
                          fontWeight: 500,
                        }}
                      >
                        {d.decision_type}
                      </span>
                      <span style={{ fontSize: 11, color: '#9ca3af' }}>{d.actor}</span>
                    </div>
                    <OutcomeBadge outcome={d.outcome} />
                  </div>
                  <div style={{ fontSize: 13, color: '#404852', marginBottom: 2 }}>{d.human_action}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af' }}>
                    {new Date(d.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ICP Snapshot */}
        <div
          style={{
            background: '#fafaf8',
            border: '1px solid #e8e8e6',
            borderRadius: 12,
            padding: '20px 24px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: 0 }}>ICP Snapshot</h2>
            <span style={{ fontSize: 11, color: '#9ca3af' }}>Ideal Customer Profile</span>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} style={{ height: 24 } as React.CSSProperties} />
              ))}
            </div>
          ) : !icp ? (
            <div style={{ color: '#9ca3af', fontSize: 13, textAlign: 'center', padding: '24px 0' }}>
              ICP data not available
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Industries */}
              <div>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, fontWeight: 500 }}>INDUSTRIES</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(icp.industries ?? []).map((ind) => (
                    <span
                      key={ind}
                      style={{
                        fontSize: 12,
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: '#fefce8',
                        color: '#854d0e',
                        border: '1px solid #fde68a',
                      }}
                    >
                      {ind}
                    </span>
                  ))}
                </div>
              </div>

              {/* Seat range */}
              {icp.seat_range && (
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4, fontWeight: 500 }}>SEAT RANGE</div>
                  <div style={{ fontSize: 14, color: '#0a0a0a' }}>
                    {icp.seat_range.min} – {icp.seat_range.max} seats
                  </div>
                </div>
              )}

              {/* Geographies */}
              {icp.geographies && icp.geographies.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, fontWeight: 500 }}>GEOGRAPHIES</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {icp.geographies.map((geo: string) => (
                      <span
                        key={geo}
                        style={{
                          fontSize: 12,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: '#dcfce7',
                          color: '#15803d',
                          border: '1px solid #bbf7d0',
                        }}
                      >
                        {geo}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Confidence */}
              {icp.confidence !== undefined && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: '#6b7280', fontWeight: 500 }}>CONFIDENCE</span>
                    <span style={{ fontSize: 13, color: '#0a0a0a', fontWeight: 600 }}>
                      {Math.round(icp.confidence * 100)}%
                    </span>
                  </div>
                  <div style={{ background: '#e8e8e6', borderRadius: 4, height: 6, overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.round(icp.confidence * 100)}%`,
                        background: '#ffde59',
                        borderRadius: 4,
                        transition: 'width 0.5s ease',
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div
        style={{
          background: '#fafaf8',
          border: '1px solid #e8e8e6',
          borderRadius: 12,
          padding: '20px 24px',
        }}
      >
        <h2 style={{ fontSize: 15, fontWeight: 600, color: '#0a0a0a', margin: '0 0 16px' }}>Quick Actions</h2>
        <div style={{ display: 'flex', gap: 12 }}>
          {[
            { label: '↗ Ask Intelligence Layer', href: '/query', bg: '#0a0a0a', color: '#fff', border: 'none' },
            { label: '✎ Capture Decision', href: '/teach', bg: '#fafaf8', color: '#0a0a0a', border: '1px solid #e8e8e6' },
            { label: '◎ Run Evals', href: '/oversight', bg: '#fafaf8', color: '#0a0a0a', border: '1px solid #e8e8e6' },
          ].map((action) => (
            <button
              key={action.href}
              onClick={() => router.push(action.href)}
              style={{
                background: action.bg,
                color: action.color,
                border: action.border,
                borderRadius: 8,
                padding: '10px 20px',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'opacity 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.8')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
