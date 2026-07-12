import React, { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw, Search, Bell, TrendingUp, TrendingDown, Shield, Zap,
  Radio, BarChart2, ArrowUpRight, ArrowDownRight, ChevronUp, ChevronDown,
  Activity, Cpu, Globe, BookOpen, ExternalLink, Star
} from 'lucide-react'
import ExplanationModal from '../components/ExplanationModal'
import {
  getAlerts, getPortfolio, getStats, fetchAndAnalyzeNews,
  getArticles, getStockPrices, getMarketOverview
} from '../services/api'
import { transformAlert, transformPortfolio, transformStats } from '../utils/dataTransform'
import { useWebSocket } from '../hooks/useWebSocket'

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  bg:          '#0b1221',
  panel:       '#0f1a2e',
  card:        '#131f35',
  cardHover:   '#182540',
  border:      '#1c2f4a',
  borderDim:   '#152340',
  text:        '#dde8f5',
  muted:       '#5d7a9a',
  dim:         '#243650',
  blue:        '#4f91f6',
  blueSoft:    'rgba(79,145,246,0.1)',
  green:       '#22d18b',
  greenSoft:   'rgba(34,209,139,0.1)',
  red:         '#f06565',
  redSoft:     'rgba(240,101,101,0.1)',
  orange:      '#f5a523',
  orangeSoft:  'rgba(245,165,35,0.1)',
  purple:      '#a07cf5',
  purpleSoft:  'rgba(160,124,245,0.1)',
  cyan:        '#22d3ee',
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt  = n => n == null ? '—' : typeof n === 'number' ? n.toFixed(2) : n
const ago  = ts => {
  if (!ts) return ''
  const d = Math.floor((Date.now() - new Date(ts)) / 1000)
  if (d < 60) return `${d}s ago`
  if (d < 3600) return `${Math.floor(d / 60)}m ago`
  return `${Math.floor(d / 3600)}h ago`
}
const sevColor = s => {
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

// ── Alert sparkline (7-day trend) ─────────────────────────────────────────────
function AlertTrendChart({ alerts }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  // Build rough daily counts from alert timestamps, fallback to illustrative data
  const base = [2, 5, 3, 8, 4, 6, alerts.length || 4]
  const max  = Math.max(...base, 1)
  const W = 260, H = 72
  const pl = 4, pr = 4, pt = 6, pb = 22

  const pts = base.map((v, i) => ({
    x: pl + (i / (base.length - 1)) * (W - pl - pr),
    y: pt + (1 - v / max) * (H - pt - pb),
  }))
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = `${line} L${pts.at(-1).x.toFixed(1)},${(H - pb).toFixed(1)} L${pts[0].x.toFixed(1)},${(H - pb).toFixed(1)} Z`

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.blue} stopOpacity="0.25" />
          <stop offset="100%" stopColor={C.blue} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#trendFill)" />
      <path d={line} fill="none" stroke={C.blue} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="2.5" fill={C.blue} />
      ))}
      {days.map((d, i) => (
        <text key={d} x={pts[i].x} y={H - 4} textAnchor="middle"
          style={{ fontSize: '8px', fill: C.muted, fontFamily: 'monospace' }}>
          {d}
        </text>
      ))}
    </svg>
  )
}

// ── Top bar ───────────────────────────────────────────────────────────────────
function TopBar({ isConnected, refreshing, analyzing, onRefresh, onAnalyze }) {
  const [tick, setTick] = useState(new Date())
  const [q, setQ] = useState('')
  useEffect(() => {
    const t = setInterval(() => setTick(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex items-center gap-4 px-6 border-b shrink-0"
      style={{ height: 56, background: C.bg, borderColor: C.border }}>

      {/* Title block */}
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <h1 className="text-[16px] font-black" style={{ color: C.text }}>Dashboard</h1>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full"
              style={{ background: isConnected ? C.green : C.red, boxShadow: `0 0 6px ${isConnected ? C.green : C.red}` }} />
            <span className="text-[9px] font-bold uppercase tracking-widest"
              style={{ color: isConnected ? C.green : C.red }}>
              {isConnected ? 'Live' : 'Offline'}
            </span>
          </div>
        </div>
        <p className="text-[11px] mt-0.5" style={{ color: C.muted }}>
          Real-time market intelligence at a glance
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Search companies, events…"
          className="pl-8 pr-3 py-1.5 rounded-lg text-[11px] outline-none transition-all w-56"
          style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }}
          onFocus={e => { e.target.style.borderColor = C.blue }}
          onBlur={e  => { e.target.style.borderColor = C.border }} />
      </div>

      {/* Time */}
      <span className="text-[10px] font-mono shrink-0" style={{ color: C.muted }}>
        {tick.toUTCString().slice(17, 25)} UTC
      </span>

      {/* Refresh */}
      <button onClick={onRefresh} disabled={refreshing} title="Refresh"
        className="w-8 h-8 rounded-lg flex items-center justify-center transition-all active:scale-95 disabled:opacity-40"
        style={{ background: C.card, border: `1px solid ${C.border}` }}>
        <RefreshCw size={13} style={{ color: C.muted }} className={refreshing ? 'animate-spin' : ''} />
      </button>
    </div>
  )
}

// ── Stock prices row ──────────────────────────────────────────────────────────
function StockPricesSection({ prices, onRefresh, refreshing, lastUpdated }) {
  const entries = Object.entries(prices || {}).slice(0, 6)
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [lastUpdated])

  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: C.border }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={13} style={{ color: C.blue }} />
          <span className="text-[12px] font-black" style={{ color: C.text }}>Live Stock Prices</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px]" style={{ color: C.muted }}>
            Updated {secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m`} ago
          </span>
          <button onClick={onRefresh} disabled={refreshing}
            className="text-[10px] font-semibold px-2.5 py-1 rounded-md transition-all active:scale-95"
            style={{ background: C.blueSoft, color: C.blue, border: `1px solid rgba(79,145,246,0.2)` }}>
            {refreshing ? 'Refreshing…' : 'Refresh Prices'}
          </button>
        </div>
      </div>

      <div className="flex gap-3">
        {entries.length === 0
          ? ['AAPL', 'NVDA', 'AMD', 'INTC', 'AMGN'].map(t => (
              <div key={t} className="flex-1 rounded-xl p-3 border"
                style={{ background: C.card, borderColor: C.border }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-black font-mono" style={{ color: C.muted }}>{t}</span>
                  <ArrowUpRight size={10} style={{ color: C.dim }} />
                </div>
                <div className="text-[15px] font-black font-mono" style={{ color: C.dim }}>$0.00</div>
                <div className="text-[9px] mt-0.5" style={{ color: C.dim }}>— (0.00%)</div>
              </div>
            ))
          : entries.map(([ticker, d]) => {
              const price = d?.current_price ?? d?.price ?? 0
              const chg   = d?.change_percent ?? 0
              const up    = chg >= 0
              return (
                <div key={ticker} className="flex-1 rounded-xl p-3 border transition-all"
                  style={{ background: C.card, borderColor: C.border }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-black font-mono" style={{ color: C.muted }}>{ticker}</span>
                    {up ? <ArrowUpRight size={10} style={{ color: C.green }} />
                        : <ArrowDownRight size={10} style={{ color: C.red }} />}
                  </div>
                  <div className="text-[15px] font-black font-mono" style={{ color: C.text }}>
                    ${fmt(price)}
                  </div>
                  <div className="text-[9px] mt-0.5 font-semibold" style={{ color: up ? C.green : C.red }}>
                    {up ? '+' : ''}{fmt(chg)}%
                  </div>
                </div>
              )
            })}
      </div>
    </div>
  )
}

// ── Stats row ─────────────────────────────────────────────────────────────────
function StatsRow({ alerts, stats, portfolio }) {
  const watched = portfolio?.holdings?.length ?? stats?.watchedCompanies ?? 0
  const impact  = stats?.marketImpactScore ?? 7.2
  const events  = stats?.eventsDetected ?? 0

  const cards = [
    {
      label: 'Active Alerts',
      value: alerts.length,
      delta: '+0 today',
      color: C.orange,
      bg:    C.orangeSoft,
      icon:  Bell,
    },
    {
      label: 'Watched Companies',
      value: watched,
      delta: '+0 this week',
      color: C.blue,
      bg:    C.blueSoft,
      icon:  Star,
    },
    {
      label: 'Market Impact Score',
      value: typeof impact === 'number' ? impact.toFixed(1) : impact,
      delta: '+0.0 from yesterday',
      color: C.green,
      bg:    C.greenSoft,
      icon:  BarChart2,
    },
    {
      label: 'Events Detected',
      value: events,
      delta: '+0 this week',
      color: C.purple,
      bg:    C.purpleSoft,
      icon:  Activity,
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-4 px-6 py-4 border-b" style={{ borderColor: C.border }}>
      {cards.map(({ label, value, delta, color, bg, icon: Icon }) => (
        <div key={label} className="rounded-xl p-4 border flex items-start gap-3"
          style={{ background: C.card, borderColor: C.border }}>
          <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: bg }}>
            <Icon size={15} style={{ color }} />
          </div>
          <div className="min-w-0">
            <div className="text-[22px] font-black leading-none" style={{ color: C.text }}>{value}</div>
            <div className="text-[11px] font-semibold mt-0.5 truncate" style={{ color: C.muted }}>{label}</div>
            <div className="text-[10px] mt-1" style={{ color }}>
              {delta}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Recent alerts panel ───────────────────────────────────────────────────────
function RecentAlertsPanel({ alerts, onExplain }) {
  return (
    <div className="flex flex-col rounded-xl border overflow-hidden"
      style={{ background: C.panel, borderColor: C.border }}>
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2">
          <Bell size={13} style={{ color: C.orange }} />
          <span className="text-[12px] font-black" style={{ color: C.text }}>Recent Alerts</span>
        </div>
        <button className="text-[10px] font-semibold" style={{ color: C.blue }}>View All</button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {alerts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-28 gap-2">
            <Shield size={18} style={{ color: C.dim }} />
            <span className="text-[11px]" style={{ color: C.dim }}>No alerts — market is calm</span>
          </div>
        )}
        {/* Header row */}
        {alerts.length > 0 && (
          <div className="grid grid-cols-[80px_1fr_60px_64px] px-4 py-2 border-b"
            style={{ borderColor: C.borderDim }}>
            {['Severity', 'Description', 'Impact', 'Time'].map(h => (
              <span key={h} className="text-[9px] font-bold uppercase tracking-widest" style={{ color: C.dim }}>{h}</span>
            ))}
          </div>
        )}
        {alerts.slice(0, 12).map((a, i) => (
          <div key={i} onClick={() => onExplain(a)}
            className="grid grid-cols-[80px_1fr_60px_64px] items-center px-4 py-2.5 border-b cursor-pointer transition-all"
            style={{ borderColor: C.borderDim }}
            onMouseEnter={e => e.currentTarget.style.background = C.cardHover}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <div>
              <span className="text-[9px] font-black px-2 py-0.5 rounded-full"
                style={{ background: sevBg(a.severity), color: sevColor(a.severity) }}>
                {(a.severity || 'LOW').slice(0, 6)}
              </span>
            </div>
            <span className="text-[11px] truncate pr-2" style={{ color: C.text }}>
              {a.ticker ? `${a.ticker} — ` : ''}{(a.description || a.event || 'Market event').slice(0, 55)}
            </span>
            <span className="text-[11px] font-semibold" style={{ color: a.impact_percent >= 0 ? C.green : C.red }}>
              {a.impact_percent != null ? `${a.impact_percent >= 0 ? '+' : ''}${fmt(a.impact_percent)}%` : '—'}
            </span>
            <span className="text-[10px]" style={{ color: C.muted }}>{ago(a.timestamp)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Alert trend panel ─────────────────────────────────────────────────────────
function AlertTrendPanel({ alerts }) {
  return (
    <div className="flex flex-col rounded-xl border overflow-hidden"
      style={{ width: 280, flexShrink: 0, background: C.panel, borderColor: C.border }}>
      <div className="flex items-center gap-2 px-4 py-3 border-b shrink-0" style={{ borderColor: C.border }}>
        <TrendingUp size={13} style={{ color: C.blue }} />
        <span className="text-[12px] font-black" style={{ color: C.text }}>Alert Trend</span>
        <span className="text-[9px] ml-auto" style={{ color: C.muted }}>7 days</span>
      </div>
      <div className="flex-1 flex flex-col justify-between px-4 py-3">
        <AlertTrendChart alerts={alerts} />
        <div className="flex items-center justify-between mt-3">
          <div className="text-center">
            <div className="text-[18px] font-black" style={{ color: C.text }}>{alerts.length}</div>
            <div className="text-[9px] uppercase tracking-wide" style={{ color: C.muted }}>This week</div>
          </div>
          <div className="text-center">
            <div className="text-[18px] font-black"
              style={{ color: alerts.filter(a => ['HIGH','CRITICAL'].includes(a.severity?.toUpperCase())).length > 0 ? C.red : C.green }}>
              {alerts.filter(a => ['HIGH','CRITICAL'].includes(a.severity?.toUpperCase())).length}
            </div>
            <div className="text-[9px] uppercase tracking-wide" style={{ color: C.muted }}>High / Critical</div>
          </div>
          <div className="text-center">
            <div className="text-[18px] font-black" style={{ color: C.orange }}>
              {alerts.filter(a => ['MEDIUM','MODERATE'].includes(a.severity?.toUpperCase())).length}
            </div>
            <div className="text-[9px] uppercase tracking-wide" style={{ color: C.muted }}>Medium</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Recent news panel ─────────────────────────────────────────────────────────
function RecentNewsPanel({ articles }) {
  return (
    <div className="flex flex-col rounded-xl border overflow-hidden"
      style={{ background: C.panel, borderColor: C.border }}>
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: C.border }}>
        <div className="flex items-center gap-2">
          <BookOpen size={13} style={{ color: C.cyan }} />
          <span className="text-[12px] font-black" style={{ color: C.text }}>Recent News</span>
          {articles.length > 0 && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: C.blueSoft, color: C.blue }}>
              {articles.length} articles
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto divide-y" style={{ borderColor: C.borderDim }}>
        {articles.length === 0 && (
          <div className="flex items-center justify-center h-24">
            <span className="text-[11px]" style={{ color: C.dim }}>No recent articles</span>
          </div>
        )}
        {articles.slice(0, 8).map((a, i) => (
          <div key={i} className="px-4 py-3 transition-all"
            onMouseEnter={e => e.currentTarget.style.background = C.cardHover}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            <div className="flex items-start justify-between gap-2">
              <p className="text-[12px] font-semibold leading-snug flex-1" style={{ color: C.text }}>
                {(a.title || '').slice(0, 80)}
              </p>
              <ExternalLink size={10} style={{ color: C.dim, flexShrink: 0, marginTop: 2 }} />
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[9px]" style={{ color: C.muted }}>
                {a.published_at ? new Date(a.published_at).toLocaleDateString() : ''} · {a.source || 'Source'}
              </span>
              {(a.tickers || []).slice(0, 3).map(t => (
                <span key={t} className="text-[8px] font-black px-1.5 py-0.5 rounded"
                  style={{ background: C.blueSoft, color: C.blue }}>
                  {t}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── AI Analysis panel ─────────────────────────────────────────────────────────
function AIAnalysisPanel({ analyzing, analysisResult, onAnalyze }) {
  const steps = [
    { label: 'News Ingestion',    icon: Globe,    desc: 'Multi-source fetch'        },
    { label: 'FinBERT Sentiment', icon: Cpu,      desc: 'Local NLP sentiment model' },
    { label: 'GNN Supply-Chain',  icon: BarChart2, desc: 'Shock propagation graph'  },
    { label: 'Monte Carlo 48h',   icon: Shield,   desc: 'Portfolio risk simulation' },
  ]
  const doneCount = analyzing ? 1 : analysisResult ? 4 : 0

  return (
    <div className="flex flex-col rounded-xl border overflow-hidden"
      style={{ width: 280, flexShrink: 0, background: C.panel, borderColor: C.border }}>

      <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: C.border }}>
        <Cpu size={13} style={{ color: C.purple }} />
        <span className="text-[12px] font-black" style={{ color: C.text }}>AI Analysis</span>
        {analyzing && <span className="ml-auto text-[9px] font-mono animate-pulse" style={{ color: C.purple }}>RUNNING…</span>}
        {analysisResult && !analyzing && <span className="ml-auto text-[9px] font-mono" style={{ color: C.green }}>COMPLETE ✓</span>}
      </div>

      <div className="flex-1 px-4 py-3 flex flex-col gap-3">
        <p className="text-[11px] leading-relaxed" style={{ color: C.muted }}>
          Fetch latest news and run the full multi-agent supply chain intelligence pipeline.
        </p>

        {/* Steps */}
        <div className="space-y-1.5">
          {steps.map((s, i) => {
            const done   = i < doneCount
            const active = analyzing && i === 1
            const Icon   = s.icon
            return (
              <div key={i} className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-all"
                style={{
                  background: done ? C.greenSoft : active ? C.purpleSoft : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${done ? 'rgba(34,209,139,0.2)' : active ? 'rgba(160,124,245,0.2)' : C.borderDim}`,
                }}>
                <div className="w-5 h-5 rounded-md flex items-center justify-center shrink-0"
                  style={{ background: done ? C.greenSoft : active ? C.purpleSoft : C.card }}>
                  {done
                    ? <span className="text-[9px]" style={{ color: C.green }}>✓</span>
                    : active
                      ? <Radio size={9} className="animate-pulse" style={{ color: C.purple }} />
                      : <Icon size={9} style={{ color: C.dim }} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] font-semibold"
                    style={{ color: done ? C.green : active ? C.purple : C.muted }}>
                    {s.label}
                  </div>
                  <div className="text-[9px]" style={{ color: C.dim }}>{s.desc}</div>
                </div>
                {active && (
                  <div className="flex gap-0.5">
                    {[0, 1, 2].map(j => (
                      <div key={j} className="w-1 h-1 rounded-full animate-bounce"
                        style={{ background: C.purple, animationDelay: `${j * 0.12}s` }} />
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Result summary */}
        {analysisResult && !analyzing && (() => {
          const sev     = (analysisResult.mc_severity || 'LOW').toUpperCase()
          const sevClr  = sev === 'CRITICAL' ? C.red : sev === 'HIGH' ? C.orange : sev === 'MEDIUM' ? C.yellow || '#f5a523' : C.green
          const sevBg   = sev === 'CRITICAL' ? 'rgba(240,101,101,0.08)' : sev === 'HIGH' ? 'rgba(245,165,35,0.08)' : sev === 'MEDIUM' ? 'rgba(245,165,35,0.06)' : C.greenSoft
          const hasGNN  = analysisResult.avg_gnn_impact != null
          const hasMC   = analysisResult.var_95 != null && analysisResult.var_95 !== 0
          return (
            <div className="space-y-1.5">
              {/* Articles + alerts row */}
              <div className="rounded-lg px-2.5 py-2 border flex justify-between"
                style={{ background: C.greenSoft, borderColor: 'rgba(34,209,139,0.2)' }}>
                <div className="text-[10px]" style={{ color: C.muted }}>
                  Articles <span style={{ color: C.text }}>{analysisResult.articles_fetched ?? '—'}</span>
                </div>
                <div className="text-[10px]" style={{ color: C.muted }}>
                  Signals <span style={{ color: analysisResult.alerts_generated > 0 ? C.red : C.green }}>
                    {analysisResult.alerts_generated ?? 0}
                  </span>
                </div>
              </div>

              {/* GNN supply-chain impact */}
              {hasGNN && (
                <div className="rounded-lg px-2.5 py-2 border"
                  style={{ background: 'rgba(79,145,246,0.06)', borderColor: 'rgba(79,145,246,0.2)' }}>
                  <div className="text-[9px] font-black uppercase tracking-widest mb-1" style={{ color: C.blue }}>
                    GNN Supply-Chain
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span style={{ color: C.muted }}>Shock origin</span>
                    <span className="font-mono font-bold" style={{ color: C.text }}>
                      {analysisResult.shocked_ticker ?? '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] mt-0.5">
                    <span style={{ color: C.muted }}>Avg portfolio Δ</span>
                    <span className="font-bold" style={{ color: analysisResult.avg_gnn_impact < 0 ? C.red : C.green }}>
                      {analysisResult.avg_gnn_impact >= 0 ? '+' : ''}{fmt(analysisResult.avg_gnn_impact)}%
                    </span>
                  </div>
                </div>
              )}

              {/* Monte Carlo 48h risk */}
              {hasMC && (
                <div className="rounded-lg px-2.5 py-2 border"
                  style={{ background: sevBg, borderColor: `${sevClr}33` }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[9px] font-black uppercase tracking-widest" style={{ color: C.purple }}>
                      48h Monte Carlo
                    </span>
                    <span className="text-[8px] font-black px-1.5 py-0.5 rounded-full"
                      style={{ background: `${sevClr}22`, color: sevClr }}>
                      {sev}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span style={{ color: C.muted }}>VaR-95</span>
                    <span className="font-bold font-mono" style={{ color: C.red }}>
                      {analysisResult.var_95 >= 0 ? '+' : ''}{fmt(analysisResult.var_95)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] mt-0.5">
                    <span style={{ color: C.muted }}>CVaR-95</span>
                    <span className="font-bold font-mono" style={{ color: C.red }}>
                      {analysisResult.cvar_95 >= 0 ? '+' : ''}{fmt(analysisResult.cvar_95)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] mt-0.5">
                    <span style={{ color: C.muted }}>P(loss &gt; 2%)</span>
                    <span className="font-bold" style={{ color: sevClr }}>
                      {fmt(analysisResult.prob_loss)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })()}

        <button onClick={onAnalyze} disabled={analyzing}
          className="w-full py-2.5 rounded-lg text-[12px] font-black uppercase tracking-wide transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2 mt-auto"
          style={{ background: analyzing ? C.greenSoft : 'linear-gradient(135deg,#15803d,#16a34a)', color: '#fff' }}>
          {analyzing
            ? <><Radio size={12} className="animate-pulse" />Scanning…</>
            : <><Zap size={12} />Fetch &amp; Analyze News</>}
        </button>
      </div>
    </div>
  )
}

// ── Portfolio quick-view ──────────────────────────────────────────────────────
function PortfolioStrip({ portfolio, stockPrices, alerts }) {
  const holdings = portfolio?.holdings || []
  if (holdings.length === 0) return null

  return (
    <div className="flex items-center gap-1 px-6 py-2 border-b overflow-x-auto"
      style={{ background: C.panel, borderColor: C.border }}>
      <span className="text-[9px] font-black uppercase tracking-widest shrink-0 mr-2"
        style={{ color: C.muted }}>Portfolio</span>
      {holdings.slice(0, 10).map(h => {
        const p   = stockPrices?.[h.ticker]
        const chg = p?.change_percent
        const up  = chg >= 0
        const hasAlert = alerts.some(a => a.ticker === h.ticker)
        return (
          <div key={h.ticker} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border shrink-0"
            style={{ background: C.card, borderColor: hasAlert ? `${sevColor(alerts.find(a=>a.ticker===h.ticker)?.severity)}33` : C.borderDim }}>
            {hasAlert && <div className="w-1 h-1 rounded-full" style={{ background: C.red }} />}
            <span className="text-[10px] font-black font-mono" style={{ color: C.text }}>{h.ticker}</span>
            {p && <span className="text-[9px]" style={{ color: C.muted }}>${fmt(p.current_price ?? p.price)}</span>}
            {chg != null && (
              <span className="text-[9px] font-bold" style={{ color: up ? C.green : C.red }}>
                {up ? '+' : ''}{fmt(chg)}%
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ onCompanyClick }) {
  const [alerts,         setAlerts]         = useState([])
  const [articles,       setArticles]       = useState([])
  const [portfolio,      setPortfolio]      = useState({ holdings: [] })
  const [stats,          setStats]          = useState({})
  const [stockPrices,    setStockPrices]    = useState({})
  const [loading,        setLoading]        = useState(true)
  const [refreshing,     setRefreshing]     = useState(false)
  const [analyzing,      setAnalyzing]      = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [priceUpdated,   setPriceUpdated]   = useState(Date.now())
  const [showModal,      setShowModal]      = useState(false)
  const [selectedAlert,  setSelectedAlert]  = useState(null)

  const { isConnected, alerts: wsAlerts } = useWebSocket()

  useEffect(() => { loadAll() }, [])
  useEffect(() => {
    const t = setInterval(loadStockPrices, 15_000)
    return () => clearInterval(t)
  }, [])
  useEffect(() => {
    if (wsAlerts.length > 0) setAlerts(prev => [transformAlert(wsAlerts[0]), ...prev])
  }, [wsAlerts])

  async function loadAll() {
    setLoading(true)
    try {
      const portData = await getPortfolio().catch(() => ({ holdings: [] }))
      const tickers  = portData.holdings?.map(h => h.ticker) || []
      const [alertsData, articlesData, statsData] = await Promise.all([
        getAlerts().catch(() => ({ alerts: [] })),
        getArticles(20, tickers).catch(() => ({ articles: [] })),
        getStats().catch(() => ({})),
      ])
      setAlerts((alertsData.alerts || alertsData || []).map(transformAlert))
      setArticles(articlesData.articles || articlesData || [])
      setPortfolio(portData.holdings?.length ? transformPortfolio(portData) : { holdings: [] })
      setStats(statsData ? transformStats(statsData) : {})
      await loadStockPrices()
    } finally { setLoading(false) }
  }

  async function loadStockPrices(holdings = []) {
    try {
      // Always pass explicit tickers — avoids the slow "all holdings" DB scan
      const base = ['AAPL', 'NVDA', 'AMD', 'INTC', 'TSM', 'AMGN']
      const portTickers = (holdings.length ? holdings : portfolio?.holdings || [])
        .map(h => h.ticker).filter(Boolean)
      const tickers = [...new Set([...portTickers, ...base])].slice(0, 8).join(',')
      const d = await getStockPrices(tickers)
      if (d?.data) {
        // Only keep valid (non-zero) prices
        const valid = Object.fromEntries(
          Object.entries(d.data).filter(([, v]) => v?.is_valid !== false && (v?.current_price ?? v?.price ?? 0) > 0)
        )
        setStockPrices(valid)
        setPriceUpdated(Date.now())
      }
    } catch {}
  }

  async function handleAnalyze() {
    setAnalyzing(true)
    setAnalysisResult(null)
    try {
      const r = await fetchAndAnalyzeNews(10)
      setAnalysisResult(r)
      await loadAll()
    } catch (e) { console.error(e) }
    finally { setAnalyzing(false) }
  }

  const handleRefresh  = async () => { setRefreshing(true); await loadAll(); setRefreshing(false) }
  const handleExplain  = useCallback(a => { setSelectedAlert(a); setShowModal(true) }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: C.bg }}>
        <div className="text-center space-y-4">
          <div className="relative w-10 h-10 mx-auto">
            <div className="absolute inset-0 rounded-full border-2 border-t-transparent animate-spin"
              style={{ borderColor: `${C.blue} transparent transparent transparent` }} />
            <div className="absolute inset-2 rounded-full border border-b-transparent animate-spin"
              style={{ borderColor: `${C.purple} ${C.purple} ${C.purple} transparent`, animationDuration: '0.7s', animationDirection: 'reverse' }} />
          </div>
          <p className="text-[10px] font-mono tracking-widest uppercase" style={{ color: C.dim }}>
            Initializing Intel Platform
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: C.bg, fontFamily: "'Inter', system-ui, sans-serif" }}>
      <TopBar isConnected={isConnected} refreshing={refreshing} analyzing={analyzing}
        onRefresh={handleRefresh} onAnalyze={handleAnalyze} />

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <StockPricesSection prices={stockPrices} onRefresh={loadStockPrices}
          refreshing={refreshing} lastUpdated={priceUpdated} />

        {portfolio?.holdings?.length > 0 && (
          <PortfolioStrip portfolio={portfolio} stockPrices={stockPrices} alerts={alerts} />
        )}

        <StatsRow alerts={alerts} stats={stats} portfolio={portfolio} />

        {/* Middle row: Recent Alerts + Alert Trend */}
        <div className="flex gap-4 px-6 py-4 border-b" style={{ borderColor: C.border, minHeight: 280 }}>
          <div className="flex-1 min-w-0">
            <RecentAlertsPanel alerts={alerts} onExplain={handleExplain} />
          </div>
          <AlertTrendPanel alerts={alerts} />
        </div>

        {/* Bottom row: Recent News + AI Analysis */}
        <div className="flex gap-4 px-6 py-4" style={{ minHeight: 280 }}>
          <div className="flex-1 min-w-0">
            <RecentNewsPanel articles={articles} />
          </div>
          <AIAnalysisPanel analyzing={analyzing} analysisResult={analysisResult} onAnalyze={handleAnalyze} />
        </div>
      </div>

      {showModal && selectedAlert && (
        <ExplanationModal alert={selectedAlert} onClose={() => setShowModal(false)} />
      )}
    </div>
  )
}
