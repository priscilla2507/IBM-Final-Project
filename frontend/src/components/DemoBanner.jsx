import React, { useState } from 'react'
import { AlertTriangle, RefreshCw, ArrowRightLeft } from 'lucide-react'
import { isDemo } from '../services/api'

export default function DemoBanner({ onCheckBackend, onSwitchLive }) {
  const [checking, setChecking] = useState(false)

  if (!isDemo) return null

  const handleCheck = async () => {
    setChecking(true)
    if (onCheckBackend) await onCheckBackend()
    setTimeout(() => setChecking(false), 1500)
  }

  return (
    <div
      className="flex items-center gap-3 px-6 py-2.5 border-b border-amber-300 text-xs"
      style={{ backgroundColor: '#fffbeb' }}
    >
      <AlertTriangle size={13} className="text-amber-600 flex-shrink-0" />
      <span className="text-amber-800 flex-1">
        <strong>Simulated Demo Mode Active:</strong> Showing authentic Hyderabad heat index data.
        Backend FastAPI at{' '}
        <code className="font-mono bg-amber-100 px-1 py-0.5 rounded text-amber-900">
          http://localhost:8000
        </code>{' '}
        is unreachable / offline.
      </span>
      <button
        onClick={handleCheck}
        disabled={checking}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-amber-400 text-amber-800 hover:bg-amber-100 transition-colors font-medium whitespace-nowrap"
      >
        {checking ? <RefreshCw size={12} className="animate-spin" /> : null}
        Check Backend
      </button>
      <button
        onClick={onSwitchLive}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-white font-medium whitespace-nowrap transition-colors"
        style={{ backgroundColor: '#b45309' }}
      >
        <ArrowRightLeft size={12} />
        Switch to Live API
      </button>
    </div>
  )
}
