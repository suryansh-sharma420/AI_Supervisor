'use client'
import { useState } from 'react'
import type { Run } from '@/lib/types'

interface Props { run: Run }

export function CurrentState({ run }: Props) {
  const [expanded, setExpanded] = useState(true)
  const s = run.state

  const rows: [string, string][] = [
    ['order_status', s.order_status ?? '—'],
    ['agent_summary', s.agent_summary ?? '—'],
    ['next_check_focus', s.next_check_focus ?? '—'],
    ['iteration_count', String(s.iteration_count ?? 0)],
  ]

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:bg-gray-50 rounded-lg"
      >
        Current State
        <svg className={`w-4 h-4 transition-transform ${expanded ? '' : '-rotate-90'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-5 pb-4 divide-y divide-gray-100">
          {rows.map(([k, v]) => (
            <div key={k} className="py-2 flex gap-3">
              <span className="font-mono text-xs text-gray-500 w-36 flex-shrink-0 pt-0.5">{k}</span>
              <span className="text-sm text-gray-800 line-clamp-2 flex-1">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
