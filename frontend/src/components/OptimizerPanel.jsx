import React, { useState } from 'react'
import { BarChart2, RefreshCw, Plus, Trash2, PieChart } from 'lucide-react'

const C = {
  bg: '#0b1221', card: '#131f35', border: '#1c2f4a', text: '#dde8f5',
  muted: '#5d7a9a', dim: '#243650', blue: '#4f91f6', green: '#22d18b',
  red: '#f06565', orange: '#f5a523', purple: '#a07cf5',
}

export default function OptimizerPanel({ onOptimize, result = null, loading = false }) {
  const [holdings, setHoldings] = useState([
    { ticker: 'AAPL', value: 25000 },
    { ticker: 'NVDA', value: 25000 },
    { ticker: 'MSFT', value: 25000 },
    { ticker: 'GOOGL', value: 25000 },
  ])
  const [newTicker, setNewTicker] = useState('')
  const [newValue, setNewValue] = useState(10000)

  function addHolding() {
    if (newTicker.trim()) {
      setHoldings([...holdings, { ticker: newTicker.trim().toUpperCase(), value: newValue }])
      setNewTicker('')
    }
  }

  function removeHolding(index) {
    setHoldings(holdings.filter((_, i) => i !== index))
  }

  function updateHolding(index, field, val) {
    const updated = [...holdings]
    updated[index] = { ...updated[index], [field]: val }
    setHoldings(updated)
  }

  function handleOptimize() {
    if (onOptimize) onOptimize(holdings)
  }

  const totalValue = holdings.reduce((sum, h) => sum + h.value, 0)

  return (
    <div className="flex gap-6 h-full">
      <div className="flex-1 rounded-xl p-4 border overflow-y-auto" style={{ background: C.card, borderColor: C.border }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <PieChart size={16} style={{ color: C.blue }} />
            <h3 className="text-sm font-bold" style={{ color: C.text }}>Portfolio Holdings</h3>
          </div>
          <span className="text-xs" style={{ color: C.muted }}>
            Total: ${totalValue.toLocaleString()}
          </span>
        </div>

        <div className="space-y-2 mb-4">
          {holdings.map((h, i) => (
            <div key={i} className="flex items-center gap-2 p-2 rounded-lg" style={{ background: C.bg }}>
              <input value={h.ticker} onChange={e => updateHolding(i, 'ticker', e.target.value.toUpperCase())}
                className="w-20 px-2 py-1 rounded text-xs font-mono font-bold uppercase outline-none"
                style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }} />
              <input value={h.value} onChange={e => updateHolding(i, 'value', Number(e.target.value))}
                type="number" className="flex-1 px-2 py-1 rounded text-xs font-mono outline-none"
                style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }} />
              <span className="text-xs w-16 text-right font-mono" style={{ color: C.muted }}>
                {totalValue > 0 ? `${(h.value / totalValue * 100).toFixed(1)}%` : ''}
              </span>
              <button onClick={() => removeHolding(i)} className="p-1 rounded hover:bg-white/5">
                <Trash2 size={14} style={{ color: C.red }} />
              </button>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2 p-2 rounded-lg" style={{ background: C.bg }}>
          <input value={newTicker} onChange={e => setNewTicker(e.target.value.toUpperCase())}
            placeholder="TICKER" maxLength={5}
            className="w-20 px-2 py-1 rounded text-xs font-mono font-bold uppercase outline-none"
            style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }} />
          <input value={newValue} onChange={e => setNewValue(Number(e.target.value))}
            type="number" placeholder="Value" className="flex-1 px-2 py-1 rounded text-xs font-mono outline-none"
            style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }} />
          <button onClick={addHolding} className="p-1.5 rounded-lg" style={{ background: C.blue }}>
            <Plus size={14} style={{ color: '#fff' }} />
          </button>
        </div>

        <button onClick={handleOptimize} disabled={loading || holdings.length < 2}
          className="w-full mt-4 py-3 rounded-xl text-sm font-bold transition-all active:scale-95 disabled:opacity-40"
          style={{ background: 'linear-gradient(135deg,#2563eb,#7c3aed)', color: '#fff' }}>
          {loading ? 'Optimizing...' : 'Optimize Portfolio'}
        </button>
      </div>

      <div className="w-96 rounded-xl p-4 border overflow-y-auto" style={{ background: C.card, borderColor: C.border }}>
        <h3 className="text-sm font-bold mb-4" style={{ color: C.text }}>Optimization Results</h3>

        {!result && (
          <div className="flex flex-col items-center justify-center h-48 gap-2">
            <BarChart2 size={32} style={{ color: C.dim }} />
            <p className="text-xs" style={{ color: C.dim }}>Add holdings and optimize</p>
          </div>
        )}

        {result?.optimized_weights && (
          <>
            <div className="space-y-2 mb-4">
              {Object.entries(result.optimized_weights).map(([ticker, weight]) => {
                const current = holdings.find(h => h.ticker === ticker)
                const currentWeight = current ? current.value / totalValue : 0
                const diff = weight - currentWeight
                return (
                  <div key={ticker} className="flex items-center justify-between p-2 rounded-lg" style={{ background: C.bg }}>
                    <span className="text-xs font-bold font-mono" style={{ color: C.text }}>{ticker}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs" style={{ color: C.muted }}>{(currentWeight * 100).toFixed(1)}%</span>
                      <span className="text-xs font-mono" style={{ color: C.blue }}>→</span>
                      <span className="text-xs font-bold" style={{ color: weight > currentWeight ? C.green : C.red }}>
                        {(weight * 100).toFixed(1)}%
                      </span>
                      <span className="text-xs font-mono" style={{ color: diff > 0 ? C.green : diff < 0 ? C.red : C.muted }}>
                        {diff > 0 ? '+' : ''}{(diff * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>

            {result.metrics && (
              <div className="space-y-2 p-3 rounded-lg" style={{ background: `${C.bg}` }}>
                <div className="flex justify-between text-xs">
                  <span style={{ color: C.muted }}>Expected Return</span>
                  <span className="font-bold" style={{ color: (result.metrics.expected_return || 0) > 0 ? C.green : C.red }}>
                    {result.metrics.expected_return || 0}%
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span style={{ color: C.muted }}>Risk (Std Dev)</span>
                  <span className="font-bold" style={{ color: C.orange }}>{result.metrics.expected_risk || 0}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span style={{ color: C.muted }}>Sharpe Ratio</span>
                  <span className="font-bold" style={{ color: (result.metrics.sharpe_ratio || 0) > 1 ? C.green : C.orange }}>
                    {result.metrics.sharpe_ratio || 0}
                  </span>
                </div>
              </div>
            )}

            {result.suggested_trades?.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-bold mb-2" style={{ color: C.text }}>Suggested Trades</h4>
                <div className="space-y-1">
                  {result.suggested_trades.slice(0, 5).map((trade, i) => (
                    <div key={i} className="flex justify-between text-xs p-1.5 rounded" style={{ background: C.bg }}>
                      <span className="font-mono font-bold" style={{ color: C.text }}>{trade.ticker}</span>
                      <span className="font-bold" style={{ color: trade.action === 'BUY' ? C.green : C.red }}>
                        {trade.action} {(trade.adjustment * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
