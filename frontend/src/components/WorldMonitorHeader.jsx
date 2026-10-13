import React, { useState, useEffect } from 'react'
import { 
  RefreshCw, Search, Bell, Settings, Shield, 
  Activity, Clock, Globe, Zap, Monitor, 
  ChevronDown, Sun, Moon, Wifi, WifiOff
} from 'lucide-react'
import { T as C } from '../theme'
import { getEvidenceHealth } from '../services/api'

// World Monitor style variants
const VARIANTS = [
  { id: 'world', label: 'World', icon: Globe },
  { id: 'tech', label: 'Tech', icon: Monitor },
  { id: 'finance', label: 'Finance', icon: Activity },
  { id: 'happy', label: 'Happy', icon: Zap },
]

// Source freshness comes from /api/evidence/health. This panel used to render
// a hardcoded list that always claimed "live" with invented latencies — the
// exact failure this whole layer exists to stop: a dead feed reported as fine.
const formatAge = (seconds) => {
  if (seconds == null) return 'age unknown'
  if (seconds < 60) return `${Math.round(seconds)}s ago`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  return `${Math.round(seconds / 3600)}h ago`
}

export default function WorldMonitorHeader({ 
  isConnected, 
  refreshing, 
  onRefresh, 
  currentVariant = 'world',
  onVariantChange,
  theme = 'dark',
  onThemeToggle 
}) {
  const [time, setTime] = useState(new Date())
  const [showVariants, setShowVariants] = useState(false)
  const [showDataFreshness, setShowDataFreshness] = useState(false)
  // ponytail: hardcoded placeholder, never updated; wire to a real source count
  const signalCount = 12
  const [showSettings, setShowSettings] = useState(false)
  const [evidence, setEvidence] = useState(null)

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const load = () => getEvidenceHealth().then(setEvidence).catch(() => setEvidence(null))
    load()
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
  }, [])

  const sourceList = Object.entries(evidence?.sources || {}).map(([id, s]) => ({
    id,
    name: id,
    available: s.available,
    detail: s.available ? formatAge(s.age_seconds) : (s.error || 'unavailable'),
  }))
  const activeSources = evidence?.live_count ?? 0
  const totalSources = evidence?.total_count ?? 0
  const delayedSources = totalSources - activeSources

  return (
    <div className="flex items-center gap-2 sm:gap-3 px-2 sm:px-4 border-b shrink-0"
      style={{ height: 44, background: C.panel, borderColor: C.border }}>

      {/* Brand block */}
      <div className="flex items-center gap-2.5">
        <div className="w-6 h-6 rounded border flex items-center justify-center text-[10px] font-bold"
          style={{ borderColor: '#2f8f68', color: '#4ade80', background: '#14532d' }}>
          M
        </div>
        <div className="hidden lg:block">
          <span className="text-[13px] font-bold tracking-tight" style={{ color: C.text }}>
            MarketPulse
          </span>
          <span className="hidden lg:block text-[9px] ml-1" style={{ color: C.dim }}>
            AI Intelligence
          </span>
        </div>
      </div>

      {/* Variant switcher */}
      <div className="relative">
        <button
          onClick={() => setShowVariants(!showVariants)}
          className="flex items-center gap-2 px-2 py-1.5"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
        >
          {React.createElement(VARIANTS.find(v => v.id === currentVariant)?.icon || Globe, { 
            size: 12, 
            style: { color: C.blue } 
          })}
          <span className="hidden sm:inline text-[10px] font-semibold" style={{ color: C.text }}>
            {VARIANTS.find(v => v.id === currentVariant)?.label || 'World'}
          </span>
          <ChevronDown size={10} style={{ color: C.muted }} />
        </button>

        {showVariants && (
          <div 
            className="absolute top-full left-0 mt-1 p-1 space-y-0.5"
            style={{ 
              background: C.panel, 
              border: `1px solid ${C.border}`,
              borderRadius: '2px',
              minWidth: '120px',
              zIndex: 100
            }}
          >
            {VARIANTS.map(variant => (
              <button
                key={variant.id}
                onClick={() => {
                  onVariantChange?.(variant.id)
                  setShowVariants(false)
                }}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-left"
                style={{
                  background: currentVariant === variant.id ? C.blueSoft : 'transparent',
                  borderRadius: '2px'
                }}
              >
                {React.createElement(variant.icon, { 
                  size: 12, 
                  style: { color: currentVariant === variant.id ? C.blue : C.muted } 
                })}
                <span className="text-[10px]" style={{ color: currentVariant === variant.id ? C.blue : C.muted }}>
                  {variant.label}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Search - mobile responsive */}
      <div className="relative ml-2 hidden md:block">
        <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: C.dim }} />
        <input
          placeholder="Search companies, events… (Cmd+K)"
          className="pl-7 pr-2 py-1 text-[11px] outline-none w-48 lg:w-64"
          style={{ 
            background: C.bgDeep, 
            border: `1px solid ${C.border}`, 
            color: C.text,
            borderRadius: '2px'
          }}
        />
      </div>

      {/* Mobile: search icon only */}
      <button aria-label="Search" className="md:hidden w-8 h-8 flex items-center justify-center"
        style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: '2px' }}>
        <Search size={12} style={{ color: C.muted }} />
      </button>

      {/* Intelligence badge */}
      <div className="relative ml-auto">
        <button
          onClick={() => setShowDataFreshness(!showDataFreshness)}
          className="flex items-center gap-2 px-2 py-1.5"
          style={{ 
            background: delayedSources > 0 ? 'rgba(248,113,113,0.12)' : C.card, 
            border: `1px solid ${delayedSources > 0 ? C.red : C.border}`,
            borderRadius: '2px'
          }}
        >
          <Shield size={12} style={{ color: delayedSources > 0 ? C.red : C.blue }} />
          <span className="text-[10px] font-semibold" style={{ color: C.text }}>
            {signalCount}
          </span>
          {delayedSources > 0 && (
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: C.red }} />
          )}
        </button>

        {showDataFreshness && (
          <div 
            className="absolute top-full right-0 mt-1 p-2 space-y-1"
            style={{ 
              background: C.panel, 
              border: `1px solid ${C.border}`,
              borderRadius: '2px',
              minWidth: '220px',
              zIndex: 100
            }}
          >
            <div className="flex items-center justify-between mb-2 pb-1 border-b" style={{ borderColor: C.borderDim }}>
              <span className="text-[9px] font-bold" style={{ color: C.muted }}>
                Data Freshness
              </span>
              <span className="text-[9px]" style={{ color: C.dim }}>
                {activeSources}/{totalSources} live
              </span>
            </div>
            {sourceList.length === 0 && (
              <div className="text-[9px] px-1 py-1" style={{ color: C.dim }}>
                No source has reported yet.
              </div>
            )}
            {sourceList.map(source => (
              <div key={source.id} className="flex items-center justify-between px-1 py-1 gap-2">
                <div className="flex items-center gap-2">
                  <div 
                    className={`w-1.5 h-1.5 rounded-full ${source.available ? 'animate-pulse' : ''}`}
                    style={{ 
                      background: source.available ? C.green : C.red,
                      boxShadow: source.available ? `0 0 4px ${C.green}` : 'none'
                    }}
                  />
                  <span className="text-[9px]" style={{ color: C.muted }}>
                    {source.name}
                  </span>
                </div>
                <span className="text-[9px] font-mono truncate" style={{ color: C.dim, maxWidth: 130 }}
                      title={source.detail}>
                  {source.detail}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Status chips - mobile responsive */}
      <div className="flex items-center gap-1.5">
        {/* Connection status - simplified on mobile */}
        <div className="hidden sm:flex items-center gap-1.5 px-2 py-1"
          style={{ 
            background: isConnected ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)',
            border: `1px solid ${isConnected ? '#14532d' : '#7f1d1d'}`,
            borderRadius: '2px'
          }}
        >
          {isConnected ? (
            <Wifi size={10} style={{ color: C.green }} />
          ) : (
            <WifiOff size={10} style={{ color: C.red }} />
          )}
          <span className="text-[9px] font-semibold" style={{ color: isConnected ? C.green : C.red }}>
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>

        {/* Mobile: just show status dot */}
        <div className="sm:hidden w-2 h-2 rounded-full" style={{ 
          background: isConnected ? C.green : C.red,
          boxShadow: isConnected ? `0 0 6px ${C.green}` : 'none'
        }} />

        {/* UTC time - hide on mobile */}
        <div className="hidden lg:flex items-center gap-1.5 px-2 py-1"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
        >
          <Clock size={10} style={{ color: C.muted }} />
          <span className="text-[9px] font-mono" style={{ color: C.muted }}>
            {time.toUTCString().slice(17, 25)} UTC
          </span>
        </div>

        {/* Refresh button */}
        <button 
          onClick={onRefresh} 
          disabled={refreshing}
          className="w-7 h-7 flex items-center justify-center"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
          title="Refresh data"
        >
          <RefreshCw 
            size={12} 
            style={{ color: C.muted }} 
            className={refreshing ? 'animate-spin' : ''} 
          />
        </button>

        {/* Theme toggle */}
        <button
          onClick={onThemeToggle}
          className="w-7 h-7 flex items-center justify-center"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
          title="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun size={12} style={{ color: C.muted }} />
          ) : (
            <Moon size={12} style={{ color: C.muted }} />
          )}
        </button>

        {/* Settings - hide on mobile */}
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="w-7 h-7 flex items-center justify-center hidden lg:flex"
          style={{ 
            background: C.card, 
            border: `1px solid ${C.border}`,
            borderRadius: '2px'
          }}
          title="Settings (Cmd+,)"
        >
          <Settings size={12} style={{ color: C.muted }} />
        </button>
      </div>
    </div>
  )
}