'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { getActivities } from '@/lib/api'
import type { Activity } from '@/lib/types'

export function useActivities(run_id: string, autoRefresh: boolean) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getActivities(run_id)
      setActivities(data)
      setError(null)
    } catch (e: any) {
      setError(e.message)
    }
  }, [run_id])

  useEffect(() => {
    setLoading(true)
    refresh().finally(() => setLoading(false))
  }, [refresh])

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (autoRefresh) {
      intervalRef.current = setInterval(refresh, 10000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [autoRefresh, refresh])

  return { activities, loading, error, refresh }
}
