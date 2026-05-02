'use client'
import { use, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  addInstruction as apiAddInstruction,
  getSupervisor,
  interruptRun,
  resumeRun,
  sendEvent,
  terminateRun,
  triggerRun,
  wakeRun,
} from '@/lib/api'
import type { Supervisor } from '@/lib/types'
import { useRun } from '@/hooks/useRun'
import { useActivities } from '@/hooks/useActivities'
import { TopBar } from '@/components/layout/TopBar'
import { RunOverview } from '@/components/run-detail/RunOverview'
import { CurrentState } from '@/components/run-detail/CurrentState'
import { RuntimeInstructions } from '@/components/run-detail/RuntimeInstructions'
import { ExecutiveControls } from '@/components/run-detail/ExecutiveControls'
import { ActivityFeed } from '@/components/run-detail/ActivityFeed'
import { EventInjector } from '@/components/run-detail/EventInjector'
import { FinalSummary } from '@/components/run-detail/FinalSummary'
import { useToast } from '@/components/ui/Toast'

export default function RunDetailPage({ params }: { params: Promise<{ run_id: string }> }) {
  const { run_id } = use(params)
  const router = useRouter()
  const { toast } = useToast()

  const { run, loading: runLoading, error: runError, refresh: refreshRun } = useRun(run_id)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const { activities, loading: actLoading, refresh: refreshActivities } = useActivities(run_id, autoRefresh)
  const [supervisor, setSupervisor] = useState<Supervisor | null>(null)

  useEffect(() => {
    if (run?.supervisor_id) {
      getSupervisor(run.supervisor_id).then(setSupervisor).catch(() => {})
    }
  }, [run?.supervisor_id])

  function refreshAll() {
    refreshRun()
    refreshActivities()
  }

  async function wrap(fn: () => Promise<any>, successMsg: string) {
    try {
      await fn()
      toast('success', successMsg)
      refreshAll()
    } catch (e: any) {
      toast('error', e.message)
    }
  }

  if (runLoading) return (
    <div>
      <TopBar title="Run Detail" />
      <div className="p-6 animate-pulse space-y-4">
        <div className="h-32 bg-gray-200 rounded-lg" />
        <div className="h-24 bg-gray-200 rounded-lg" />
      </div>
    </div>
  )

  if (runError || !run) return (
    <div>
      <TopBar title="Run Not Found" />
      <div className="p-6 text-center">
        <p className="text-gray-500 mb-4">Run not found or could not be loaded.</p>
        <button onClick={() => router.push('/runs')} className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">
          Back to Runs
        </button>
      </div>
    </div>
  )

  return (
    <div>
      <TopBar
        title={`Run — ${run.order_id}`}
        action={
          <button onClick={() => router.push('/runs')} className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            All Runs
          </button>
        }
      />

      <div className="p-6 flex gap-5 items-start">
        {/* LEFT: 40% */}
        <div className="w-[40%] flex flex-col gap-4 flex-shrink-0">
          <RunOverview run={run} supervisor={supervisor} />
          <CurrentState run={run} />
          <RuntimeInstructions
            run={run}
            onAddInstruction={async (instr) => {
              await apiAddInstruction(run_id, instr)
              toast('success', 'Instruction added')
              refreshRun()
            }}
          />
          <ExecutiveControls
            run={run}
            onTrigger={() => wrap(() => triggerRun(run_id), 'Agent triggered')}
            onWake={() => wrap(() => wakeRun(run_id), 'Run woken')}
            onInterrupt={() => wrap(() => interruptRun(run_id), 'Run paused')}
            onResume={() => wrap(() => resumeRun(run_id), 'Run resumed')}
            onTerminate={() => wrap(() => terminateRun(run_id), 'Run terminated')}
          />
        </div>

        {/* RIGHT: 60% */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          {run.final_summary && (
            <FinalSummary run={run} activities={activities} />
          )}
          <ActivityFeed
            activities={activities}
            loading={actLoading}
            autoRefresh={autoRefresh}
            onToggleAutoRefresh={() => setAutoRefresh(v => !v)}
          />
          <EventInjector
            onSendEvent={async (eventType, data) => {
              await sendEvent(run_id, eventType, data)
              toast('success', `Event "${eventType}" sent`)
              refreshAll()
            }}
          />
        </div>
      </div>
    </div>
  )
}
