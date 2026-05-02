import type { Run, Supervisor } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatCountdown, formatDuration, formatRelativeTime, formatTimestamp } from '@/lib/utils'

interface Props {
  run: Run
  supervisor: Supervisor | null
}

export function RunOverview({ run, supervisor }: Props) {
  const finished = run.status === 'completed' || run.status === 'terminated'

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Order Reference</div>
      <div className="text-2xl font-bold text-gray-900 font-mono mb-2">{run.order_id}</div>
      <div className="mb-4"><StatusBadge status={run.status} large /></div>

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600 mb-4">
        <span><span className="text-gray-400">Supervisor:</span> {supervisor?.name ?? run.supervisor_id.slice(0, 8)}</span>
        <span><span className="text-gray-400">Started:</span> {formatRelativeTime(run.started_at)}</span>
      </div>

      {run.status === 'sleeping' && run.wake_at && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 flex items-start gap-3">
          <span className="text-xl">🌙</span>
          <div>
            <div className="font-semibold text-blue-800 text-sm">Sleeping — wakes {formatCountdown(run.wake_at)}</div>
            <div className="text-xs text-blue-600 mt-0.5">{formatTimestamp(run.wake_at)}</div>
          </div>
        </div>
      )}

      {finished && (
        <div className={`rounded-lg px-4 py-3 text-sm ${run.status === 'completed' ? 'bg-teal-50 border border-teal-200 text-teal-800' : 'bg-red-50 border border-red-200 text-red-800'}`}>
          <div className="font-semibold capitalize">{run.status}</div>
          {run.completed_at && (
            <div className="text-xs mt-0.5 opacity-80">
              {formatTimestamp(run.completed_at)} · Duration: {formatDuration(run.started_at, run.completed_at)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
