import React from 'react'
import { ClipboardList, Check, X, Clock, Zap, AlertTriangle } from 'lucide-react'

import { T as C } from '../theme'

function formatMs(ms) {
  if (!ms && ms !== 0) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function NodeRow({ node, index, total }) {
  const success = node.success !== false
  const isSlowest = node.duration_ms > 3000

  return (
    <div className="flex items-start gap-2.5 relative">
      {/* Timeline line */}
      {index < total - 1 && (
        <div className="absolute left-[9px] top-5 w-px h-full" style={{ background: C.dim }} />
      )}

      {/* Node indicator */}
      <div className="w-[18px] h-[18px] rounded-full flex items-center justify-center shrink-0 z-10"
        style={{
          background: success ? C.greenSoft : C.redSoft,
          border: `2px solid ${success ? C.green : C.red}`,
        }}>
        {success
          ? <Check size={8} style={{ color: C.green }} />
          : <X size={8} style={{ color: C.red }} />}
      </div>

      {/* Node details */}
      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold truncate" style={{ color: C.text }}>
            {node.node}
          </span>
          {isSlowest && (
            <span className="text-[7px] px-1 py-0.5 rounded font-mono" style={{ background: C.orangeSoft, color: C.orange }}>
              SLOW
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[8px] font-mono flex items-center gap-0.5" style={{ color: C.muted }}>
            <Clock size={7} /> {formatMs(node.duration_ms)}
          </span>
          {node.tools_called > 0 && (
            <span className="text-[8px] font-mono flex items-center gap-0.5" style={{ color: C.cyan }}>
              <Zap size={7} /> {node.tools_called} tool{node.tools_called > 1 ? 's' : ''}
            </span>
          )}
          {node.llm_calls > 0 && (
            <span className="text-[8px] font-mono flex items-center gap-0.5" style={{ color: C.purple }}>
              <Zap size={7} /> {node.llm_calls} LLM
            </span>
          )}
          {node.errors > 0 && (
            <span className="text-[8px] font-mono flex items-center gap-0.5" style={{ color: C.red }}>
              <AlertTriangle size={7} /> {node.errors}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AuditTrail({ auditSummary }) {
  const summary = auditSummary || {}

  if (!summary.pipeline_id && !summary.node_breakdown?.length) {
    return (
      <div className="rounded-xl border px-4 py-3" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center gap-2 mb-1">
          <ClipboardList size={12} style={{ color: C.muted }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>Audit Trail</span>
        </div>
        <p className="text-[10px]" style={{ color: C.muted }}>Run the pipeline to see execution audit.</p>
      </div>
    )
  }

  const nodes = summary.node_breakdown || []
  const slowest = summary.slowest_nodes?.[0]

  return (
    <div className="rounded-xl border overflow-hidden" style={{ background: C.card, borderColor: C.border }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2">
          <ClipboardList size={12} style={{ color: C.blue }} />
          <span className="text-[11px] font-bold" style={{ color: C.text }}>Audit Trail</span>
        </div>
        <div className="flex items-center gap-3 text-[8px] font-mono" style={{ color: C.muted }}>
          <span>{summary.total_nodes || 0} nodes</span>
          <span>{formatMs(summary.total_duration_ms)}</span>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-4 gap-1 px-4 py-2 border-b" style={{ borderColor: C.border }}>
        {[
          { label: 'Tools', value: summary.total_tool_calls || 0, color: C.cyan },
          { label: 'LLM', value: summary.total_llm_calls || 0, color: C.purple },
          { label: 'Errors', value: summary.total_errors || 0, color: summary.total_errors ? C.red : C.green },
          { label: 'Pipeline', value: summary.success ? 'OK' : 'FAIL', color: summary.success ? C.green : C.red },
        ].map((s, i) => (
          <div key={i} className="text-center">
            <div className="text-[11px] font-bold font-mono" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[7px]" style={{ color: C.muted }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Node timeline */}
      <div className="px-4 py-3 max-h-[280px] overflow-y-auto">
        {nodes.map((node, i) => (
          <NodeRow key={i} node={node} index={i} total={nodes.length} />
        ))}
      </div>

      {/* Slowest node */}
      {slowest && (
        <div className="px-4 py-2 border-t flex items-center gap-2" style={{ borderColor: C.border }}>
          <AlertTriangle size={9} style={{ color: C.orange }} />
          <span className="text-[8px] font-mono" style={{ color: C.muted }}>
            Slowest: <span style={{ color: C.orange }}>{slowest.node}</span> ({formatMs(slowest.duration_ms)})
          </span>
        </div>
      )}

      {/* Pipeline ID */}
      {summary.pipeline_id && (
        <div className="px-4 py-1.5 border-t" style={{ borderColor: C.border }}>
          <span className="text-[7px] font-mono" style={{ color: C.dim }}>{summary.pipeline_id}</span>
        </div>
      )}
    </div>
  )
}
