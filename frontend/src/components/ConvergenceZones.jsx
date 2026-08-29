import React from 'react'
import { Network, Circle, Zap, TrendingUp, TrendingDown } from 'lucide-react'

import { T as C, SOURCE_COLORS } from '../theme'

function SourceDot({ source, active }) {
  const color = SOURCE_COLORS[source] || C.muted

  return (
    <div className="flex items-center gap-1.5">
      <div className="w-2 h-2 rounded-full" style={{ background: active ? color : C.dim }} />
      <span className="text-[9px] font-mono" style={{ color: active ? C.text : C.dim }}>
        {source}
      </span>
    </div>
  )
}

function ZoneCard({ zone }) {
  const ticker = zone.ticker || '???'
  const signal = zone.signal || zone.direction || 'mixed'
  const score = zone.score || zone.confidence || zone.impact_pct || 0
  const sources = zone.sources_count || zone.sources || 0
  const sourceList = zone.sources_list || zone.tools_triggered || []

  const isBearish = signal.toLowerCase().includes('bear') || score < -0.1
  const isBullish = signal.toLowerCase().includes('bull') || score > 0.1
  const color = isBearish ? C.red : isBullish ? C.green : C.orange
  const bg = isBearish ? C.redSoft : isBullish ? C.greenSoft : C.orangeSoft
  const SignalIcon = isBearish ? TrendingDown : isBullish ? TrendingUp : Zap

  return (
    <div className="rounded-lg border px-3 py-2.5" style={{ background: C.card, borderColor: color + '30' }}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-black font-mono" style={{ color }}>{ticker}</span>
          <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded" style={{ background: bg }}>
            <SignalIcon size={8} style={{ color }} />
            <span className="text-[8px] font-bold uppercase" style={{ color }}>{signal}</span>
          </div>
        </div>
        {typeof score === 'number' && (
          <span className="text-[10px] font-mono font-bold" style={{ color }}>
            {score > 0 ? '+' : ''}{typeof score === 'number' ? score.toFixed(1) : score}
            {typeof score === 'number' && Math.abs(score) < 10 ? '%' : ''}
          </span>
        )}
      </div>

      {/* Source convergence dots */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {typeof sources === 'number' ? (
          <>
            <span className="text-[8px] font-mono" style={{ color: C.muted }}>{sources} sources</span>
            {Array.from({ length: sources }, (_, i) => (
              <Circle key={i} size={4} fill={color} style={{ color }} />
            ))}
          </>
        ) : (
          sourceList.map((s, i) => <SourceDot key={i} source={s} active />)
        )}
      </div>
    </div>
  )
}

export default function ConvergenceZones({ convergenceZones }) {
  const zones = convergenceZones || []

  if (!zones.length) {
    return (
      <div className="rounded-xl border px-4 py-3" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center gap-2 mb-1">
          <Network size={12} style={{ color: C.muted }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>Convergence Zones</span>
        </div>
        <p className="text-[10px]" style={{ color: C.muted }}>Run the pipeline to detect multi-source convergence.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border overflow-hidden" style={{ background: C.card, borderColor: C.border }}>
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2">
          <Network size={12} style={{ color: C.purple }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>Convergence Zones</span>
        </div>
        <span className="text-[9px] font-mono px-2 py-0.5 rounded-full" style={{ background: C.purpleSoft, color: C.purple }}>
          {zones.length} detected
        </span>
      </div>

      <div className="px-4 py-3 space-y-2">
        {zones.slice(0, 6).map((zone, i) => (
          <ZoneCard key={i} zone={zone} />
        ))}
      </div>
    </div>
  )
}
