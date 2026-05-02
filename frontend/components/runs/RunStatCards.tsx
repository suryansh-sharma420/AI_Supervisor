import type { Run } from '@/lib/types'
import { isToday } from '@/lib/utils'

interface Props {
  runs: Run[]
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-5 py-4">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">{label}</div>
      <div className={`text-3xl font-bold ${color}`}>{value}</div>
    </div>
  )
}

export function RunStatCards({ runs }: Props) {
  const active = runs.filter(r => r.status === 'active').length
  const sleeping = runs.filter(r => r.status === 'sleeping').length
  const completedToday = runs.filter(r => r.status === 'completed' && r.completed_at && isToday(r.completed_at)).length
  const terminated = runs.filter(r => r.status === 'terminated').length

  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCard label="Total Active Runs" value={active} color="text-blue-600" />
      <StatCard label="Total Sleeping" value={sleeping} color="text-gray-600" />
      <StatCard label="Completed Today" value={completedToday} color="text-teal-600" />
      <StatCard label="Total Terminated" value={terminated} color="text-red-600" />
    </div>
  )
}
