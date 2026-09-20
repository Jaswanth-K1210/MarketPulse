import React from 'react'
import { TrendingUp, TrendingDown, Activity } from 'lucide-react'

const C = {
  bg: '#0a0a0a', card: '#141414', border: '#2a2a2a', text: '#f5f5f5',
  muted: '#9ca3af', dim: '#52525b', green: '#4ade80', red: '#f87171',
  blue: '#4ade80', orange: '#fbbf24',
}

function signalIcon(signal) {
  if (signal.toLowerCase().includes('bullish') || signal.toLowerCase().includes('buying')) {
    return <TrendingUp size={14} style={{ color: C.green }} />
  }
  if (signal.toLowerCase().includes('bearish') || signal.toLowerCase().includes('selling')) {
    return <TrendingDown size={14} style={{ color: C.red }} />
  }
  return <Activity size={14} style={{ color: C.blue }} />
}

function signalColor(signal) {
  if (signal.toLowerCase().includes('bullish') || signal.toLowerCase().includes('buying')) return C.green
  if (signal.toLowerCase().includes('bearish') || signal.toLowerCase().includes('selling')) return C.red
  return C.blue
}

export default function SignalTimeline({ signals = [], ticker = '' }) {
  if (!signals || signals.length === 0) return null

  return (
    <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
      <h3 className="text-sm font-bold mb-4" style={{ color: C.text }}>
        Active Signals {ticker && <>for {ticker}</>}
      </h3>
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px" style={{ background: C.border }} />
        <div className="space-y-4">
          {signals.map((signal, i) => (
            <div key={i} className="relative flex items-start gap-4 pl-10">
              <div className="absolute left-2.5 -translate-x-1/2 mt-1.5">
                <div className="w-3 h-3 rounded-full" style={{ background: signalColor(signal), boxShadow: `0 0 8px ${signalColor(signal)}` }} />
              </div>
              <div className="flex-1 py-2 px-3 rounded-none" style={{ background: `${C.bg}` }}>
                <div className="flex items-center gap-2">
                  {signalIcon(signal)}
                  <span className="text-sm" style={{ color: C.text }}>{signal}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
