'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { getHealth } from '@/lib/api'

function IconSupervisors() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  )
}

function IconRuns() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    getHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false))
  }, [])

  const navItems = [
    { href: '/supervisors', label: 'Supervisors', icon: <IconSupervisors /> },
    { href: '/runs', label: 'Runs', icon: <IconRuns /> },
  ]

  return (
    <aside className="w-[220px] min-h-screen bg-slate-900 flex flex-col fixed left-0 top-0 z-40">
      <div className="px-5 pt-6 pb-4 border-b border-slate-800">
        <div className="text-white font-bold text-base leading-tight">Order Supervisor</div>
        <div className="text-slate-500 text-xs uppercase tracking-widest mt-1">Mission Control</div>
      </div>

      <nav className="flex-1 py-4">
        {navItems.map(item => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-5 py-2.5 text-sm transition-colors relative
                ${active
                  ? 'text-white bg-slate-800 border-l-2 border-blue-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800 border-l-2 border-transparent'
                }`}
            >
              {item.icon}
              {item.label}
            </Link>
          )
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
            apiOnline === null ? 'bg-slate-500' :
            apiOnline ? 'bg-green-400' : 'bg-red-500'
          }`} />
          <span className="text-xs text-slate-400 uppercase tracking-wider">
            API STATUS: {apiOnline === null ? 'CHECKING' : apiOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </aside>
  )
}
