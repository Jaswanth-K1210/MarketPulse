import React from 'react'
import { GitBranch, ArrowRight } from 'lucide-react'

import { T as C, EDGE_COLORS } from '../theme'

function NeighborRow({ neighbor }) {
  const target = neighbor.target || neighbor.id || '???'
  const edgeType = neighbor.edge_type || 'related'
  const weight = neighbor.weight || 0
  const color = EDGE_COLORS[edgeType] || C.muted
  const nodeType = neighbor.node_type || 'company'

  return (
    <div className="flex items-center gap-2 px-2 py-1.5 rounded-md" style={{ background: 'rgba(255,255,255,0.02)' }}>
      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
      <ArrowRight size={7} style={{ color: C.dim }} />
      <span className="text-[10px] font-mono font-bold flex-1 truncate" style={{ color: C.text }}>
        {target}
      </span>
      <span className="text-[8px] font-mono px-1.5 py-0.5 rounded" style={{ background: color + '15', color }}>
        {edgeType}
      </span>
      <span className="text-[8px] font-mono" style={{ color: C.muted }}>
        {(weight * 100).toFixed(0)}%
      </span>
    </div>
  )
}

export default function KGContext({ kgContext, ticker }) {
  const ctx = kgContext || {}
  const neighbors = ctx.neighbors || []

  if (!ctx.found && neighbors.length === 0) {
    return (
      <div className="rounded-xl border px-4 py-3" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center gap-2 mb-1">
          <GitBranch size={12} style={{ color: C.muted }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>
            Knowledge Graph{ticker ? `: ${ticker}` : ''}
          </span>
        </div>
        <p className="text-[10px]" style={{ color: C.muted }}>No graph data for this ticker yet.</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border overflow-hidden" style={{ background: C.card, borderColor: C.border }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2">
          <GitBranch size={12} style={{ color: C.cyan }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>
            Knowledge Graph{ticker ? `: ${ticker}` : ''}
          </span>
        </div>
        <div className="flex items-center gap-2 text-[8px] font-mono" style={{ color: C.muted }}>
          <span>{neighbors.length} neighbors</span>
          <span>deg: {ctx.degree || 0}</span>
        </div>
      </div>

      {/* Attributes */}
      {ctx.attributes && Object.keys(ctx.attributes).length > 0 && (
        <div className="px-4 py-2 border-b flex gap-3" style={{ borderColor: C.border }}>
          {Object.entries(ctx.attributes).filter(([k]) => !['type'].includes(k)).slice(0, 4).map(([k, v]) => (
            <div key={k} className="text-center">
              <div className="text-[9px] font-mono" style={{ color: C.text }}>{String(v)}</div>
              <div className="text-[7px]" style={{ color: C.muted }}>{k}</div>
            </div>
          ))}
        </div>
      )}

      {/* Neighbors list */}
      <div className="px-4 py-3 space-y-1 max-h-[200px] overflow-y-auto">
        {neighbors.slice(0, 8).map((n, i) => (
          <NeighborRow key={i} neighbor={n} />
        ))}
      </div>
    </div>
  )
}
