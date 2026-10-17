import React from 'react'

import { T as C } from '../theme'
import { parseTimestamp } from '../utils/dataTransform'

export const fmt  = n => n == null ? '—' : typeof n === 'number' ? n.toFixed(2) : n
export const ago  = ts => {
  const t = parseTimestamp(ts)
  if (!t) return ''
  const d = Math.floor((Date.now() - t) / 1000)
  if (d < 60) return `${d}s ago`
  if (d < 3600) return `${Math.floor(d / 60)}m ago`
  return `${Math.floor(d / 3600)}h ago`
}
export const sevColor = s => {
  if (!s) return C.blue
  const u = s.toUpperCase()
  if (u === 'CRITICAL' || u === 'HIGH') return C.red
  if (u === 'MEDIUM'   || u === 'MODERATE') return C.orange
  return C.green
}
const sevBg = s => {
  if (!s) return C.blueSoft
  const u = s.toUpperCase()
  if (u === 'CRITICAL' || u === 'HIGH') return C.redSoft
  if (u === 'MEDIUM'   || u === 'MODERATE') return C.orangeSoft
  return C.greenSoft
}

export default function AlertCard({ alert: a, onExplain }) {
  return (
    <div onClick={() => onExplain(a)}
      className="grid grid-cols-[80px_1fr_60px_64px] items-center px-3 py-2.5 border-b cursor-pointer transition-all"
      style={{ borderColor: C.borderDim }}
      onMouseEnter={e => e.currentTarget.style.background = C.cardHover}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
      <div>
        <span className="text-[9px] font-semibold px-1.5 py-0.5 border"
          style={{ background: sevBg(a.severity), color: sevColor(a.severity), borderColor: `${sevColor(a.severity)}33` }}>
          {(a.severity || 'LOW').slice(0, 6)}
        </span>
      </div>
      <span className="text-[11px] truncate pr-2" style={{ color: C.text }}>
        {a.ticker ? `${a.ticker} — ` : ''}{(a.description || a.event || 'Market event').slice(0, 55)}
      </span>
      <span className="text-[11px] font-semibold" style={{ color: a.impact_percent >= 0 ? C.green : C.red }}>
        {a.impact_percent != null ? `${a.impact_percent >= 0 ? '+' : ''}${fmt(a.impact_percent)}%` : '—'}
      </span>
      <span className="text-[10px]" style={{ color: C.muted }}>{ago(a.created_at ?? a.timestamp)}</span>
    </div>
  )
}
