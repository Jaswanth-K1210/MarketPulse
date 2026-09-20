import React, { useEffect, useState } from 'react'
import { getEvidenceHealth } from '../services/api'
import { T as C } from '../theme'

// A dead feed should be visible at a glance, not inferred from a suspicious zero.
const dot = (available) => ({
  display: 'inline-block', width: 8, height: 8, borderRadius: 4,
  background: available ? C.green : C.red, marginRight: 6,
})

export default function SourceCoverage({ compact = false }) {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const load = () => getEvidenceHealth().then(setHealth).catch(() => setHealth(null))
    load()
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
  }, [])

  if (!health || !health.sources) return null
  const { live_count: live, total_count: total, sources } = health
  if (!total) return null

  const tone = live < total ? C.orange : C.green

  if (compact) {
    return (
      <span
        style={{ color: tone, fontSize: 11 }}
        title={Object.entries(sources)
          .filter(([, s]) => !s.available)
          .map(([id, s]) => `${id}: ${s.error || 'unavailable'}`)
          .join('\n') || 'all sources live'}
      >
        {live}/{total} sources live
      </span>
    )
  }

  return (
    <div style={{ fontSize: 12 }}>
      <div style={{ marginBottom: 6, color: tone }}>{live}/{total} sources live</div>
      {Object.entries(sources).map(([id, s]) => (
        <div key={id} title={s.error || s.origin || ''} style={{ color: C.muted }}>
          <span style={dot(s.available)} />
          {id}
          {!s.available && s.error ? ` — ${s.error}` : ''}
        </div>
      ))}
    </div>
  )
}
