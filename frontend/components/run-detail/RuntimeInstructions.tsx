'use client'
import { useState } from 'react'
import type { Run } from '@/lib/types'

interface Props {
  run: Run
  onAddInstruction: (instruction: string) => Promise<void>
}

export function RuntimeInstructions({ run, onAddInstruction }: Props) {
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const instructions = run.state.custom_instructions ?? []

  async function handleAdd() {
    if (!text.trim()) return
    setSaving(true)
    setError(null)
    try {
      await onAddInstruction(text.trim())
      setText('')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Runtime Instructions</div>

      {instructions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {instructions.map((instr, i) => (
            <span
              key={i}
              className="bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1 rounded-full text-xs"
            >
              {instr}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="Add custom logic instruction..."
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleAdd}
          disabled={saving || !text.trim()}
          className="px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-60 whitespace-nowrap"
        >
          {saving ? '...' : 'Add'}
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  )
}
