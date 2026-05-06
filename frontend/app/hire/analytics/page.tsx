'use client'

import { useEffect, useState } from 'react'
import { getAnalytics, AnalyticsResponse, AnalyticsFunnelItem, AnalyticsRoleRow } from '../../../lib/hire-api'

const STAGE_LABELS: Record<string, string> = {
  applied: 'Applied', pre_screening: 'Pre-screening', pre_screened: 'Pre-screened',
  test_invited: 'Test Invited', screened: 'Screened', shortlisted: 'Shortlisted',
  offer_sent: 'Offer Sent', hired: 'Hired',
}

const STAGE_COLORS: Record<string, string> = {
  applied: '#888888', pre_screening: '#ff6ea8', pre_screened: '#ff2d78',
  test_invited: '#f59e0b', screened: '#10b981', shortlisted: '#10b981',
  offer_sent: '#ff2d78', hired: '#10b981',
}

const CARD: React.CSSProperties = { background: '#111111', border: '1px solid #1f1f1f', borderRadius: 12, padding: '20px 22px' }
const TITLE: React.CSSProperties = { fontSize: 11, fontWeight: 700, color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 18, marginTop: 0 }

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div style={{ ...CARD, textAlign: 'center' }}>
      <div style={{ fontSize: 36, fontWeight: 700, color: accent ?? '#ffffff', lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 13, color: '#888', marginTop: 8 }}>{label}</div>
      {sub ? <div style={{ fontSize: 11, color: '#444', marginTop: 4 }}>{sub}</div> : null}
    </div>
  )
}

function FunnelBar({ item, maxCount }: { item: AnalyticsFunnelItem; maxCount: number }) {
  const pct = maxCount > 0 ? (item.count / maxCount) * 100 : 0
  const color = STAGE_COLORS[item.stage] ?? '#888'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: '#ccc' }}>{STAGE_LABELS[item.stage] ?? item.stage}</span>
        <span style={{ fontSize: 13, color: '#666' }}>{item.count} <span style={{ color: '#444', fontSize: 11 }}>({item.rate}%)</span></span>
      </div>
      <div style={{ height: 6, background: '#1f1f1f', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 999, transition: 'width 0.5s' }} />
      </div>
    </div>
  )
}

function RoleTable({ rows }: { rows: AnalyticsRoleRow[] }) {
  const fmt = (v: number | null) => v !== null ? v.toFixed(1) : '—'
  const scoreCol = (v: number | null) => v === null ? '#444' : v >= 70 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr>
          {['Role', 'Total', 'Avg Resume', 'Avg Screen'].map((h) => (
            <th key={h} style={{ textAlign: h === 'Role' ? 'left' : 'right', color: '#555', fontWeight: 600, paddingBottom: 10, borderBottom: '1px solid #1f1f1f', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.role}>
            <td style={{ color: '#ffffff', padding: '10px 0', borderBottom: '1px solid #1f1f1f33' }}>{row.role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</td>
            <td style={{ color: '#888', textAlign: 'right', padding: '10px 0', borderBottom: '1px solid #1f1f1f33' }}>{row.total}</td>
            <td style={{ textAlign: 'right', padding: '10px 0', borderBottom: '1px solid #1f1f1f33', color: scoreCol(row.avg_resume) }}>{fmt(row.avg_resume)}</td>
            <td style={{ textAlign: 'right', padding: '10px 0', borderBottom: '1px solid #1f1f1f33', color: scoreCol(row.avg_screen) }}>{fmt(row.avg_screen)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function WeeklyChart({ data }: { data: { week: string; count: number }[] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 100 }}>
      {data.map((d) => {
        const pct = (d.count / maxCount) * 100
        const label = new Date(d.week).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
        return (
          <div key={d.week} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <span style={{ fontSize: 10, color: '#888' }}>{d.count}</span>
            <div style={{ width: '100%', height: `${pct}%`, minHeight: 4, background: '#ff2d78', borderRadius: '3px 3px 0 0', opacity: 0.8 }} />
            <span style={{ fontSize: 9, color: '#444', whiteSpace: 'nowrap' }}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getAnalytics().then(setData).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load')).finally(() => setLoading(false))
  }, [])

  if (loading) return <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#555', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading…</div>
  if (error || !data) return <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{error ?? 'No data'}</div>

  const hired = data.stage_counts['hired'] ?? 0
  const shortlisted = data.stage_counts['shortlisted'] ?? 0
  const screened = data.stage_counts['screened'] ?? 0
  const rejected = data.stage_counts['rejected'] ?? 0
  const maxFunnel = data.funnel.reduce((m, f) => Math.max(m, f.count), 1)
  const passRate = data.total > 0 ? (((hired + shortlisted + (data.stage_counts['offer_sent'] ?? 0)) / data.total) * 100).toFixed(0) : '0'

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#ffffff', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ padding: '20px 28px', borderBottom: '1px solid #1f1f1f', background: '#0d0d0d' }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#ffffff' }}>Hiring Analytics</h1>
        <div style={{ color: '#555', fontSize: 13, marginTop: 2 }}>{data.total} total applications across all roles</div>
      </div>

      <div style={{ padding: '24px 28px', maxWidth: 1100 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
          <StatCard label="Total Applications" value={data.total} accent="#ff6ea8" />
          <StatCard label="Screened" value={screened} sub={data.total > 0 ? `${((screened / data.total) * 100).toFixed(0)}% conversion` : undefined} accent="#10b981" />
          <StatCard label="Hired / Shortlisted" value={hired} sub={shortlisted > 0 ? `${shortlisted} shortlisted` : undefined} accent="#ff2d78" />
          <StatCard label="Rejection Rate" value={`${data.total > 0 ? ((rejected / data.total) * 100).toFixed(0) : 0}%`} sub={`${rejected} rejected`} accent="#ef4444" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
          <div style={CARD}>
            <p style={TITLE}>Pipeline Funnel</p>
            {data.funnel.map((item) => <FunnelBar key={item.stage} item={item} maxCount={maxFunnel} />)}
          </div>
          <div style={CARD}>
            <p style={TITLE}>Weekly Intake (last 10 weeks)</p>
            {data.weekly_intake.length > 0 ? <WeeklyChart data={data.weekly_intake} /> : <div style={{ color: '#444', fontSize: 13 }}>No data yet</div>}
            <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #1f1f1f', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#ff2d78' }}>{passRate}%</div>
                <div style={{ fontSize: 12, color: '#555', marginTop: 2 }}>Offer / Pipeline rate</div>
              </div>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#ff6ea8' }}>{data.by_role.length}</div>
                <div style={{ fontSize: 12, color: '#555', marginTop: 2 }}>Active roles</div>
              </div>
            </div>
          </div>
        </div>

        <div style={CARD}>
          <p style={TITLE}>Scores by Role</p>
          {data.by_role.length > 0 ? <RoleTable rows={data.by_role} /> : <div style={{ color: '#444', fontSize: 13 }}>No applications yet</div>}
        </div>
      </div>
    </div>
  )
}
