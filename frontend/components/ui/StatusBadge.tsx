import { getStatusColor } from '@/lib/utils'

interface Props {
  status: string
  large?: boolean
}

export function StatusBadge({ status, large = false }: Props) {
  const base = large
    ? 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold'
    : 'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium'

  return (
    <span className={`${base} ${getStatusColor(status)}`}>
      {status === 'running' && (
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
      )}
      {status}
    </span>
  )
}
