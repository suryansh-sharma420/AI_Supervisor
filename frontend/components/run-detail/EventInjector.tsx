'use client'
import { useState } from 'react'

const EVENT_TYPES = [
  'order_created',
  'payment_confirmed',
  'payment_failed',
  'shipment_created',
  'shipment_delayed',
  'delivered',
  'refund_requested',
  'customer_message_received',
  'no_update_for_n_hours',
]

interface Props {
  onSendEvent: (eventType: string, data: any) => Promise<void>
}

export function EventInjector({ onSendEvent }: Props) {
  const [eventType, setEventType] = useState(EVENT_TYPES[0])
  const [dataStr, setDataStr] = useState('{}')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSend() {
    let parsed: any
    try {
      parsed = JSON.parse(dataStr)
    } catch {
      setError('Invalid JSON in data field')
      return
    }
    setSending(true)
    setError(null)
    try {
      await onSendEvent(eventType, parsed)
      setDataStr('{}')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Inject Manual Event</div>

      <div className="flex gap-2 mb-2">
        <select
          value={eventType}
          onChange={e => setEventType(e.target.value)}
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input
          type="text"
          value={dataStr}
          onChange={e => setDataStr(e.target.value)}
          placeholder='{"key": "value"}'
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <button
        onClick={handleSend}
        disabled={sending}
        className="w-full py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-md disabled:opacity-60 flex items-center justify-center gap-2 transition-colors"
      >
        {sending
          ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          : '▶'
        }
        Send Event
      </button>

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      <p className="text-xs text-gray-400 mt-2">This simulates a real order event being received</p>
    </div>
  )
}
