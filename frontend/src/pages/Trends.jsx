import React, { useState, useEffect } from 'react'
import { TrendingUp, Globe, Activity, BarChart2, RefreshCw, Zap, PieChart } from 'lucide-react'
import { getRiskScores, getMacroData, getMarketOverview, getSignals, getCorrelations, getFactorRotation } from '../services/api'
import SectorHeatmap from '../components/SectorHeatmap'

const REGIME_COLORS = {
  bull:     { bg: 'bg-green-500/10',  border: 'border-green-500/30',  text: 'text-green-400',  dot: 'bg-green-500' },
  bear:     { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-400',    dot: 'bg-red-500' },
  volatile: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  sideways: { bg: 'bg-blue-500/10',   border: 'border-blue-500/30',   text: 'text-blue-400',   dot: 'bg-blue-500' },
}

const riskColor = (s) => s >= 70 ? 'bg-red-500' : s >= 50 ? 'bg-orange-500' : s >= 30 ? 'bg-yellow-500' : 'bg-green-500'
const riskText  = (s) => s >= 70 ? 'text-red-400' : s >= 50 ? 'text-orange-400' : s >= 30 ? 'text-yellow-400' : 'text-green-400'

export default function MarketTrends() {
  const [overview,     setOverview]     = useState(null)
  const [riskScores,   setRiskScores]   = useState(null)
  const [macro,        setMacro]        = useState(null)
  const [signals,      setSignals]      = useState(null)
  const [correlations, setCorrelations] = useState(null)
  const [factorRotation, setFactorRotation] = useState(null)
  const [alphaScores, setAlphaScores] = useState({})
  const [loading,      setLoading]      = useState(true)
  const [refreshing,   setRefreshing]   = useState(false)

  async function loadAll() {
    const [o, r, m, s, c, f] = await Promise.all([
      getMarketOverview(), getRiskScores(), getMacroData(), getSignals(), getCorrelations(), getFactorRotation(),
    ])
    setOverview(o); setRiskScores(r); setMacro(m); setSignals(s); setCorrelations(c); setFactorRotation(f)
  }

  useEffect(() => {
    setLoading(true)
    loadAll().finally(() => setLoading(false))
    const t = setInterval(loadAll, 60000)
    return () => clearInterval(t)
  }, [])

  const handleRefresh = async () => { setRefreshing(true); await loadAll(); setRefreshing(false) }

  const regime    = overview?.regime || 'sideways'
  const rc        = REGIME_COLORS[regime] || REGIME_COLORS.sideways
  const topRisks  = (riskScores?.scores || []).sort((a, b) => b.score - a.score).slice(0, 12)
  const macroItems = macro ? [
    { label: 'Fed Funds Rate',   value: macro.fed_funds_rate,  suffix: '%' },
    { label: '10Y Treasury',     value: macro.treasury_10y,    suffix: '%' },
    { label: '2Y Treasury',      value: macro.treasury_2y,     suffix: '%' },
    { label: 'CPI',              value: macro.cpi,             suffix: '%' },
    { label: 'Core CPI',         value: macro.core_cpi,        suffix: '%' },
    { label: 'Unemployment',     value: macro.unemployment,    suffix: '%' },
    { label: 'VIX',              value: macro.vix },
    { label: 'Gold ($/oz)',      value: macro.gold,            prefix: '$' },
    { label: 'Crude Oil',        value: macro.crude_oil,       prefix: '$' },
    { label: 'Natural Gas',      value: macro.natural_gas,     prefix: '$' },
    { label: 'Copper',           value: macro.copper,          prefix: '$' },
    { label: 'Wheat',            value: macro.wheat,           prefix: '$' },
  ].filter(i => i.value != null) : []

  const sectorEtfs = macro?.sector_etfs ? Object.entries(macro.sector_etfs) : []
  const signalList = signals?.signals || []
  const corrList   = correlations?.correlations || []

  return (
    <div className="flex-1 bg-darkBg">
      <div className="sticky top-0 z-40 bg-darkBg/95 backdrop-blur border-b border-darkBorder">
        <div className="px-8 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-black text-primary uppercase tracking-tighter italic">Intelligence Hub</h1>
            <p className="text-secondary text-sm">Market regime · Macro indicators · Geopolitical risk · Signal correlations</p>
          </div>
          <button onClick={handleRefresh} disabled={refreshing} className="p-2 hover:bg-darkBorder rounded-lg disabled:opacity-50">
            <RefreshCw size={20} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
        </div>
      ) : (
        <div className="p-8 space-y-8">

          {/* Row 1: 4 KPI cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className={`rounded-2xl p-5 border ${rc.bg} ${rc.border}`}>
              <div className="flex items-center gap-2 mb-2">
                <Activity size={16} className={rc.text} />
                <span className="text-xs font-black uppercase tracking-widest text-gray-400">Market Regime</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full animate-pulse ${rc.dot}`} />
                <span className={`text-2xl font-black uppercase ${rc.text}`}>{regime}</span>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">
                Conf: {overview?.confidence != null ? `${(overview.confidence * 100).toFixed(0)}%` : '—'}
              </p>
            </div>
            {[
              { label: 'VIX (Fear Index)', val: overview?.vix?.toFixed(2), sub: overview?.vix >= 30 ? 'High Fear' : overview?.vix >= 20 ? 'Elevated' : 'Calm', color: overview?.vix >= 30 ? 'text-red-400' : overview?.vix >= 20 ? 'text-yellow-400' : 'text-green-400' },
              { label: 'SPY 5-Day Return', val: overview?.spy_5d_return != null ? `${(overview.spy_5d_return * 100).toFixed(2)}%` : '—', sub: 'S&P 500 proxy', color: (overview?.spy_5d_return || 0) >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Fed Funds Rate',   val: macro?.fed_funds_rate != null ? `${macro.fed_funds_rate.toFixed(2)}%` : '—', sub: 'Current policy rate', color: 'text-blue-400' },
            ].map(c => (
              <div key={c.label} className="glass-card rounded-2xl p-5">
                <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">{c.label}</div>
                <div className={`text-2xl font-mono font-black ${c.color}`}>{c.val ?? '—'}</div>
                <div className="text-[10px] text-gray-500 mt-1">{c.sub}</div>
              </div>
            ))}
          </div>

          {/* Row 2: CII + Macro */}
          <div className="grid grid-cols-2 gap-6">
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Globe size={18} className="text-orange-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">Country Instability Index (CII)</h2>
              </div>
              {topRisks.length > 0 ? (
                <div className="space-y-3">
                  {topRisks.map(c => (
                    <div key={c.country_code} className="flex items-center gap-3">
                      <span className="text-[10px] font-mono text-gray-400 w-8">{c.country_code}</span>
                      <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${riskColor(c.score)}`} style={{ width: `${c.score}%` }} />
                      </div>
                      <span className={`text-[10px] font-mono w-8 text-right ${riskText(c.score)}`}>{Math.round(c.score)}</span>
                      <span className="text-[10px] text-gray-600 w-28 truncate">{c.country_name || c.name || ''}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600 text-xs">
                  <Globe size={32} className="mx-auto mb-2 opacity-20" />Risk data loading...
                </div>
              )}
            </div>

            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 size={18} className="text-purple-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">Macro Indicators</h2>
              </div>
              {macroItems.length > 0 ? (
                <div className="grid grid-cols-2 gap-1">
                  {macroItems.map(item => (
                    <div key={item.label} className="flex justify-between items-center py-1.5 px-2 rounded-lg hover:bg-white/5">
                      <span className="text-[10px] text-gray-500">{item.label}</span>
                      <span className="text-[11px] font-mono text-gray-200">
                        {item.prefix || ''}{typeof item.value === 'number' ? item.value.toFixed(2) : item.value}{item.suffix || ''}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600 text-xs">
                  <BarChart2 size={32} className="mx-auto mb-2 opacity-20" />FRED + commodity data loading...
                </div>
              )}
            </div>
          </div>

          {/* Row 3: Sector ETFs */}
          {sectorEtfs.length > 0 && (
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={18} className="text-blue-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">Sector ETF Performance</h2>
              </div>
              <div className="grid grid-cols-6 gap-3">
                {sectorEtfs.map(([sector, data]) => {
                  const chg = data?.change_pct ?? data?.change_percent ?? 0
                  return (
                    <div key={sector} className="bg-white/5 rounded-xl p-3 text-center hover:bg-white/10 transition-all">
                      <div className="text-[10px] text-gray-500 uppercase mb-1">{sector.replace('_', ' ')}</div>
                      <div className="text-xs font-mono text-gray-300">{data?.ticker || ''}</div>
                      <div className={`text-[11px] font-bold mt-1 ${chg >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {chg >= 0 ? '+' : ''}{Number(chg).toFixed(2)}%
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Row 4: Signals + Correlations */}
          <div className="grid grid-cols-2 gap-6">
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap size={18} className="text-yellow-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">Active Signals</h2>
              </div>
              {signalList.length > 0 ? (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {signalList.slice(0, 10).map((s, i) => (
                    <div key={i} className="flex items-start gap-3 p-2 rounded-lg bg-white/5 hover:bg-white/10">
                      <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${s.severity === 'high' ? 'bg-red-500' : s.severity === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'}`} />
                      <div>
                        <p className="text-[11px] text-gray-300 leading-tight">{s.title || s.description || ''}</p>
                        <p className="text-[9px] text-gray-600 mt-0.5">{s.country || s.source || ''}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600 text-xs">No active signals</div>
              )}
            </div>

            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={18} className="text-pink-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">Correlation Alerts</h2>
              </div>
              {corrList.length > 0 ? (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {corrList.slice(0, 8).map((c, i) => (
                    <div key={i} className="p-2 rounded-lg bg-white/5 hover:bg-white/10">
                      <p className="text-[11px] text-gray-300">{c.type || c.correlation_type}</p>
                      <p className="text-[9px] text-gray-500 mt-0.5">{c.description || c.detail || ''}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600 text-xs">No correlation anomalies detected</div>
              )}
            </div>
          </div>

          {/* Row 5: Factor Rotation */}
          {factorRotation && (
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <PieChart size={18} className="text-cyan-400" />
                <h2 className="text-sm font-black uppercase tracking-widest text-gray-300">
                  Factor Rotation — <span className="text-cyan-300">{factorRotation.regime?.toUpperCase()}</span>
                </h2>
              </div>
              <div className="grid grid-cols-5 gap-3">
                {Object.entries(factorRotation.recommended_allocation || {}).map(([factor, alloc]) => {
                  const isPrimary = factor === factorRotation.primary_factor
                  const isAvoid = factor === factorRotation.avoid_factor
                  return (
                    <div key={factor} className={`rounded-xl p-3 text-center border ${isPrimary ? 'border-green-500/30' : isAvoid ? 'border-red-500/30' : 'border-white/10'}`}
                      style={{ background: isPrimary ? 'rgba(34,209,139,0.08)' : isAvoid ? 'rgba(240,101,101,0.08)' : 'rgba(255,255,255,0.03)' }}>
                      <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: isPrimary ? '#22d18b' : isAvoid ? '#f06565' : '#94a3b8' }}>
                        {factor}
                      </div>
                      <div className="text-lg font-black mt-1 font-mono" style={{ color: isPrimary ? '#22d18b' : '#c8d6ee' }}>
                        {(alloc * 100).toFixed(0)}%
                      </div>
                      {isPrimary && <div className="text-[8px] mt-1 px-1.5 py-0.5 rounded-full bg-green-500/20 text-green-400">PRIMARY</div>}
                      {isAvoid && <div className="text-[8px] mt-1 px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400">AVOID</div>}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Row 6: Sector Heatmap */}
          <SectorHeatmap alphaScores={alphaScores} />

        </div>
      )}
    </div>
  )
}
