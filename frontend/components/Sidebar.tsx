'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import clsx from 'clsx'

const hireNavItems = [
  {
    href: '/hire',
    label: 'Pipeline',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="3" width="3" height="10" rx="1" fill="currentColor" opacity="0.7" />
        <rect x="6" y="5" width="3" height="8" rx="1" fill="currentColor" opacity="0.7" />
        <rect x="11" y="7" width="3" height="6" rx="1" fill="currentColor" opacity="0.7" />
      </svg>
    ),
  },
  {
    href: '/hire/analytics',
    label: 'Analytics',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 13L5 8L8 10L11 5L14 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
        <circle cx="14" cy="3" r="1.5" fill="currentColor" opacity="0.7" />
      </svg>
    ),
  },
  {
    href: '/hire/settings',
    label: 'HR Settings',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
        <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.42 1.42M11.53 11.53l1.42 1.42M3.05 12.95l1.42-1.42M11.53 4.47l1.42-1.42" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      </svg>
    ),
  },
]

const navItems = [
  {
    href: '/',
    label: 'Dashboard',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="1" y="1" width="6" height="6" rx="1" fill="currentColor" opacity="0.7" />
        <rect x="9" y="1" width="6" height="6" rx="1" fill="currentColor" opacity="0.7" />
        <rect x="1" y="9" width="6" height="6" rx="1" fill="currentColor" opacity="0.7" />
        <rect x="9" y="9" width="6" height="6" rx="1" fill="currentColor" opacity="0.7" />
      </svg>
    ),
  },
  {
    href: '/query',
    label: 'Ask',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
        <path d="M6 6.5C6 5.4 6.9 4.5 8 4.5C9.1 4.5 10 5.4 10 6.5C10 7.4 9.4 8.1 8.6 8.4C8.3 8.5 8 8.8 8 9.1V9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
        <circle cx="8" cy="11.5" r="0.75" fill="currentColor" opacity="0.7" />
      </svg>
    ),
  },
  {
    href: '/teach',
    label: 'Teach',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M2 4L8 1L14 4V8C14 11 11 13.5 8 15C5 13.5 2 11 2 8V4Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity="0.7" />
        <path d="M5.5 8L7 9.5L10.5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
      </svg>
    ),
  },
  {
    href: '/oversight',
    label: 'Oversight',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 2C4.7 2 2 4.7 2 8C2 11.3 4.7 14 8 14C11.3 14 14 11.3 14 8C14 4.7 11.3 2 8 2Z" stroke="currentColor" strokeWidth="1.5" opacity="0.7" />
        <path d="M8 5V8.5L10.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
      </svg>
    ),
  },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside
      style={{ width: 240, minHeight: '100vh', backgroundColor: '#0a0a0a', borderRight: '1px solid #1a1a1a' }}
      className="flex flex-col"
    >
      {/* Logo */}
      <div className="px-5 py-6" style={{ borderBottom: '1px solid #1a1a1a' }}>
        <div className="flex items-center gap-2">
          <div
            style={{ width: 28, height: 28, background: '#ffde59', borderRadius: 6 }}
            className="flex items-center justify-center flex-shrink-0"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M2 2H6V6H2V2Z" fill="#0a0a0a" opacity="0.9" />
              <path d="M8 2H12V6H8V2Z" fill="#0a0a0a" opacity="0.5" />
              <path d="M2 8H6V12H2V8Z" fill="#0a0a0a" opacity="0.5" />
              <path d="M8 8H12V12H8V8Z" fill="#0a0a0a" opacity="0.9" />
            </svg>
          </div>
          <div>
            <div
              style={{ fontSize: 13, fontVariant: 'small-caps', letterSpacing: '0.08em', color: '#ffffff', fontWeight: 600 }}
            >
              context engine
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.04em' }}>
              intelligence layer
            </div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3">
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', fontWeight: 600, padding: '0 8px 8px' }}>
          NAVIGATION
        </div>
        <ul className="space-y-1 list-none m-0 p-0">
          {navItems.map((item) => {
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href)

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-150 no-underline',
                  )}
                  style={
                    isActive
                      ? { borderLeft: '2px solid #ffde59', paddingLeft: 10, background: 'rgba(255,222,89,0.08)', color: '#ffde59' }
                      : { borderLeft: '2px solid transparent', color: 'rgba(255,255,255,0.5)' }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'rgba(255,255,255,0.85)'
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'rgba(255,255,255,0.5)'
                  }}
                >
                  <span style={{ color: isActive ? '#ffde59' : 'rgba(255,255,255,0.35)' }}>
                    {item.icon}
                  </span>
                  <span style={{ fontWeight: isActive ? 600 : 400 }}>{item.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>

        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em', fontWeight: 600, padding: '16px 8px 8px' }}>
          HIRE
        </div>
        <ul className="space-y-1 list-none m-0 p-0">
          {hireNavItems.map((item) => {
            const isActive =
              item.href === '/hire'
                ? pathname === '/hire'
                : pathname.startsWith(item.href)
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-all duration-150 no-underline',
                  )}
                  style={
                    isActive
                      ? { borderLeft: '2px solid #ffde59', paddingLeft: 10, background: 'rgba(255,222,89,0.08)', color: '#ffde59' }
                      : { borderLeft: '2px solid transparent', color: 'rgba(255,255,255,0.5)' }
                  }
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'rgba(255,255,255,0.85)'
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.color = 'rgba(255,255,255,0.5)'
                  }}
                >
                  <span style={{ color: isActive ? '#ffde59' : 'rgba(255,255,255,0.35)' }}>
                    {item.icon}
                  </span>
                  <span style={{ fontWeight: isActive ? 600 : 400 }}>{item.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="px-5 py-4" style={{ borderTop: '1px solid #1a1a1a' }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)' }}>v0.1.0</div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)', marginTop: 2 }}>YourCompany © 2026</div>
      </div>
    </aside>
  )
}
