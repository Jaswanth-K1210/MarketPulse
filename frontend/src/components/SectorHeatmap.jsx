import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

const C = {
  bg: '#0b1221', card: '#131f35', border: '#1c2f4a', text: '#dde8f5',
  muted: '#5d7a9a', green: '#22d18b', red: '#f06565',
}

const SECTORS = [
  { name: 'Technology', ticker: 'XLK', companies: ['AAPL', 'MSFT', 'NVDA', 'AMD', 'INTC'] },
  { name: 'Semiconductors', ticker: 'SMH', companies: ['TSM', 'NVDA', 'AMD', 'INTC', 'ASML'] },
  { name: 'Healthcare', ticker: 'XLV', companies: ['JNJ', 'PFE', 'MRK', 'ABBV', 'AMGN'] },
  { name: 'Financial', ticker: 'XLF', companies: ['JPM', 'GS', 'BAC', 'V', 'MA'] },
  { name: 'Consumer Cyclical', ticker: 'XLY', companies: ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'] },
  { name: 'Energy', ticker: 'XLE', companies: ['XOM', 'CVX', 'COP', 'SLB', 'EOG'] },
  { name: 'Defense', ticker: 'XAR', companies: ['RTX', 'LMT', 'NOC', 'GD', 'BA'] },
  { name: 'Utilities', ticker: 'XLU', companies: ['NEE', 'DUK', 'SO', 'D', 'AEP'] },
]

export default function SectorHeatmap({ alphaScores = {} }) {
  const maxScore = Math.max(...Object.values(alphaScores), 5)

  function getIntensity(score) {
    if (!score || score === 0) return 0.5
    return Math.min(1, Math.abs(score) / maxScore)
  }

  function getColor(score) {
    if (!score || score === 0) return '#1a2740'
    if (score > 0) {
      const intensity = getIntensity(score)
      return `rgba(34, 209, 139, ${0.15 + intensity * 0.6})`
    }
    const intensity = getIntensity(score)
    return `rgba(240, 101, 101, ${0.15 + intensity * 0.6})`
  }

  function getTextColor(score) {
    if (!score || score === 0) return C.muted
    return score > 0 ? C.green : C.red
  }

  return (
    <div className="rounded-xl p-4 border" style={{ background: C.card, borderColor: C.border }}>
      <h3 className="text-sm font-bold mb-4" style={{ color: C.text }}>Sector Heatmap</h3>
      <div className="grid grid-cols-4 gap-3">
        {SECTORS.map(sector => {
          const sectorScores = sector.companies.map(t => alphaScores[t] || 0)
          const avgScore = sectorScores.reduce((a, b) => a + b, 0) / sectorScores.length || 0

          return (
            <div key={sector.name}
              className="rounded-xl p-3 border transition-all cursor-pointer hover:scale-105"
              style={{ background: getColor(avgScore), borderColor: avgScore > 0 ? 'rgba(34,209,139,0.2)' : avgScore < 0 ? 'rgba(240,101,101,0.2)' : C.border }}>
              <div className="text-xs font-bold" style={{ color: C.text }}>{sector.name}</div>
              <div className="text-[10px] mt-0.5" style={{ color: C.muted }}>{sector.ticker}</div>
              <div className="text-lg font-bold mt-2" style={{ color: getTextColor(avgScore) }}>
                {avgScore > 0 ? '+' : ''}{avgScore.toFixed(1)}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {sector.companies.slice(0, 3).map(t => (
                  <span key={t} className="text-[8px] font-mono px-1 py-0.5 rounded"
                    style={{ background: `${C.bg}`, color: C.muted }}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
