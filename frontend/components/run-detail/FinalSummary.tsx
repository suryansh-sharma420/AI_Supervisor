import ReactMarkdown from 'react-markdown'
import type { Activity, Run } from '@/lib/types'
import { formatDuration, formatTimestamp } from '@/lib/utils'

interface Props {
  run: Run
  activities: Activity[]
}

export function FinalSummary({ run, activities }: Props) {
  if (!run.final_summary) return null

  const finalOutput = [...activities].reverse().find(a => a.activity_type === 'final_output')
  const actionCount = activities.filter(a => a.activity_type === 'agent_action').length

  return (
    <div className="bg-white border-l-4 border-teal-500 border border-gray-200 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-teal-600 text-lg">✓</span>
        <h3 className="font-semibold text-gray-900">Run Complete — Final Summary</h3>
      </div>

      <div className="space-y-3 text-sm">
        {finalOutput && (
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Completion Reason</span>
            <p className="text-gray-700 mt-0.5">{finalOutput.payload.completion_reason ?? '—'}</p>
          </div>
        )}

        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Outcome</span>
          <div className="mt-1 text-gray-700 leading-relaxed bg-gray-50 rounded-md p-4 text-sm markdown-content">
            <ReactMarkdown>{run.final_summary}</ReactMarkdown>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 pt-2 border-t border-gray-100">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Completed At</span>
            <p className="text-gray-700 mt-0.5">{run.completed_at ? formatTimestamp(run.completed_at) : '—'}</p>
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Total Duration</span>
            <p className="text-gray-700 mt-0.5">{formatDuration(run.started_at, run.completed_at)}</p>
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Total Actions</span>
            <p className="text-gray-700 mt-0.5">{actionCount}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
