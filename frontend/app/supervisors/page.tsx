'use client'
import { useCallback, useEffect, useState } from 'react'
import { createSupervisor, deleteSupervisor, getSupervisors, updateSupervisor } from '@/lib/api'
import type { Supervisor, SupervisorCreate } from '@/lib/types'
import { TopBar } from '@/components/layout/TopBar'
import { SupervisorTable } from '@/components/supervisors/SupervisorTable'
import { SupervisorDrawer } from '@/components/supervisors/SupervisorDrawer'
import { useToast } from '@/components/ui/Toast'

export default function SupervisorsPage() {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<Supervisor | null>(null)
  const { toast } = useToast()

  const load = useCallback(async () => {
    try {
      setSupervisors(await getSupervisors())
    } catch (e: any) {
      toast('error', e.message)
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  async function handleSave(data: SupervisorCreate) {
    if (editing) {
      await updateSupervisor(editing.id, data)
      toast('success', 'Supervisor updated')
    } else {
      await createSupervisor(data)
      toast('success', 'Supervisor created')
    }
    setEditing(null)
    await load()
  }

  async function handleDelete(id: string) {
    try {
      await deleteSupervisor(id)
      toast('success', 'Supervisor deleted')
      await load()
    } catch (e: any) {
      toast('error', e.message)
    }
  }

  return (
    <div>
      <TopBar
        title="Supervisor Configurations"
        action={
          <button
            onClick={() => { setEditing(null); setDrawerOpen(true) }}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 font-medium"
          >
            + New Supervisor
          </button>
        }
      />
      <div className="p-6">
        <div className="bg-white border border-gray-200 rounded-lg">
          {loading ? (
            <div className="p-8 space-y-3 animate-pulse">
              {[1, 2, 3].map(i => <div key={i} className="h-10 bg-gray-100 rounded" />)}
            </div>
          ) : (
            <SupervisorTable
              supervisors={supervisors}
              onEdit={s => { setEditing(s); setDrawerOpen(true) }}
              onDelete={handleDelete}
            />
          )}
        </div>
      </div>

      <SupervisorDrawer
        open={drawerOpen}
        supervisor={editing}
        onClose={() => { setDrawerOpen(false); setEditing(null) }}
        onSave={handleSave}
      />
    </div>
  )
}
