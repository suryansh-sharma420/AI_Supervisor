'use client'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import type { Run, Supervisor } from '@/lib/types'
import { formatCountdown, formatRelativeTime, truncateId } from '@/lib/utils'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface Props {
  runs: Run[]
  supervisors: Supervisor[]
  onTrigger: (id: string) => Promise<void>
  onWake: (id: string) => Promise<void>
  onTerminate: (id: string) => Promise<void>
}

export function RunsTable({ runs, supervisors, onTrigger, onWake, onTerminate }: Props) {
  const router = useRouter()
  const [confirmTerminate, setConfirmTerminate] = useState<string | null>(null)
  const [loading, setLoading] = useState<string | null>(null)

  const supMap = Object.fromEntries(supervisors.map(s => [s.id, s.name]))

  async function action(id: string, fn: (id: string) => Promise<void>) {
    setLoading(id)
    try { await fn(id) } finally { setLoading(null) }
  }

  if (runs.length === 0) {
    return (
      <div className="text-center py-16">
        <svg className="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p className="text-gray-500">No runs found</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            {['Run ID', 'Order ID', 'Supervisor', 'Status', 'Started', 'Wake At', 'Actions'].map(h => (
              <th key={h} className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {runs.map(run => (
            <tr key={run.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <button
                  onClick={() => router.push(`/runs/${run.id}`)}
                  className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline"
                >
                  {truncateId(run.id)}
                </button>
              </td>
              <td className="px-4 py-3 font-medium text-gray-900">{run.order_id}</td>
              <td className="px-4 py-3 text-gray-600 text-xs">{supMap[run.supervisor_id] ?? run.supervisor_id.slice(0, 8)}</td>
              <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
              <td className="px-4 py-3 text-gray-500">{formatRelativeTime(run.started_at)}</td>
              <td className="px-4 py-3 text-gray-500">
                {run.status === 'sleeping' && run.wake_at ? (
                  <span className="text-blue-600">{formatCountdown(run.wake_at)}</span>
                ) : '—'}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1">
                  {/* View */}
                  <button
                    onClick={() => router.push(`/runs/${run.id}`)}
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                    title="View"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                  {/* Trigger */}
                  {(run.status === 'active' || run.status === 'sleeping') && (
                    <button
                      onClick={() => action(run.id, onTrigger)}
                      disabled={loading === run.id}
                      className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded"
                      title="Trigger Agent"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                  )}
                  {/* Wake */}
                  {run.status === 'sleeping' && (
                    <button
                      onClick={() => action(run.id, onWake)}
                      disabled={loading === run.id}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      title="Wake Run"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                      </svg>
                    </button>
                  )}
                  {/* Terminate */}
                  {!['completed', 'terminated'].includes(run.status) && (
                    confirmTerminate === run.id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { action(run.id, onTerminate); setConfirmTerminate(null) }}
                          className="px-2 py-0.5 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                        >Confirm</button>
                        <button onClick={() => setConfirmTerminate(null)} className="text-xs text-gray-500 hover:text-gray-700">✕</button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmTerminate(run.id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                        title="Terminate"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                        </svg>
                      </button>
                    )
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
