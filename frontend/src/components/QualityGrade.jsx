import React from 'react'
import { Shield, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'
import { T as C, GRADE_COLORS } from '../theme'

const GRADE_CONFIG = {
  A: { icon: ShieldCheck, label: 'Excellent', ...GRADE_COLORS.A },
  B: { icon: Shield,      label: 'Good',      ...GRADE_COLORS.B },
  C: { icon: ShieldAlert, label: 'Fair',      ...GRADE_COLORS.C },
  D: { icon: ShieldX,     label: 'Poor',      ...GRADE_COLORS.D },
  F: { icon: ShieldX,     label: 'Failed',    ...GRADE_COLORS.F },
}

function DimBar({ label, score, color }) {
  const pct = Math.round(score * 100)
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] w-20 truncate" style={{ color: C.muted }}>{label}</span>
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: C.dim }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[9px] font-mono w-7 text-right" style={{ color: C.muted }}>{pct}</span>
    </div>
  )
}

export default function QualityGrade({ qualityGrade, qualityScores }) {
  const grade = qualityGrade || ''
  const config = GRADE_CONFIG[grade] || GRADE_CONFIG.F
  const Icon = config.icon
  const scores = qualityScores?.dimensions || qualityScores || {}

  const dimensions = [
    { key: 'accuracy',      label: 'Accuracy',      weight: '25%' },
    { key: 'relevance',     label: 'Relevance',     weight: '15%' },
    { key: 'depth',         label: 'Depth',          weight: '25%' },
    { key: 'timeliness',    label: 'Timeliness',    weight: '15%' },
    { key: 'actionability', label: 'Actionability',  weight: '20%' },
  ]

  if (!grade && Object.keys(scores).length === 0) {
    return (
      <div className="rounded-xl border px-4 py-3" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center gap-2 mb-2">
          <Shield size={12} style={{ color: C.muted }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>Quality Grade</span>
        </div>
        <p className="text-[10px]" style={{ color: C.muted }}>Run the intelligence pipeline to see quality scores.</p>
      </div>
    )
  }

  const overallPct = qualityScores?.overall_score != null ? Math.round(qualityScores.overall_score * 100) : null

  return (
    <div className="rounded-xl border overflow-hidden" style={{ background: C.card, borderColor: C.border }}>
      {/* Header with grade badge */}
      <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: config.bg, border: `2px solid ${config.ring}`, boxShadow: `0 0 20px ${config.ring}` }}>
          <Icon size={18} style={{ color: config.color }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[18px] font-black" style={{ color: config.color }}>{grade}</span>
            <span className="text-[10px] font-mono" style={{ color: C.muted }}>{config.label}</span>
          </div>
          {overallPct != null && (
            <span className="text-[9px] font-mono" style={{ color: C.muted }}>
              Score: {overallPct}/100
            </span>
          )}
        </div>
      </div>

      {/* Dimension bars */}
      <div className="px-4 py-3 space-y-2">
        {dimensions.map(d => {
          const dimData = scores[d.key] || {}
          const score = dimData.score || 0
          return <DimBar key={d.key} label={`${d.label} (${d.weight})`} score={score} color={config.color} />
        })}
      </div>
    </div>
  )
}
