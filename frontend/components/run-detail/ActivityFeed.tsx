'use client'
import ReactMarkdown from 'react-markdown'
import type { Activity } from '@/lib/types'
import { formatRelativeTime } from '@/lib/utils'

interface Props {
  activities: Activity[]
  loading: boolean
  autoRefresh: boolean
  onToggleAutoRefresh: () => void
}

function ActivityIcon({ type, payload }: { type: string; payload: any }) {
  const base = 'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0'

  switch (type) {
    case 'event_received':
      return <div className={`${base} bg-gray-100`}>
        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
    case 'wake_decision':
      return <div className={`${base} ${payload.decision === 'wake' ? 'bg-blue-100' : 'bg-gray-100'}`}>
        <svg className={`w-4 h-4 ${payload.decision === 'wake' ? 'text-blue-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      </div>
    case 'agent_action':
      return <div className={`${base} bg-purple-100`}>
        <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>
    case 'sleep_decision':
      return <div className={`${base} bg-gray-100`}><span className="text-base">🌙</span></div>
    case 'manual_instruction':
      return <div className={`${base} bg-orange-100`}>
        <svg className="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
      </div>
    case 'final_output':
      return <div className={`${base} bg-teal-100`}>
        <svg className="w-4 h-4 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6H8L7 11H6m0 10H3m0 0h3" />
        </svg>
      </div>
    default:
      return <div className={`${base} bg-gray-100`}>
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
  }
}

function ActivityContent({ activity }: { activity: Activity }) {
  const { activity_type, payload } = activity

  switch (activity_type) {
    case 'event_received':
      return (
        <div>
          <span className="text-sm text-gray-700">Event: <strong>{payload.event_type}</strong></span>
          {payload.data && Object.keys(payload.data).length > 0 && (
            <pre className="mt-1 bg-gray-900 text-green-400 text-xs rounded p-2 overflow-x-auto">
              {JSON.stringify(payload.data, null, 2)}
            </pre>
          )}
        </div>
      )
    case 'wake_decision':
      return (
        <div className="text-sm">
          <span className="text-gray-700">Wake: </span>
          <strong className={payload.decision === 'wake' ? 'text-green-600' : 'text-gray-500'}>
            {payload.decision === 'wake' ? 'Yes' : 'No'}
          </strong>
          {payload.reason && <p className="text-gray-600 mt-0.5">Reason: {payload.reason}</p>}
          {payload.classifier_layer && (
            <span className="inline-block mt-1 bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">
              via {payload.classifier_layer} layer
            </span>
          )}
        </div>
      )
    case 'agent_action':
      return (
        <div className="text-sm">
          <strong className="text-blue-700 font-mono">{payload.action}</strong>
          {(payload.parameters?.message || payload.parameters?.note) && (
            <div className="text-gray-700 mt-1 markdown-content prose-sm">
              <ReactMarkdown>{payload.parameters?.message || payload.parameters?.note}</ReactMarkdown>
            </div>
          )}
          {payload.reasoning && (
            <div className="text-gray-400 italic text-xs mt-1 border-t border-gray-50 pt-1">
              <ReactMarkdown>{payload.reasoning}</ReactMarkdown>
            </div>
          )}
        </div>
      )
    case 'sleep_decision':
      return (
        <div className="text-sm text-gray-700">
          <p>Sleeping for <strong>{payload.duration_minutes} minutes</strong></p>
          {payload.reason && <p className="text-gray-500 mt-0.5">Reason: {payload.reason}</p>}
          {payload.next_check_focus && (
            <p className="text-gray-500 mt-0.5">Watching for: {payload.next_check_focus}</p>
          )}
        </div>
      )
    case 'manual_instruction':
      return <p className="text-sm text-gray-700">{payload.instruction}</p>
    case 'final_output':
      return (
        <div className="bg-teal-50 border border-teal-200 rounded-md p-3 w-full">
          <div className="font-semibold text-teal-800 mb-1">✓ Run Complete</div>
          <div className="text-xs text-teal-700 markdown-content">
            <ReactMarkdown>{payload.summary}</ReactMarkdown>
          </div>
        </div>
      )
    default:
      return (
        <p className="text-sm text-gray-700">
          {payload.event ?? activity_type}
          {payload.reason ? ` — ${payload.reason}` : ''}
        </p>
      )
  }
}

export function ActivityFeed({ activities, loading, autoRefresh, onToggleAutoRefresh }: Props) {
  const reversed = [...activities].reverse()

  return (
    <div className="bg-white border border-gray-200 rounded-lg flex flex-col">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900 text-sm">Activity Log</h3>
          <span className="flex items-center gap-1 bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            LIVE
          </span>
        </div>
        <button
          onClick={onToggleAutoRefresh}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            autoRefresh
              ? 'bg-blue-600 text-white border-blue-600'
              : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto max-h-[600px] divide-y divide-gray-100">
        {loading && activities.length === 0 ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="flex gap-3 animate-pulse">
                <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-gray-200 rounded w-1/3" />
                  <div className="h-3 bg-gray-200 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : reversed.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">No activity yet</div>
        ) : (
          reversed.map(activity => (
            <div key={activity.id} className="flex gap-3 px-5 py-3 hover:bg-gray-50">
              <ActivityIcon type={activity.activity_type} payload={activity.payload} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                    {activity.activity_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                    {formatRelativeTime(activity.created_at)}
                  </span>
                </div>
                <ActivityContent activity={activity} />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
