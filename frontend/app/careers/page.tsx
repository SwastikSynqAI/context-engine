'use client'

import { useState } from 'react'
import Link from 'next/link'

interface Job {
  id: string
  title: string
  department: string
  locations: string[]
  type: string
  experience: string
  description: string
  responsibilities: string[]
  requirements: string[]
}

const JOBS: Job[] = [
  {
    id: 'bd_manager',
    title: 'Business Development Manager',
    department: 'Business Development',
    locations: ['Bangalore', 'Delhi NCR', 'Mumbai'],
    type: 'Full-time',
    experience: '3–7 years',
    description:
      "Drive enterprise sales and build long-term client relationships for YourCompany's managed office portfolio across India. You'll own the full sales cycle — from identifying enterprise leads to closing multi-crore facility contracts.",
    responsibilities: [
      'Own the full B2B sales cycle for enterprise managed office mandates',
      'Build and maintain a robust pipeline of 50K+ sq ft corporate clients',
      'Partner with operations and design teams to craft winning proposals',
      'Represent YourCompany at industry events and build broker relationships',
      'Consistently hit quarterly revenue targets',
    ],
    requirements: [
      '3–7 years in B2B enterprise sales (real estate, SaaS, or professional services preferred)',
      'Track record of closing significant enterprise deals',
      'Strong CRM discipline and pipeline management habits',
      'Excellent communication and executive presence',
      'Willingness to travel across metro cities',
    ],
  },
  {
    id: 'operations_manager',
    title: 'Operations Manager — Managed Offices',
    department: 'Operations & Facilities',
    locations: ['Bangalore', 'Delhi NCR', 'Mumbai'],
    type: 'Full-time',
    experience: '4–8 years',
    description:
      "Lead day-to-day operations across YourCompany's managed office portfolio. You'll own vendor performance, facility SLAs, and client experience across 500K+ sq ft of premium workspace.",
    responsibilities: [
      'Manage a portfolio of 3–5 managed office sites end-to-end',
      'Own housekeeping, security, MEP, and soft services vendors',
      'Drive SLA compliance and escalate client-impacting issues fast',
      'Implement process improvements to reduce cost and improve CSAT',
      'Build and mentor a team of on-site facility coordinators',
    ],
    requirements: [
      '4–8 years in facility management, IFM, or flex workspace operations',
      'Experience managing 100K+ sq ft facilities',
      'Strong vendor negotiation and contract management skills',
      'Working knowledge of HVAC, BMS, and electrical systems',
      'Hands-on, detail-oriented leader with high EQ',
    ],
  },
]

function JobCard({ job }: { job: Job }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      style={{
        background: '#12121a',
        border: '1px solid #1e1e2e',
        borderRadius: 14,
        padding: '24px 28px',
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0, fontSize: 19, fontWeight: 700, color: '#f1f5f9' }}>{job.title}</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
            {[job.department, job.locations.join(' / '), job.type, job.experience].map((tag) => (
              <span
                key={tag}
                style={{
                  background: '#1e1e2e',
                  color: '#94a3b8',
                  fontSize: 11,
                  padding: '3px 10px',
                  borderRadius: 999,
                  fontWeight: 500,
                }}
              >
                {tag}
              </span>
            ))}
          </div>
          <p style={{ margin: '14px 0 0', color: '#94a3b8', fontSize: 14, lineHeight: 1.65, maxWidth: 600 }}>
            {job.description}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0 }}>
          <Link
            href={`/apply?role=${job.id}`}
            style={{
              background: '#10b981',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '10px 22px',
              fontSize: 14,
              fontWeight: 700,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              textDecoration: 'none',
              display: 'block',
              textAlign: 'center',
            }}
          >
            Apply Now
          </Link>
          <button
            onClick={() => setOpen((v) => !v)}
            style={{
              background: 'transparent',
              color: '#94a3b8',
              border: '1px solid #1e1e2e',
              borderRadius: 8,
              padding: '8px 16px',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            {open ? 'Hide details' : 'View details'}
          </button>
        </div>
      </div>

      {open ? (
        <div style={{ marginTop: 22, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, paddingTop: 20, borderTop: '1px solid #1e1e2e' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
              Responsibilities
            </div>
            <ul style={{ margin: 0, padding: '0 0 0 16px', color: '#94a3b8', fontSize: 13, lineHeight: 1.9 }}>
              {job.responsibilities.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 10 }}>
              Requirements
            </div>
            <ul style={{ margin: 0, padding: '0 0 0 16px', color: '#94a3b8', fontSize: 13, lineHeight: 1.9 }}>
              {job.requirements.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default function CareersPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0f', color: '#f1f5f9', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Nav */}
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
            <div style={{ fontSize: 10, color: '#6b7280' }}>Careers</div>
          </div>
        </div>
        <a href="https://yourcompany.com" style={{ color: '#94a3b8', fontSize: 13, textDecoration: 'none' }}>
          yourcompany.com ↗
        </a>
      </div>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '52px 32px 80px' }}>
        {/* Hero */}
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: '#052e16', color: '#10b981',
            fontSize: 11, fontWeight: 700, letterSpacing: '0.1em',
            padding: '5px 14px', borderRadius: 999, textTransform: 'uppercase', marginBottom: 18,
          }}>
            <span style={{ width: 6, height: 6, background: '#10b981', borderRadius: '50%', display: 'inline-block' }} />
            We're hiring
          </div>
          <h1 style={{ fontSize: 40, fontWeight: 800, margin: '0 0 16px', lineHeight: 1.15, letterSpacing: '-0.01em' }}>
            Build the future of<br />
            <span style={{ color: '#10b981' }}>managed workspaces</span>
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 15, maxWidth: 520, margin: '0 auto', lineHeight: 1.7 }}>
            YourCompany operates 500K+ sq ft of premium managed offices across India's top metros.
            Join a fast-growing team that's redefining how enterprises work.
          </p>
        </div>

        {/* Stats strip */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 48, borderRadius: 12, overflow: 'hidden', border: '1px solid #1e1e2e' }}>
          {[
            { n: '500K+', label: 'sq ft managed' },
            { n: '3', label: 'metro cities' },
            { n: '50+', label: 'enterprise clients' },
            { n: '2019', label: 'founded' },
          ].map((s, i) => (
            <div key={s.label} style={{ flex: 1, padding: '20px 0', textAlign: 'center', background: '#12121a', borderRight: i < 3 ? '1px solid #1e1e2e' : 'none' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#f1f5f9' }}>{s.n}</div>
              <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Job listings */}
        <div style={{ fontSize: 11, fontWeight: 700, color: '#4b5563', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 16 }}>
          {JOBS.length} open position{JOBS.length !== 1 ? 's' : ''}
        </div>

        {JOBS.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}

        {/* General apply CTA */}
        <div style={{
          marginTop: 32,
          background: '#12121a',
          border: '1px solid #1e1e2e',
          borderRadius: 14,
          padding: '28px 32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 24,
        }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>Don't see your role?</div>
            <div style={{ fontSize: 13, color: '#94a3b8' }}>
              We're always interested in exceptional talent. Send us a general application.
            </div>
          </div>
          <Link
            href="/apply"
            style={{
              background: 'transparent',
              color: '#10b981',
              border: '1px solid #10b981',
              borderRadius: 8,
              padding: '10px 22px',
              fontSize: 14,
              fontWeight: 600,
              textDecoration: 'none',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            Apply Anyway →
          </Link>
        </div>
      </div>

      <div style={{ borderTop: '1px solid #1e1e2e', padding: '18px 32px', textAlign: 'center', color: '#374151', fontSize: 12 }}>
        Your Company Legal Name · hiring@example.com · yourcompany.com
      </div>
    </div>
  )
}
