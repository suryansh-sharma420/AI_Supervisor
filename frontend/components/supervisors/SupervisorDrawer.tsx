'use client'
import { useEffect, useState } from 'react'
import type { Supervisor, SupervisorCreate } from '@/lib/types'

const ALL_ACTIONS = [
  'message_fulfillment_team',
  'message_payments_team',
  'message_logistics_team',
  'message_customer',
  'create_internal_note',
]

interface Props {
  open: boolean
  supervisor?: Supervisor | null
  onClose: () => void
  onSave: (data: SupervisorCreate) => Promise<void>
}

export function SupervisorDrawer({ open, supervisor, onClose, onSave }: Props) {
  const [name, setName] = useState('')
  const [baseInstruction, setBaseInstruction] = useState('')
  const [actions, setActions] = useState<string[]>([...ALL_ACTIONS])
  const [aggressiveness, setAggressiveness] = useState<'conservative' | 'normal' | 'aggressive'>('normal')
  const [sleepMinutes, setSleepMinutes] = useState(60)
  const [model, setModel] = useState('llama-3.3-70b-versatile')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (supervisor) {
      setName(supervisor.name)
      setBaseInstruction(supervisor.base_instruction)
      setActions(supervisor.available_actions)
      setAggressiveness(supervisor.wake_aggressiveness)
      setSleepMinutes(supervisor.wake_up_behavior?.default_sleep_minutes ?? 60)
      setModel(supervisor.llm_settings?.model ?? 'llama-3.3-70b-versatile')
    } else {
      setName('')
      setBaseInstruction('')
      setActions([...ALL_ACTIONS])
      setAggressiveness('normal')
      setSleepMinutes(60)
      setModel('llama-3.3-70b-versatile')
    }
    setError(null)
  }, [supervisor, open])

  function toggleAction(a: string) {
    setActions(prev => prev.includes(a) ? prev.filter(x => x !== a) : [...prev, a])
  }

  async function handleSave() {
    if (!name.trim() || !baseInstruction.trim()) {
      setError('Name and Base Instruction are required.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSave({
        name: name.trim(),
        base_instruction: baseInstruction.trim(),
        available_actions: actions,
        wake_aggressiveness: aggressiveness,
        wake_up_behavior: { default_sleep_minutes: sleepMinutes },
        llm_settings: { model },
      })
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
          <h2 className="text-lg font-semibold text-gray-900">
            {supervisor ? 'Edit Supervisor' : 'New Supervisor'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name <span className="text-red-500">*</span></label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Standard Order Supervisor"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base Instruction <span className="text-red-500">*</span></label>
            <textarea
              rows={6}
              value={baseInstruction}
              onChange={e => setBaseInstruction(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Describe how this supervisor should behave..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Available Actions</label>
            <div className="space-y-2">
              {ALL_ACTIONS.map(a => (
                <label key={a} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={actions.includes(a)}
                    onChange={() => toggleAction(a)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 font-mono">{a}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Wake Aggressiveness</label>
            <div className="flex rounded-md border border-gray-300 overflow-hidden">
              {(['conservative', 'normal', 'aggressive'] as const).map(v => (
                <button
                  key={v}
                  onClick={() => setAggressiveness(v)}
                  className={`flex-1 py-2 text-sm font-medium transition-colors capitalize
                    ${aggressiveness === v ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default Sleep Duration (minutes)</label>
            <input
              type="number"
              value={sleepMinutes}
              onChange={e => setSleepMinutes(Number(e.target.value))}
              min={1}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
            <input
              type="text"
              value={model}
              onChange={e => setModel(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
          >
            {saving && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
            Save Supervisor
          </button>
        </div>
      </div>
    </div>
  )
}
