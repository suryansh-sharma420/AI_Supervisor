'use client'
import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  addInstruction, createRun, getRuns, getSupervisors,
  terminateRun, triggerRun, wakeRun,
} from '@/lib/api'
import type { Run, RunCreate, Supervisor } from '@/lib/types'
import { TopBar } from '@/components/layout/TopBar'
import { RunStatCards } from '@/components/runs/RunStatCards'
import { RunsTable } from '@/components/runs/RunsTable'
import { StartRunDrawer } from '@/components/runs/StartRunDrawer'
import { useToast } from '@/components/ui/Toast'

const STATUS_FILTERS = ['All', 'active', 'sleeping', 'running', 'paused', 'completed', 'terminated']

export default function RunsPage() {
  const router = useRouter()
  const [allRuns, setAllRuns] = useState<Run[]>([])
  const [supervisors, setSupervisors] = useState<Supervisor[]>([])
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { toast } = useToast()

  const load = useCallback(async () => {
    try {
      const [runs, sups] = await Promise.all([getRuns(), getSupervisors()])
      setAllRuns(runs)
      setSupervisors(sups)
    } catch (e: any) {
      toast('error', e.message)
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  const displayed = filter === 'All' ? allRuns : allRuns.filter(r => r.status === filter)

  async function handleStart(data: RunCreate, initialInstruction?: string) {
    const run = await createRun(data)
    toast('success', `Run started for ${data.order_id}`)
    if (initialInstruction) {
      await addInstruction(run.id, initialInstruction)
    }
    await load()
    router.push(`/runs/${run.id}`)
  }

  async function handleTrigger(id: string) {
    try {
      await triggerRun(id)
      toast('success', 'Agent triggered')
      await load()
    } catch (e: any) { toast('error', e.message) }
  }

  async function handleWake(id: string) {
    try {
      await wakeRun(id)
      toast('success', 'Run woken')
      await load()
    } catch (e: any) { toast('error', e.message) }
  }

  async function handleTerminate(id: string) {
    try {
      await terminateRun(id)
      toast('success', 'Run terminated')
      await load()
    } catch (e: any) { toast('error', e.message) }
  }

  return (
    <div>
      <TopBar
        title="Runs"
        action={
          <button
            onClick={() => setDrawerOpen(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 font-medium"
          >
            + Start Run
          </button>
        }
      />
      <div className="p-6 space-y-5">
        <RunStatCards runs={allRuns} />

        {/* Status filter tabs */}
        <div className="flex gap-1 border-b border-gray-200">
          {STATUS_FILTERS.map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
                filter === s
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg">
          {loading ? (
            <div className="p-8 space-y-3 animate-pulse">
              {[1, 2, 3].map(i => <div key={i} className="h-10 bg-gray-100 rounded" />)}
            </div>
          ) : (
            <RunsTable
              runs={displayed}
              supervisors={supervisors}
              onTrigger={handleTrigger}
              onWake={handleWake}
              onTerminate={handleTerminate}
            />
          )}
        </div>
      </div>

      <StartRunDrawer
        open={drawerOpen}
        supervisors={supervisors}
        onClose={() => setDrawerOpen(false)}
        onStart={handleStart}
      />
    </div>
  )
}
