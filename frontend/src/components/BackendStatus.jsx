import React, { useState, useEffect, useCallback } from 'react'
import { Loader, WifiOff } from 'lucide-react'
import { getHealth } from '../services/api'

// The backend sleeps after ~15min idle and a cold start takes ~60s. Without
// this the app renders empty panels during the wake-up and looks broken.
export default function BackendStatus() {
  const [state, setState] = useState('checking') // checking | waking | ok | down

  const check = useCallback(() => {
    setState('checking')
    let settled = false
    const slow = setTimeout(() => { if (!settled) setState('waking') }, 3000)
    getHealth()
      .then(() => setState('ok'))
      .catch(() => setState('down'))
      .finally(() => { settled = true; clearTimeout(slow) })
  }, [])

  useEffect(check, [check])

  if (state === 'ok' || state === 'checking') return null

  const waking = state === 'waking'
  return (
    <div
      className={`px-4 py-2 text-sm flex items-center gap-2 border-b ${
        waking
          ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-300'
          : 'bg-red-500/10 border-red-500/30 text-red-300'
      }`}
    >
      {waking ? <Loader size={14} className="animate-spin" /> : <WifiOff size={14} />}
      <span>
        {waking
          ? 'Waking the backend — free tier cold start, this can take up to a minute.'
          : 'Backend unreachable. Data shown may be stale.'}
      </span>
      {!waking && (
        <button onClick={check} className="ml-2 underline hover:no-underline">
          Retry
        </button>
      )}
    </div>
  )
}
