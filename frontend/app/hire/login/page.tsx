'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { loginAdmin, saveToken } from '@/lib/hire-api'

export default function HireLoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginAdmin(email, password)
      saveToken(data.access_token)
      router.replace('/hire')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const fieldStyle: React.CSSProperties = {
    width: '100%',
    background: '#0d0d0d',
    border: '1px solid #2a2a2a',
    borderRadius: 8,
    padding: '10px 12px',
    color: '#ffffff',
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block',
    fontSize: 12,
    color: '#888',
    marginBottom: 6,
    fontWeight: 500,
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: 380, background: '#111111', border: '1px solid #1f1f1f', borderRadius: 16, padding: '40px 48px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ width: 32, height: 32, background: '#ff2d78', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 4h4v4H3V4zM9 4h4v4H9V4zM3 10h4v3H3v-3z" fill="white" opacity="0.9"/>
                <path d="M9 10h4v3H9v-3z" fill="white" opacity="0.6"/>
              </svg>
            </div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#ffffff', margin: 0 }}>AI Hire</h1>
          </div>
          <p style={{ fontSize: 13, color: '#555', margin: 0 }}>Admin dashboard — sign in to continue</p>
        </div>

        {error && (
          <div style={{ background: '#1a0a0a', border: '1px solid #7f1d1d', color: '#ef4444', borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 20 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={labelStyle} htmlFor="hire-email">Email</label>
            <input id="hire-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={fieldStyle} placeholder="admin@example.com" />
          </div>
          <div>
            <label style={labelStyle} htmlFor="hire-password">Password</label>
            <input id="hire-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required style={fieldStyle} placeholder="••••••••" />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 8, width: '100%', padding: '11px 0', borderRadius: 8, border: 'none',
              background: loading ? '#2a2a2a' : '#ff2d78',
              color: loading ? '#555' : '#ffffff',
              fontSize: 14, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', transition: 'background 0.15s',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
