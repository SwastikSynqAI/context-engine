import type { Metadata } from 'next'
import { Poppins } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'

const poppins = Poppins({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-poppins',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Context Engine',
  description: 'Data Intelligence Layer for YourCompany',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={poppins.variable}>
      <body style={{ backgroundColor: '#ffffff', color: '#0a0a0a', margin: 0, padding: 0, fontFamily: 'var(--font-poppins), sans-serif' }}>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          <Sidebar />
          <main
            style={{
              flex: 1,
              minWidth: 0,
              minHeight: '100vh',
              overflowX: 'hidden',
              overflowY: 'auto',
              backgroundColor: '#ffffff',
            }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
