'use client'
import { useEffect, useState } from 'react'
import type { RunCreate, Supervisor } from '@/lib/types'

interface Props {
  open: boolean
  supervisors: Supervisor[]
  onClose: () => void
  onStart: (data: RunCreate, initialInstruction?: string) => Promise<void>
}

export function StartRunDrawer({ open, supervisors, onClose, onStart }: Props) {
  const [supervisorId, setSupervisorId] = useState('')
  const [orderId, setOrderId] = useState('')
  const [maxAge, setMaxAge] = useState(168)
  const [initialInstruction, setInitialInstruction] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setSupervisorId(supervisors[0]?.id ?? '')
      setOrderId('')
      setMaxAge(168)
      setInitialInstruction('')
      setError(null)
    }
  }, [open, supervisors])

  async function handleStart() {
    if (!supervisorId || !orderId.trim()) {
      setError('Supervisor and Order ID are required.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onStart(
        { supervisor_id: supervisorId, order_id: orderId.trim(), max_run_age_hours: maxAge },
        initialInstruction.trim() || undefined,
      )
      onClose()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-[480px] bg-white shadow-2xl flex flex-col">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Start New Run</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Supervisor <span className="text-red-500">*</span></label>
            <select
              value={supervisorId}
              onChange={e => setSupervisorId(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {supervisors.length === 0
                ? <option value="">No supervisors — create one first</option>
                : supervisors.map(s => <option key={s.id} value={s.id}>{s.name}</option>)
              }
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Order ID <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={orderId}
              onChange={e => setOrderId(e.target.value)}
              placeholder="ORD-2024-001"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Run Age (hours)</label>
            <input
              type="number"
              value={maxAge}
              onChange={e => setMaxAge(Number(e.target.value))}
              min={1}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Initial Instruction (optional)</label>
            <textarea
              rows={3}
              value={initialInstruction}
              onChange={e => setInitialInstruction(e.target.value)}
              placeholder="e.g. This is a VIP customer, prioritize communication"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2 text-sm text-red-700">{error}</div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button
            onClick={handleStart}
            disabled={saving || supervisors.length === 0}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
          >
            {saving && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
            Start Run
          </button>
        </div>
      </div>
    </div>
  )
}
