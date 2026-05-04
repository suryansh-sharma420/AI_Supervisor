export interface Supervisor {
  id: string
  name: string
  base_instruction: string
  available_actions: string[]
  wake_up_behavior: Record<string, any> | null
  wake_aggressiveness: 'conservative' | 'normal' | 'aggressive'
  default_sleep_minutes: number
  llm_settings: Record<string, any> | null
  created_at: string
  updated_at: string
}

export interface RunState {
  order_status: string
  agent_summary: string
  next_check_focus?: string
  iteration_count: number
  custom_instructions: string[]
  events_since_last_wake: any[]
  last_action?: string
}

export interface Run {
  id: string
  supervisor_id: string
  order_id: string
  status: 'active' | 'sleeping' | 'running' | 'paused' | 'completed' | 'terminated'
  state: RunState
  wake_at: string | null
  started_at: string
  completed_at: string | null
  max_run_age_hours: number
  final_summary: string | null
  created_at: string
  updated_at: string
}

export type ActivityType =
  | 'event_received'
  | 'wake_decision'
  | 'agent_action'
  | 'sleep_decision'
  | 'manual_instruction'
  | 'final_output'
  | 'system_event'

export interface Activity {
  id: string
  run_id: string
  activity_type: ActivityType
  payload: Record<string, any>
  created_at: string
}

export interface SupervisorCreate {
  name: string
  base_instruction: string
  available_actions: string[]
  wake_aggressiveness: 'conservative' | 'normal' | 'aggressive'
  default_sleep_minutes: number
  wake_up_behavior?: Record<string, any>
  llm_settings?: { model: string }
}

export interface RunCreate {
  supervisor_id: string
  order_id: string
  max_run_age_hours?: number
  initial_state?: Record<string, any>
}
