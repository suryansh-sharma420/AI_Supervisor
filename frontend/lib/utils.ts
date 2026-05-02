export function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.floor((now - then) / 1000)

  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function formatDuration(startStr: string, endStr: string | null): string {
  if (!endStr) return 'ongoing'
  const seconds = Math.floor((new Date(endStr).getTime() - new Date(startStr).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h === 0) return `${m}m`
  return `${h}h ${m}m`
}

export function formatCountdown(wakeAtStr: string): string {
  const now = Date.now()
  const wakeAt = new Date(wakeAtStr).getTime()
  const diff = Math.floor((wakeAt - now) / 1000)

  if (diff <= 0) return 'Overdue'
  if (diff < 3600) return `In ${Math.floor(diff / 60)}m`
  const h = Math.floor(diff / 3600)
  const m = Math.floor((diff % 3600) / 60)
  return `In ${h}h ${m}m`
}

export function truncateId(id: string): string {
  if (id.length <= 8) return id
  return `${id.slice(0, 4)}...${id.slice(-2)}`
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'running': return 'bg-green-100 text-green-800'
    case 'active': return 'bg-blue-100 text-blue-800'
    case 'sleeping': return 'bg-gray-100 text-gray-700'
    case 'paused': return 'bg-yellow-100 text-yellow-800'
    case 'completed': return 'bg-teal-100 text-teal-800'
    case 'terminated': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-700'
  }
}

export function formatTimestamp(dateStr: string): string {
  return new Date(dateStr).toLocaleString()
}

export function isToday(dateStr: string): boolean {
  const d = new Date(dateStr)
  const now = new Date()
  return d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
}
