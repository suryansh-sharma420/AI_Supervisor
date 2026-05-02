'use client'
import { useState } from 'react'
import type { Supervisor } from '@/lib/types'

interface Props {
  supervisors: Supervisor[]
  onEdit: (s: Supervisor) => void
  onDelete: (id: string) => Promise<void>
}

function AggressivenessBadge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    conservative: 'bg-blue-100 text-blue-700',
    normal: 'bg-gray-100 text-gray-700',
    aggressive: 'bg-orange-100 text-orange-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[value] ?? 'bg-gray-100 text-gray-700'}`}>
      {value}
    </span>
  )
}

export function SupervisorTable({ supervisors, onEdit, onDelete }: Props) {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  async function handleDelete(id: string) {
    if (confirmDelete !== id) {
      setConfirmDelete(id)
      return
    }
    setDeleting(id)
    await onDelete(id)
    setDeleting(null)
    setConfirmDelete(null)
  }

  if (supervisors.length === 0) {
    return (
      <div className="text-center py-20">
        <svg className="w-12 h-12 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        <p className="text-gray-500 font-medium">No supervisors configured</p>
        <p className="text-gray-400 text-sm mt-1">Create your first supervisor to get started</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
            <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Base Instruction</th>
            <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Wake Aggressiveness</th>
            <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {supervisors.map(s => (
            <tr key={s.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
              <td className="px-4 py-3 text-gray-600 max-w-xs">
                {s.base_instruction.length > 60
                  ? s.base_instruction.slice(0, 60) + '...'
                  : s.base_instruction}
              </td>
              <td className="px-4 py-3">
                <AggressivenessBadge value={s.wake_aggressiveness} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onEdit(s)}
                    className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                    title="Edit"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    disabled={deleting === s.id}
                    className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                      confirmDelete === s.id
                        ? 'bg-red-600 text-white hover:bg-red-700'
                        : 'text-gray-500 hover:text-red-600 hover:bg-red-50'
                    }`}
                  >
                    {deleting === s.id ? '...' : confirmDelete === s.id ? 'Confirm?' : (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                  </button>
                  {confirmDelete === s.id && (
                    <button
                      onClick={() => setConfirmDelete(null)}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Cancel
                    </button>
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
