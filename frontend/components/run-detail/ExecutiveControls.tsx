'use client'
import { useState } from 'react'
import type { Run } from '@/lib/types'

interface Props {
  run: Run
  onTrigger: () => Promise<void>
  onWake: () => Promise<void>
  onInterrupt: () => Promise<void>
  onResume: () => Promise<void>
  onTerminate: () => Promise<void>
}

function CtrlBtn({
  label, icon, onClick, disabled, variant = 'secondary',
}: {
  label: string; icon: React.ReactNode; onClick: () => void
  disabled?: boolean; variant?: 'primary' | 'secondary' | 'danger' | 'warning'
}) {
  const [loading, setLoading] = useState(false)
  const colors = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'border border-gray-300 bg-white hover:bg-gray-50 text-gray-700',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    warning: 'bg-yellow-500 hover:bg-yellow-600 text-white',
  }

  async function handle() {
    setLoading(true)
    try { await onClick() } finally { setLoading(false) }
  }

  return (
    <button
      onClick={handle}
      disabled={disabled || loading}
      className={`flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 ${colors[variant]}`}
    >
      {loading
        ? <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        : icon}
      {label}
    </button>
  )
}

export function ExecutiveControls({ run, onTrigger, onWake, onInterrupt, onResume, onTerminate }: Props) {
  const [confirmTerminate, setConfirmTerminate] = useState(false)
  const finished = run.status === 'completed' || run.status === 'terminated'

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Executive Controls</div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        <CtrlBtn
          label="Trigger Agent"
          variant="primary"
          disabled={['paused', 'completed', 'terminated'].includes(run.status)}
          onClick={onTrigger}
          icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
        />
        <CtrlBtn
          label="Wake Run"
          variant="primary"
          disabled={run.status !== 'sleeping'}
          onClick={onWake}
          icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>}
        />
        <CtrlBtn
          label="Pause Run"
          variant="warning"
          disabled={['paused', 'completed', 'terminated'].includes(run.status)}
          onClick={onInterrupt}
          icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <CtrlBtn
          label="Resume Run"
          variant="secondary"
          disabled={run.status !== 'paused'}
          onClick={onResume}
          icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      {confirmTerminate ? (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-2">
          <p className="text-sm text-red-700 mb-2 font-medium">Are you sure? This cannot be undone.</p>
          <div className="flex gap-2">
            <button
              onClick={() => { setConfirmTerminate(false); onTerminate() }}
              className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-md hover:bg-red-700"
            >Confirm</button>
            <button
              onClick={() => setConfirmTerminate(false)}
              className="px-3 py-1.5 border border-gray-300 text-sm rounded-md hover:bg-gray-50 text-gray-700"
            >Cancel</button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setConfirmTerminate(true)}
          disabled={finished}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium disabled:opacity-40 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Terminate Run
        </button>
      )}
    </div>
  )
}
