import React, { useState, useEffect } from 'react'
import { Globe, TrendingUp, AlertTriangle, Activity, BarChart2 } from 'lucide-react'
import { getRiskScores, getMacroData, getMarketOverview } from '../services/api'

const REGIME_COLORS = {
  bull: 'text-green-400 bg-green-500/10 border-green-500/30',
  bear: 'text-red-400 bg-red-500/10 border-red-500/30',
  volatile: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  sideways: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
}

const RISK_COLOR = (score) => {
  if (score >= 70) return 'bg-red-500'
  if (score >= 50) return 'bg-orange-500'
  if (score >= 30) return 'bg-yellow-500'
  return 'bg-green-500'
}

export default function IntelligencePanel() {
  const [riskScores, setRiskScores] = useState(null)
  const [macro, setMacro] = useState(null)
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      const [r, m, o] = await Promise.all([getRiskScores(), getMacroData(), getMarketOverview()])
      setRiskScores(r)
      setMacro(m)
      setOverview(o)
      setLoading(false)
    }
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [])

  if (loading) return (
    <div className="glass-card rounded-2xl p-6 animate-pulse">
      <div className="h-4 bg-white/5 rounded w-1/3 mb-4"></div>
      <div className="h-32 bg-white/5 rounded"></div>
    </div>
  )

  const regime = overview?.regime || 'sideways'
  const regimeClass = REGIME_COLORS[regime] || REGIME_COLORS.sideways
  const topRisks = (riskScores?.scores || []).sort((a, b) => b.score - a.score).slice(0, 6)

  return (
    <div className="space-y-4">
      {/* Market Regime */}
      {overview && (
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={16} className="text-blue-400" />
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-400">Market Regime</h3>
          </div>
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-black uppercase ${regimeClass}`}>
            <span className="w-2 h-2 rounded-full bg-current animate-pulse"></span>
            {regime}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {overview.vix != null && (
              <div className="bg-white/5 rounded-lg p-2 text-center">
                <div className="text-[10px] text-gray-500 uppercase">VIX</div>
                <div className="text-lg font-mono text-primary">{overview.vix?.toFixed(1)}</div>
              </div>
            )}
            {overview.spy_5d_return != null && (
              <div className="bg-white/5 rounded-lg p-2 text-center">
                <div className="text-[10px] text-gray-500 uppercase">SPY 5D</div>
                <div className={`text-lg font-mono ${overview.spy_5d_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {(overview.spy_5d_return * 100).toFixed(2)}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Country Risk Scores */}
      {topRisks.length > 0 && (
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Globe size={16} className="text-orange-400" />
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-400">Country Risk (CII)</h3>
          </div>
          <div className="space-y-2">
            {topRisks.map((c) => (
              <div key={c.country_code} className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-gray-400 w-6">{c.country_code}</span>
                <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${RISK_COLOR(c.score)}`}
                    style={{ width: `${c.score}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-gray-300 w-6 text-right">{Math.round(c.score)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Macro Indicators */}
      {macro && (
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 size={16} className="text-purple-400" />
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-400">Macro Indicators</h3>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Fed Funds Rate', value: macro.fed_funds_rate, suffix: '%' },
              { label: '10Y Treasury', value: macro.treasury_10y, suffix: '%' },
              { label: 'CPI YoY', value: macro.cpi, suffix: '%' },
              { label: 'Unemployment', value: macro.unemployment, suffix: '%' },
              { label: 'Gold', value: macro.gold, prefix: '$' },
              { label: 'Crude Oil', value: macro.crude_oil, prefix: '$' },
            ].filter(i => i.value != null).map((item) => (
              <div key={item.label} className="flex justify-between items-center py-1 border-b border-white/5">
                <span className="text-[11px] text-gray-500">{item.label}</span>
                <span className="text-[11px] font-mono text-gray-200">
                  {item.prefix || ''}{typeof item.value === 'number' ? item.value.toFixed(2) : item.value}{item.suffix || ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
