import type { Activity, Run, RunCreate, Supervisor, SupervisorCreate } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const err = await res.json()
      message = err.detail || err.message || message
    } catch {}
    throw new Error(message)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// --- Supervisors ---
export const getSupervisors = (): Promise<Supervisor[]> =>
  request('/api/supervisors')

export const getSupervisor = (id: string): Promise<Supervisor> =>
  request(`/api/supervisors/${id}`)

export const createSupervisor = (data: SupervisorCreate): Promise<Supervisor> =>
  request('/api/supervisors', { method: 'POST', body: JSON.stringify(data) })

export const updateSupervisor = (id: string, data: Partial<SupervisorCreate>): Promise<Supervisor> =>
  request(`/api/supervisors/${id}`, { method: 'PATCH', body: JSON.stringify(data) })

export const deleteSupervisor = (id: string): Promise<void> =>
  request(`/api/supervisors/${id}`, { method: 'DELETE' })

// --- Runs ---
export const getRuns = (params?: { status?: string; supervisor_id?: string }): Promise<Run[]> => {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.supervisor_id) qs.set('supervisor_id', params.supervisor_id)
  const query = qs.toString()
  return request(`/api/runs${query ? `?${query}` : ''}`)
}

export const getRun = (id: string): Promise<Run> => request(`/api/runs/${id}`)

export const createRun = (data: RunCreate): Promise<Run> =>
  request('/api/runs', { method: 'POST', body: JSON.stringify(data) })

export const getActivities = (run_id: string): Promise<Activity[]> =>
  request(`/api/runs/${run_id}/activities`)

// --- Run control ---
export const triggerRun = (run_id: string): Promise<any> =>
  request(`/api/runs/${run_id}/trigger`, { method: 'POST' })

export const wakeRun = (run_id: string): Promise<Run> =>
  request(`/api/runs/${run_id}/wake`, { method: 'POST' })

export const interruptRun = (run_id: string): Promise<Run> =>
  request(`/api/runs/${run_id}/interrupt`, { method: 'POST' })

export const resumeRun = (run_id: string): Promise<Run> =>
  request(`/api/runs/${run_id}/resume`, { method: 'POST' })

export const terminateRun = (run_id: string): Promise<Run> =>
  request(`/api/runs/${run_id}/terminate`, { method: 'POST' })

// --- Events and instructions ---
export const sendEvent = (run_id: string, event_type: string, data: any): Promise<any> =>
  request(`/api/runs/${run_id}/events`, {
    method: 'POST',
    body: JSON.stringify({ event_type, data }),
  })

export const addInstruction = (run_id: string, instruction: string): Promise<Run> =>
  request(`/api/runs/${run_id}/instructions`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  })

// --- Health ---
export const getHealth = (): Promise<{ status: string; environment: string }> =>
  request('/health')
