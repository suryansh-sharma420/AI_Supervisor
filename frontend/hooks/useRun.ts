'use client'
import { useCallback, useEffect, useState } from 'react'
import { getRun } from '@/lib/api'
import type { Run } from '@/lib/types'

export function useRun(run_id: string, autoRefresh = true) {
  const [run, setRun] = useState<Run | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getRun(run_id)
      setRun(data)
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
    if (!autoRefresh) return
    const interval = setInterval(refresh, 10000)
    return () => clearInterval(interval)
  }, [run_id, autoRefresh, refresh])

  return { run, loading, error, refresh }
}
