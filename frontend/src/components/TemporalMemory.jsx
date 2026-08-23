import React from 'react'
import { Clock, TrendingUp, TrendingDown, Minus, Flame } from 'lucide-react'
import { T as C } from '../theme'

function StreakBadge({ streak }) {
  if (!streak || streak.count < 2) return null
  const isBearish = streak.direction === 'bearish'
  const isBullish = streak.direction === 'bullish'
  const color = isBearish ? C.red : isBullish ? C.green : C.orange
  const bg = isBearish ? C.redSoft : isBullish ? C.greenSoft : C.orangeSoft

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded-md" style={{ background: bg }}>
      <Flame size={10} style={{ color }} />
      <span className="text-[10px] font-bold" style={{ color }}>
        {streak.count}x {streak.direction}
      </span>
      {streak.total_impact != null && streak.total_impact !== 0 && (
        <span className="text-[9px] font-mono" style={{ color: C.muted }}>
          ({streak.total_impact > 0 ? '+' : ''}{Number(streak.total_impact).toFixed(1)}%)
        </span>
      )}
    </div>
  )
}

function TrendIcon({ trend }) {
  if (!trend || trend === 'insufficient_data') return <Minus size={10} style={{ color: C.dim }} />
  if (trend === 'improving') return <TrendingUp size={10} style={{ color: C.green }} />
  if (trend === 'deteriorating') return <TrendingDown size={10} style={{ color: C.red }} />
  return <Minus size={10} style={{ color: C.orange }} />
}

function SignalBar({ bullish, bearish, total }) {
  if (!total) return null
  const bullPct = (bullish / total) * 100
  const bearPct = (bearish / total) * 100

  return (
    <div className="space-y-1">
      <div className="flex h-2 rounded-full overflow-hidden" style={{ background: C.dim }}>
        {bullPct > 0 && <div className="transition-all" style={{ width: `${bullPct}%`, background: C.green }} />}
        {bearPct > 0 && <div className="transition-all" style={{ width: `${bearPct}%`, background: C.red }} />}
      </div>
      <div className="flex justify-between text-[8px] font-mono" style={{ color: C.muted }}>
        <span style={{ color: C.green }}>{bullish} bull</span>
        <span>{total} total</span>
        <span style={{ color: C.red }}>{bearish} bear</span>
      </div>
    </div>
  )
}

export default function TemporalMemory({ temporalContext, ticker }) {
  const context = temporalContext || {}
  const streak = context.streak || {}
  const trend = context.trend || {}

  if (context.total_signals === 0 && !streak.direction) {
    return (
      <div className="rounded-xl border px-4 py-3" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center gap-2 mb-1">
          <Clock size={12} style={{ color: C.muted }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>
            Temporal Memory{ticker ? `: ${ticker}` : ''}
          </span>
        </div>
        <p className="text-[10px]" style={{ color: C.muted }}>No signals recorded yet.</p>
      </div>
    )
  }

  const trendLabel = trend.trend === 'improving' ? 'Improving'
    : trend.trend === 'deteriorating' ? 'Deteriorating'
    : trend.trend === 'stable' ? 'Stable'
    : '—'

  const trendColor = trend.trend === 'improving' ? C.green
    : trend.trend === 'deteriorating' ? C.red
    : trend.trend === 'stable' ? C.orange
    : C.muted

  return (
    <div className="rounded-xl border overflow-hidden" style={{ background: C.card, borderColor: C.border }}>
      <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <Clock size={12} style={{ color: C.cyan }} />
        <span className="text-[11px] font-bold" style={{ color: C.text }}>
          Temporal Memory{ticker ? `: ${ticker}` : ''}
        </span>
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Streak + Trend row */}
        <div className="flex items-center gap-3">
          <StreakBadge streak={streak} />
          <div className="flex items-center gap-1.5">
            <TrendIcon trend={trend.trend} />
            <span className="text-[10px] font-mono" style={{ color: trendColor }}>{trendLabel}</span>
          </div>
        </div>

        {/* Signal distribution */}
        <SignalBar bullish={context.bullish_count} bearish={context.bearish_count} total={context.total_signals} />

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Avg Sentiment', value: trend.avg_sentiment != null ? trend.avg_sentiment.toFixed(3) : '—', color: trend.avg_sentiment > 0 ? C.green : trend.avg_sentiment < 0 ? C.red : C.muted },
            { label: 'Momentum', value: trend.momentum != null ? `${trend.momentum > 0 ? '+' : ''}${trend.momentum.toFixed(3)}` : '—', color: trend.momentum > 0 ? C.green : trend.momentum < 0 ? C.red : C.muted },
            { label: 'Signal Count', value: trend.signal_count || context.total_signals || 0, color: C.text },
          ].map((s, i) => (
            <div key={i} className="text-center">
              <div className="text-[12px] font-bold font-mono" style={{ color: s.color }}>{s.value}</div>
              <div className="text-[8px]" style={{ color: C.muted }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
