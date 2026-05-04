'use client'
import { useState } from 'react'

type FieldDef = { key: string; label: string; placeholder?: string; type?: 'number' }

type EventConfig = {
  label: string
  fields: FieldDef[]
}

const EVENT_CONFIGS: Record<string, EventConfig> = {
  order_created: {
    label: 'Order Created',
    fields: [],
  },
  payment_confirmed: {
    label: 'Payment Confirmed',
    fields: [
      { key: 'amount', label: 'Amount', placeholder: 'e.g. 149.99', type: 'number' },
    ],
  },
  payment_failed: {
    label: 'Payment Failed',
    fields: [
      { key: 'reason', label: 'Reason', placeholder: 'e.g. insufficient_funds' },
      { key: 'amount', label: 'Amount', placeholder: 'e.g. 149.99', type: 'number' },
    ],
  },
  shipment_created: {
    label: 'Shipment Created',
    fields: [
      { key: 'tracking_number', label: 'Tracking Number', placeholder: 'e.g. 1Z999AA10123456784' },
      { key: 'carrier', label: 'Carrier', placeholder: 'e.g. UPS' },
    ],
  },
  shipment_delayed: {
    label: 'Shipment Delayed',
    fields: [
      { key: 'reason', label: 'Reason', placeholder: 'e.g. truck breakdown' },
      { key: 'hours', label: 'Hours', placeholder: 'e.g. 48', type: 'number' },
    ],
  },
  delivered: {
    label: 'Delivered',
    fields: [],
  },
  refund_requested: {
    label: 'Refund Requested',
    fields: [
      { key: 'reason', label: 'Reason', placeholder: 'e.g. item damaged' },
      { key: 'amount', label: 'Amount', placeholder: 'e.g. 149.99', type: 'number' },
    ],
  },
  customer_message_received: {
    label: 'Customer Message Received',
    fields: [
      { key: 'message', label: 'Message', placeholder: 'e.g. Where is my order?' },
    ],
  },
  no_update_for_n_hours: {
    label: 'No Update For N Hours',
    fields: [
      { key: 'hours', label: 'Hours', placeholder: 'e.g. 48', type: 'number' },
    ],
  },
}

const EVENT_TYPES = Object.keys(EVENT_CONFIGS)

interface Props {
  onSendEvent: (eventType: string, data: any) => Promise<void>
}

function buildData(fields: FieldDef[], values: Record<string, string>): Record<string, any> {
  const data: Record<string, any> = {}
  for (const field of fields) {
    const raw = values[field.key] ?? ''
    if (raw !== '') {
      data[field.key] = field.type === 'number' ? Number(raw) : raw
    }
  }
  return data
}

export function EventInjector({ onSendEvent }: Props) {
  const [eventType, setEventType] = useState(EVENT_TYPES[0])
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const config = EVENT_CONFIGS[eventType]
  const previewData = buildData(config.fields, fieldValues)
  const previewJson = JSON.stringify(previewData, null, 2)

  function handleTypeChange(type: string) {
    setEventType(type)
    setFieldValues({})
    setError(null)
  }

  function setField(key: string, value: string) {
    setFieldValues(prev => ({ ...prev, [key]: value }))
  }

  async function handleSend() {
    setSending(true)
    setError(null)
    try {
      await onSendEvent(eventType, previewData)
      setFieldValues({})
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Inject Manual Event</div>

      {/* Event type selector */}
      <div className="mb-3">
        <label className="block text-xs text-gray-500 mb-1">Event Type</label>
        <select
          value={eventType}
          onChange={e => handleTypeChange(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {EVENT_TYPES.map(t => (
            <option key={t} value={t}>{EVENT_CONFIGS[t].label}</option>
          ))}
        </select>
      </div>

      {/* Structured fields */}
      {config.fields.map(field => (
        <div key={field.key} className="mb-3">
          <label className="block text-xs text-gray-500 mb-1">{field.label}</label>
          <input
            type={field.type === 'number' ? 'number' : 'text'}
            value={fieldValues[field.key] ?? ''}
            onChange={e => setField(field.key, e.target.value)}
            placeholder={field.placeholder}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      ))}

      {/* Live JSON preview */}
      <div className="mb-3">
        <label className="block text-xs text-gray-500 mb-1">Preview</label>
        <pre className="bg-gray-50 border border-gray-200 rounded-md px-3 py-2 text-xs font-mono text-gray-700 whitespace-pre-wrap break-all">
          {previewJson}
        </pre>
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
      <p className="text-xs text-gray-400 mt-2">Simulates a real order event being received</p>
    </div>
  )
}
