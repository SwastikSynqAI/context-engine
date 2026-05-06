'use client'
import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { isLoggedIn } from '@/lib/hire-api'

export default function HireLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  useEffect(() => {
    if (!isLoggedIn() && pathname !== '/hire/login') {
      router.replace('/hire/login')
    }
  }, [router, pathname])
  return <>{children}</>
}
