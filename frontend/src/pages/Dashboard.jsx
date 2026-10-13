import React, { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw, Search, Bell, TrendingUp, TrendingDown,
  ArrowUpRight, ArrowDownRight, Activity, Cpu, Globe,
  BookOpen, ExternalLink, Star, Brain, Radio, Zap, Shield, BarChart2
} from 'lucide-react'
import ExplanationModal from '../components/ExplanationModal'
import AlertCard, { fmt, sevColor } from '../components/AlertCard'
import QualityGrade from '../components/QualityGrade'
import TemporalMemory from '../components/TemporalMemory'
import AuditTrail from '../components/AuditTrail'
import ConvergenceZones from '../components/ConvergenceZones'
import KGContext from '../components/KGContext'
import WorldMonitorHeader from '../components/WorldMonitorHeader'
import WorldMap from '../components/WorldMap'
import CountryPanel from '../components/CountryPanel'
import PanelManager from '../components/PanelManager'
import ConfigurablePanel from '../components/ConfigurablePanel'
import {
  getAlerts, getPortfolio, getStats, fetchAndAnalyzeNews,
  getArticles, getStockPrices,
  getTemporalMemory, getKGContext, runIntelligencePipeline
} from '../services/api'
import { transformAlert, transformPortfolio, transformStats } from '../utils/dataTransform'
import { useWebSocket } from '../hooks/useWebSocket'

import { T as C } from '../theme'

// ── Helpers ───────────────────────────────────────────────────────────────────
// Terminal-style status chip (Global / Live / UTC / counts)
function Chip({ children, live, muted }) {
  return (
    <span className="inline-flex items-center gap-1.5 h-[22px] px-2 text-[10px] font-semibold whitespace-nowrap"
      style={{
        color: live ? '#86efac' : muted ? C.dim : C.text,
        background: live ? '#062317' : '#181818',
        border: `1px solid ${live ? '#14532d' : C.border}`,
      }}>
      {live && (
        <span className="w-1.5 h-1.5 rounded-full"
          style={{ background: '#4ade80', boxShadow: '0 0 6px #4ade80' }} />
      )}
      {children}
    </span>
  )
}

// ── Alert sparkline (7-day trend) ─────────────────────────────────────────────
function AlertTrendChart({ alerts }) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const base = [2, 5, 3, 8, 4, 6, alerts.length || 4]
  const max  = Math.max(...base, 1)
  const W = 320, H = 64
  const pl = 4, pr = 4, pt = 8, pb = 18

  const pts = base.map((v, i) => ({
    x: pl + (i / (base.length - 1)) * (W - pl - pr),
    y: pt + (1 - v / max) * (H - pt - pb),
  }))
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const area = `${line} L${pts.at(-1).x.toFixed(1)},${(H - pb).toFixed(1)} L${pts[0].x.toFixed(1)},${(H - pb).toFixed(1)} Z`

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible', maxHeight: 80 }}>
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={C.blue} stopOpacity="0.22" />
          <stop offset="100%" stopColor={C.blue} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#trendFill)" />
      <path d={line} fill="none" stroke={C.blue} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="2.2" fill={C.blue} />
      ))}
      {days.map((d, i) => (
        <text key={d} x={pts[i].x} y={H - 4} textAnchor="middle"
          style={{ fontSize: '8px', fill: C.dim, fontFamily: 'monospace' }}>
          {d}
        </text>
      ))}
    </svg>
  )
}



// ── Market Pulse hero panel (situation readout + alert trend) ───────────────
function MarketPulseHero({ alerts, stats, portfolio }) {

  const watched = portfolio?.holdings?.length ?? stats?.watchedCompanies ?? 0
  const impact  = stats?.marketImpactScore ?? 7.2
  const events  = stats?.eventsDetected ?? 0

  const rows = [
    { label: 'ACTIVE ALERTS', value: alerts.length,           color: C.orange },
    { label: 'WATCHED COS',   value: watched,                 color: C.blue },
    { label: 'IMPACT SCORE',  value: typeof impact === 'number' ? impact.toFixed(1) : impact, color: C.green },
    { label: 'EVENTS',        value: events,                  color: C.purple },
  ]

  const high = alerts.filter(a => ['HIGH','CRITICAL'].includes(a.severity?.toUpperCase())).length
  const med  = alerts.filter(a => ['MEDIUM','MODERATE'].includes(a.severity?.toUpperCase())).length

  return (
    <div className="px-3 py-3 flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-[4px]">
        {rows.map(r => (
          <div key={r.label} className="border px-3 py-2.5"
            style={{ background: C.card, borderColor: C.border }}>
            <div className="text-[20px] leading-none font-bold font-mono" style={{ color: C.text }}>
              {r.value}
            </div>
            <div className="text-[9px] font-bold mt-1.5 tracking-wider" style={{ color: r.color }}>
              {r.label}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-auto">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] font-bold tracking-wider" style={{ color: C.muted }}>ALERT TREND</span>
          <span className="text-[9px]" style={{ color: C.dim }}>7 days</span>
        </div>
        <AlertTrendChart alerts={alerts} />
        <div className="flex items-center justify-between mt-1">
          <div className="flex items-center gap-1">
            <span className="text-[13px] font-bold font-mono" style={{ color: high > 0 ? C.red : C.green }}>{high}</span>
            <span className="text-[8px]" style={{ color: C.dim }}>HIGH/CRIT</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[13px] font-bold font-mono" style={{ color: C.orange }}>{med}</span>
            <span className="text-[8px]" style={{ color: C.dim }}>MED</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[13px] font-bold font-mono" style={{ color: C.text }}>{alerts.length}</span>
            <span className="text-[8px]" style={{ color: C.dim }}>TOTAL</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Stock panels (one readout per ticker) ────────────────────────────────────
function StockPanel({ d, isPlaceholder }) {
  const price = d?.current_price ?? d?.price ?? 0
  const chg   = d?.change_percent ?? 0
  const up    = chg >= 0
  return (
    <div className="px-3 py-3 flex flex-col">
      <div className="text-[24px] leading-none font-bold font-mono" style={{ color: isPlaceholder ? C.dim : C.text }}>
        ${price === 0 && isPlaceholder ? '0.00' : fmt(price)}
      </div>
      <div className="text-[10px] font-bold mt-2" style={{ color: isPlaceholder ? C.dim : (up ? C.green : C.red) }}>
        {isPlaceholder ? '— (0.00%)' : `${up ? '+' : ''}${fmt(chg)}%`}
      </div>
      <p className="text-[9px] mt-1" style={{ color: C.dim }}>
        {isPlaceholder ? 'awaiting data' : (up ? 'trending up' : 'trending down')}
      </p>
    </div>
  )
}

function StockGrid({ prices }) {
  const entries = Object.entries(prices || {}).slice(0, 8)
  const list = entries.length
    ? entries
    : ['AAPL', 'NVDA', 'AMD', 'INTC', 'AMGN'].map(t => [t, null])
  return list.map(([ticker, d]) => (
    <StockPanel key={ticker} ticker={ticker} d={d} isPlaceholder={!d} />
  ))
}

// ── Portfolio panel ──────────────────────────────────────────────────────────
function PortfolioPanel({ portfolio, stockPrices, alerts }) {
  const holdings = portfolio?.holdings || []
  if (holdings.length === 0) return null
  const hasAlert = t => alerts.some(a => a.ticker === t)

  return (
    <div className="p-3 flex flex-wrap gap-1.5">
      {holdings.slice(0, 12).map(h => {
        const p   = stockPrices?.[h.ticker]
        const chg = p?.change_percent
        const up  = chg >= 0
        const flag = hasAlert(h.ticker)
        return (
          <div key={h.ticker}
            className="flex items-center gap-1.5 px-2 py-1 border"
            style={{
              background: C.card,
              borderColor: flag
                ? `${sevColor(alerts.find(a => a.ticker === h.ticker)?.severity)}44`
                : C.borderDim,
            }}>
            {flag && <span className="w-1 h-1 rounded-full" style={{ background: C.red }} />}
            <span className="text-[10px] font-bold font-mono" style={{ color: C.text }}>{h.ticker}</span>
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

// ── Recent alerts panel ──────────────────────────────────────────────────────
function RecentAlertsPanel({ alerts, onExplain }) {
  return (
    <div className="flex-1 overflow-y-auto min-h-0 h-full">
      {alerts.length === 0 && (
        <div className="flex flex-col items-center justify-center h-32 gap-2">
          <Shield size={18} style={{ color: C.dim }} />
          <span className="text-[11px]" style={{ color: C.dim }}>No alerts — market is calm</span>
        </div>
      )}
      {alerts.length > 0 && (
        <>
          <div className="grid grid-cols-[80px_1fr_60px_64px] px-3 py-2 border-b"
            style={{ borderColor: C.borderDim }}>
            {['Severity', 'Description', 'Impact', 'Time'].map(h => (
              <span key={h} className="text-[9px] font-bold" style={{ color: C.dim }}>{h}</span>
            ))}
          </div>
          {alerts.slice(0, 14).map((a, i) => (
            <AlertCard key={i} alert={a} onExplain={onExplain} />
          ))}
        </>
      )}
    </div>
  )
}

// ── Recent news panel ─────────────────────────────────────────────────────────
function RecentNewsPanel({ articles }) {
  return (
    <div className="flex-1 overflow-y-auto divide-y min-h-0 h-full" style={{ borderColor: C.borderDim }}>
      {articles.length === 0 && (
        <div className="flex items-center justify-center h-24">
          <span className="text-[11px]" style={{ color: C.dim }}>No recent articles</span>
        </div>
      )}
      {articles.slice(0, 6).map((a, i) => (
        <div key={i} className="px-3 py-2.5 transition-all"
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
              <span key={t} className="text-[8px] font-semibold px-1.5 py-0.5 border"
                style={{ background: C.blueSoft, color: C.blue, borderColor: `${C.blue}33` }}>
                {t}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── AI Pipeline panel ─────────────────────────────────────────────────────────
function AIAnalysisPanel({ analyzing, analysisResult, onAnalyze }) {
  const steps = [
    { label: 'News Monitor',      icon: Globe,     desc: 'Multi-source ingestion + SNR filter' },
    { label: 'FinBERT Classifier', icon: Cpu,       desc: 'Local NLP sentiment model' },
    { label: 'Quant Tools',        icon: BarChart2,  desc: '6 parallel quantitative tools' },
    { label: 'Alpha Scorer',       icon: Zap,        desc: 'Tool-first alpha + optional LLM' },
    { label: 'Convergence',        icon: Activity,   desc: 'Multi-source signal fusion' },
    { label: 'GNN Supply-Chain',   icon: Shield,     desc: 'Shock propagation graph' },
    { label: 'Monte Carlo 48h',    icon: Shield,     desc: 'Portfolio risk simulation' },
    { label: 'Audit & Quality',    icon: Brain,      desc: '5-dimension quality grading' },
  ]
  const doneCount = analyzing ? 4 : analysisResult ? 8 : 0

  return (
    <div className="flex-1 min-h-0 px-3 py-3 flex flex-col gap-3 overflow-y-auto">
      <p className="text-[11px] leading-relaxed" style={{ color: C.muted }}>
        13-node LangGraph pipeline with tool-first architecture and fault-tolerant execution.
      </p>

      {/* Steps */}
      <div className="space-y-1">
        {steps.map((s, i) => {
          const done   = i < doneCount
          const active = analyzing && i === Math.floor(doneCount)
          const Icon   = s.icon
          return (
            <div key={i} className="flex items-center gap-2 px-2 py-1.5 border"
              style={{
                background: done ? C.greenSoft : active ? C.purpleSoft : 'transparent',
                borderColor: done ? `${C.green}33` : active ? `${C.purple}33` : 'transparent',
              }}>
              <div className="w-4 h-4 rounded flex items-center justify-center shrink-0"
                style={{ background: done ? C.greenSoft : active ? C.purpleSoft : C.card }}>
                {done
                  ? <span className="text-[8px]" style={{ color: C.green }}>✓</span>
                  : active
                    ? <Radio size={8} className="animate-pulse" style={{ color: C.purple }} />
                    : <Icon size={8} style={{ color: C.dim }} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[9px] font-semibold truncate"
                  style={{ color: done ? C.green : active ? C.purple : C.muted }}>
                  {s.label}
                </div>
              </div>
              {active && (
                <div className="flex gap-0.5">
                  {[0, 1, 2].map(j => (
                    <div key={j} className="w-0.5 h-0.5 rounded-full animate-bounce"
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
        const sevClr  = sev === 'CRITICAL' ? C.red : sev === 'HIGH' ? C.orange : sev === 'MEDIUM' ? C.orange : C.green
        const sevBg2  = sev === 'CRITICAL' ? C.redSoft : sev === 'HIGH' ? C.orangeSoft : sev === 'MEDIUM' ? C.orangeSoft : C.greenSoft
        const hasGNN  = analysisResult.avg_gnn_impact != null
        const hasMC   = analysisResult.var_95 != null && analysisResult.var_95 !== 0
        return (
          <div className="space-y-1.5">
            {/* Articles + alerts row */}
            <div className="px-2 py-1.5 border flex justify-between"
              style={{ background: C.greenSoft, borderColor: `${C.green}33` }}>
              <div className="text-[9px]" style={{ color: C.muted }}>
                Articles <span className="font-bold" style={{ color: C.text }}>{analysisResult.articles_fetched ?? '—'}</span>
              </div>
              <div className="text-[9px]" style={{ color: C.muted }}>
                Signals <span className="font-bold" style={{ color: analysisResult.alerts_generated > 0 ? C.red : C.green }}>
                  {analysisResult.alerts_generated ?? 0}
                </span>
              </div>
            </div>

            {/* GNN supply-chain impact */}
            {hasGNN && (
              <div className="px-2 py-1.5 border"
                style={{ background: C.blueSoft, borderColor: `${C.blue}33` }}>
                <div className="text-[8px] font-semibold mb-1" style={{ color: C.blue }}>
                  GNN Supply-Chain
                </div>
                <div className="flex justify-between text-[9px]">
                  <span style={{ color: C.muted }}>Shock origin</span>
                  <span className="font-mono font-bold" style={{ color: C.text }}>
                    {analysisResult.shocked_ticker ?? '—'}
                  </span>
                </div>
                <div className="flex justify-between text-[9px] mt-0.5">
                  <span style={{ color: C.muted }}>Avg portfolio Δ</span>
                  <span className="font-bold" style={{ color: analysisResult.avg_gnn_impact < 0 ? C.red : C.green }}>
                    {analysisResult.avg_gnn_impact >= 0 ? '+' : ''}{fmt(analysisResult.avg_gnn_impact)}%
                  </span>
                </div>
              </div>
            )}

            {/* Monte Carlo 48h risk */}
            {hasMC && (
              <div className="px-2 py-1.5 border"
                style={{ background: sevBg2, borderColor: `${sevClr}44` }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[8px] font-semibold" style={{ color: C.purple }}>
                    48h Monte Carlo
                  </span>
                  <span className="text-[8px] font-semibold px-1.5 py-0.5 border-full"
                    style={{ background: `${sevClr}22`, color: sevClr }}>
                    {sev}
                  </span>
                </div>
                <div className="flex justify-between text-[9px]">
                  <span style={{ color: C.muted }}>VaR-95</span>
                  <span className="font-bold font-mono" style={{ color: C.red }}>
                    {analysisResult.var_95 >= 0 ? '+' : ''}{fmt(analysisResult.var_95)}%
                  </span>
                </div>
                <div className="flex justify-between text-[9px] mt-0.5">
                  <span style={{ color: C.muted }}>CVaR-95</span>
                  <span className="font-bold font-mono" style={{ color: C.red }}>
                    {analysisResult.cvar_95 >= 0 ? '+' : ''}{fmt(analysisResult.cvar_95)}%
                  </span>
                </div>
              </div>
            )}

            {/* Phase 2-5: Tool-First Intelligence Summary */}
            {analysisResult.quality_grade && (
              <div className="px-2 py-1.5 border"
                style={{ background: C.purpleSoft, borderColor: `${C.purple}33` }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[8px] font-semibold" style={{ color: C.purple }}>
                    Tool-First Intel
                  </span>
                  <span className="text-[10px] font-semibold font-mono" style={{ color: C.purple }}>
                    {analysisResult.quality_grade}
                  </span>
                </div>
                {analysisResult.alpha_signal && analysisResult.alpha_signal !== 'NEUTRAL' && (
                  <div className="flex justify-between text-[9px] mt-1">
                    <span style={{ color: C.muted }}>Alpha Signal</span>
                    <span className="font-bold" style={{ color: analysisResult.alpha_signal.includes('BEAR') ? C.red : C.green }}>
                      {analysisResult.alpha_signal}
                    </span>
                  </div>
                )}
                {analysisResult.convergence_zones?.length > 0 && (
                  <div className="flex justify-between text-[9px] mt-0.5">
                    <span style={{ color: C.muted }}>Convergence</span>
                    <span className="font-bold" style={{ color: C.orange }}>
                      {analysisResult.convergence_zones.length} zone{analysisResult.convergence_zones.length > 1 ? 's' : ''}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })()}

      <button onClick={onAnalyze} disabled={analyzing}
        className="w-full py-2.5 mt-auto text-[11px] font-bold tracking-wide uppercase transition-all active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
        style={{ background: analyzing ? C.greenSoft : '#15803d', color: '#ecfdf5', border: `1px solid ${analyzing ? `${C.green}66` : '#4ade80'}` }}>
        {analyzing
          ? <><Radio size={11} className="animate-pulse" />Running 13-Node Pipeline…</>
          : <><Zap size={11} />Run Full Intelligence Pipeline</>}
      </button>
    </div>
  )
}

// ── Intelligence Layer (quality / audit / convergence / per-ticker) ─────────
function IntelligenceLayer({ pipelineResult, portfolio, temporalData, kgData }) {
  return (
    <div className="p-2 flex flex-col gap-2">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
        <QualityGrade
          qualityGrade={pipelineResult?.quality_grade}
          qualityScores={pipelineResult?.quality_scores}
        />
        <AuditTrail auditSummary={pipelineResult?.audit_summary} />
        <ConvergenceZones convergenceZones={pipelineResult?.convergence_zones} />
      </div>

      {portfolio?.holdings?.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
          {portfolio.holdings.slice(0, 6).map(h => {
            const t = h.ticker
            return (
              <React.Fragment key={t}>
                <TemporalMemory
                  temporalContext={temporalData[t] || pipelineResult?.temporal_context?.[t] || {}}
                  ticker={t}
                />
                <KGContext
                  kgContext={kgData[t] || pipelineResult?.kg_context?.[t] || {}}
                  ticker={t}
                />
              </React.Fragment>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ onCompanyClick }) {
  const [country, setCountry] = useState(null)   // { iso2, name } from a map click
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
  const [pipelineResult, setPipelineResult] = useState(null)
  const [temporalData,   setTemporalData]   = useState({})
  const [kgData,         setKgData]         = useState({})
  
  // World Monitor state
  const [currentVariant, setCurrentVariant] = useState('world')
  const [theme, setTheme] = useState('dark')
  const [activeLayers, setActiveLayers] = useState(['stocks', 'news', 'geopolitical'])
  const [timeRange, setTimeRange] = useState('24h')
  
  // Panel management state
  const [panels, setPanels] = useState([
    { id: 'market_pulse', type: 'market_pulse', span: 2, active: true },
    { id: 'alerts', type: 'alerts', span: 2, active: true },
    { id: 'news', type: 'news', span: 2, active: true },
    { id: 'portfolio', type: 'portfolio', span: 1, active: true },
    { id: 'stocks', type: 'stocks', span: 1, active: true },
    { id: 'intelligence', type: 'intelligence', span: 3, active: true },
  ])

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
    } catch { /* keep the last good prices */ }
  }

  async function handleAnalyze() {
    setAnalyzing(true)
    setAnalysisResult(null)
    setPipelineResult(null)
    try {
      // Run both the legacy pipeline AND the full LangGraph pipeline in parallel
      const tickers = portfolio?.holdings?.map(h => h.ticker).filter(Boolean) || ['AAPL', 'MSFT', 'NVDA']
      const [legacyResult, pipelineRes] = await Promise.all([
        fetchAndAnalyzeNews(10).catch(() => null),
        runIntelligencePipeline(tickers).catch(() => null),
      ])
      // Merge legacy results into pipeline result
      const merged = { ...legacyResult, ...pipelineRes }
      setAnalysisResult(legacyResult)
      setPipelineResult(merged)
      // Fetch per-ticker temporal memory and KG context for all portfolio tickers
      const temporalResults = {}
      const kgResults = {}
      await Promise.all(tickers.slice(0, 6).map(async (t) => {
        const [temp, kg] = await Promise.all([
          getTemporalMemory(t).catch(() => null),
          getKGContext(t).catch(() => null),
        ])
        if (temp) temporalResults[t] = temp
        if (kg) kgResults[t] = kg
      }))
      setTemporalData(temporalResults)
      setKgData(kgResults)
      await loadAll()
    } catch (e) { console.error(e) }
    finally { setAnalyzing(false) }
  }

  const handleRefresh  = async () => { setRefreshing(true); await loadAll(); setRefreshing(false) }
  const handleExplain  = useCallback(a => { setSelectedAlert(a); setShowModal(true) }, [])
  
  // World Monitor handlers
  const handleVariantChange = (variant) => {
    setCurrentVariant(variant)
    // Could trigger different data views based on variant
  }
  
  const handleThemeToggle = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
    localStorage.setItem('mp_theme', newTheme)
  }
  
  const handleLayerToggle = (layerId) => {
    setActiveLayers(prev => 
      prev.includes(layerId) 
        ? prev.filter(l => l !== layerId)
        : [...prev, layerId]
    )
  }
  
  const handleTimeRangeChange = (range) => {
    setTimeRange(range)
    // Could trigger data filtering based on time range
  }
  
  const handleRegionChange = () => {
    // Could trigger region-specific data loading
  }
  
  // Panel management handlers
  const handleAddPanel = (newPanel) => {
    setPanels(prev => [...prev, newPanel])
  }
  
  const handleRemovePanel = (panelId) => {
    setPanels(prev => prev.filter(p => p.id !== panelId))
  }
  
  const handleTogglePanel = (panelId, isActive) => {
    setPanels(prev => prev.map(p => 
      p.id === panelId ? { ...p, active: isActive } : p
    ))
  }
  
  const handleSpanChange = (panelId, newSpan) => {
    setPanels(prev => prev.map(p => 
      p.id === panelId ? { ...p, span: newSpan } : p
    ))
  }

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
          <p className="text-[10px] font-mono" style={{ color: C.muted }}>
            Initializing Intel Platform
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: C.bg }}>
      {/* World Monitor Header */}
      <WorldMonitorHeader 
        isConnected={isConnected} 
        refreshing={refreshing} 
        onRefresh={handleRefresh}
        currentVariant={currentVariant}
        onVariantChange={handleVariantChange}
        theme={theme}
        onThemeToggle={handleThemeToggle}
      />

      {/* World Map */}
      <WorldMap 
        onRegionChange={handleRegionChange}
        onLayerToggle={handleLayerToggle}
        activeLayers={activeLayers}
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
        onCountrySelect={(iso2, name) => setCountry({ iso2, name })}
        selectedCountry={country?.iso2}
      />

      <CountryPanel
        iso2={country?.iso2}
        name={country?.name}
        onClose={() => setCountry(null)}
        onCompanyClick={onCompanyClick}
      />

      {/* Panel Manager */}
      <PanelManager 
        panels={panels}
        onAddPanel={handleAddPanel}
        onRemovePanel={handleRemovePanel}
        onTogglePanel={handleTogglePanel}
        onSpanChange={handleSpanChange}
      />

      {/* Scrollable ops-center dashboard */}
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 grid-flow-dense auto-rows-[minmax(168px,auto)] gap-[4px] p-[4px]">
          {panels.filter(p => p.active).map(panel => {
            switch (panel.type) {
              case 'market_pulse':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={Activity}
                    title="Market Pulse"
                    color={C.green}
                    kicker="Live situation: prices, risk and detected events across the watched universe"
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                    right={
                      <>
                        <span className="text-[9px]" style={{ color: C.dim }}>
                          Prices {Math.floor((Date.now() - priceUpdated) / 1000) < 60 
                            ? `${Math.floor((Date.now() - priceUpdated) / 1000)}s` 
                            : `${Math.floor((Date.now() - priceUpdated) / 60000)}m`} ago
                        </span>
                        <button 
                          onClick={() => loadStockPrices()} 
                          disabled={refreshing}
                          className="w-6 h-6 flex items-center justify-center"
                          style={{ background: C.card, border: `1px solid ${C.border}` }}
                        >
                          <RefreshCw size={11} style={{ color: C.muted }} className={refreshing ? 'animate-spin' : ''} />
                        </button>
                      </>
                    }
                  >
                    <MarketPulseHero
                      alerts={alerts} stats={stats} portfolio={portfolio}
                    />
                  </ConfigurablePanel>
                )
              case 'alerts':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={Bell}
                    title="Active Alerts"
                    color={C.orange}
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                    right={<Chip muted>{alerts.length} open</Chip>}
                  >
                    <RecentAlertsPanel alerts={alerts} onExplain={handleExplain} />
                  </ConfigurablePanel>
                )
              case 'news':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={BookOpen}
                    title="Recent News"
                    color={C.cyan}
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                    right={articles.length > 0 ? <Chip>{articles.length} articles</Chip> : null}
                  >
                    <RecentNewsPanel articles={articles} />
                  </ConfigurablePanel>
                )
              case 'portfolio':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={Star}
                    title="Portfolio"
                    color={C.yellow}
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                    right={<Chip>{portfolio?.holdings?.length || 0} holdings</Chip>}
                  >
                    <PortfolioPanel portfolio={portfolio} stockPrices={stockPrices} alerts={alerts} />
                  </ConfigurablePanel>
                )
              case 'stocks':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={TrendingUp}
                    title="Stock Prices"
                    color={C.green}
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                  >
                    <StockGrid prices={stockPrices} />
                  </ConfigurablePanel>
                )
              case 'intelligence':
                return (
                  <ConfigurablePanel
                    key={panel.id}
                    panelId={panel.id}
                    icon={Brain}
                    title="Intelligence"
                    color={C.purple}
                    defaultSpan={panel.span}
                    onSpanChange={handleSpanChange}
                    onRemove={handleRemovePanel}
                  >
                    <div className="p-2 flex flex-col gap-2">
                      <AIAnalysisPanel analyzing={analyzing} analysisResult={analysisResult} onAnalyze={handleAnalyze} />
                      <IntelligenceLayer
                        pipelineResult={pipelineResult}
                        portfolio={portfolio}
                        temporalData={temporalData}
                        kgData={kgData}
                      />
                    </div>
                  </ConfigurablePanel>
                )
              default:
                return null
            }
          })}
        </div>
      </div>

      {showModal && selectedAlert && (
        <ExplanationModal alert={selectedAlert} onClose={() => setShowModal(false)} />
      )}
    </div>
  )
}