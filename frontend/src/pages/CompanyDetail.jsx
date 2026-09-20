import React, { useState, useEffect, useRef } from 'react'
import { ArrowLeft, TrendingUp, TrendingDown, Activity, Users, BarChart2, Globe, RefreshCw, Download } from 'lucide-react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import SignalTimeline from '../components/SignalTimeline'
import {
  getInsiderTrades, getShortInterest, getRetailSentiment,
  getTechnicalAnalysis, getFundamentals, getAlphaScore,
} from '../services/api'

const C = {
  bg: '#0a0a0a', panel: '#101010', card: '#141414', cardHover: '#1a1a1a',
  border: '#2a2a2a', borderDim: '#1c1c1c', text: '#f5f5f5', muted: '#9ca3af',
  dim: '#52525b', blue: '#4ade80', green: '#4ade80', red: '#f87171',
  orange: '#fbbf24', purple: '#c084fc',
}

export default function CompanyDetail({ ticker: initialTicker, onBack }) {
  const [ticker, setTicker] = useState(initialTicker || '')
  const [inputTicker, setInputTicker] = useState(initialTicker || '')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState({})
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState(null)
  const reportRef = useRef(null)

  // Ported from the old Search page, which exported a price-only report. This
  // view carries the actual intelligence, so it is the one worth exporting.
  async function downloadPDF() {
    if (!reportRef.current || !ticker) return
    setExporting(true)
    setExportError(null)
    try {
      const canvas = await html2canvas(reportRef.current, {
        scale: 2, backgroundColor: C.bg, logging: false, useCORS: true,
      })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const props = pdf.getImageProperties(imgData)
      const width = pdf.internal.pageSize.getWidth()
      pdf.addImage(imgData, 'PNG', 0, 0, width, (props.height * width) / props.width)
      pdf.save(`${ticker}_Intelligence_Report.pdf`)
    } catch (err) {
      // An alert() here would block the page; surface it inline instead.
      console.error('PDF generation failed:', err)
      setExportError('PDF export failed')
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    if (initialTicker) {
      setTicker(initialTicker)
      setInputTicker(initialTicker)
      fetchAll(initialTicker)
    }
  }, [initialTicker])

  async function fetchAll(t) {
    setLoading(true)
    const [alpha, insider, short, sentiment, tech, fund] = await Promise.all([
      getAlphaScore(t), getInsiderTrades(t), getShortInterest(t),
      getRetailSentiment(t), getTechnicalAnalysis(t), getFundamentals(t),
    ])
    setData({ alpha, insider, short, sentiment, tech, fund })
    setLoading(false)
  }

  function handleSearch(e) {
    e.preventDefault()
    if (inputTicker.trim()) {
      setTicker(inputTicker.trim().toUpperCase())
      fetchAll(inputTicker.trim().toUpperCase())
    }
  }

  const alpha = data.alpha || {}
  const signal = alpha.signal || 'NEUTRAL'
  const signalColor = signal === 'STRONG_BUY' || signal === 'BUY' ? C.green
    : signal === 'STRONG_SELL' || signal === 'SELL' ? C.red : C.orange

  return (
    <div className="h-full flex flex-col" style={{ background: C.bg }}>
      <div className="flex items-center gap-4 px-6 py-4 border-b shrink-0" style={{ borderColor: C.border }}>
        {onBack && (
          <button onClick={onBack} className="p-2 rounded-lg hover:bg-white/5">
            <ArrowLeft size={18} style={{ color: C.text }} />
          </button>
        )}
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1 max-w-xs">
            <input value={inputTicker} onChange={e => setInputTicker(e.target.value.toUpperCase())}
              placeholder="Enter ticker (e.g. AAPL)"
              className="w-full px-4 py-2 rounded-lg text-sm outline-none font-mono font-bold"
              style={{ background: C.card, border: `1px solid ${C.border}`, color: C.text }}
            />
          </div>
          <button type="submit" disabled={loading}
            className="px-4 py-2 rounded-lg text-xs font-bold transition-all"
            style={{ background: C.blue, color: '#fff' }}>
            {loading ? 'Loading...' : 'Analyze'}
          </button>
        </form>
        <button onClick={() => fetchAll(ticker)} disabled={loading}
          className="p-2 rounded-lg hover:bg-white/5">
          <RefreshCw size={16} style={{ color: C.muted }} className={loading ? 'animate-spin' : ''} />
        </button>
        {ticker && (
          <button onClick={downloadPDF} disabled={exporting}
            title={exportError || 'Export this report as PDF'}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-bold hover:bg-white/5"
            style={{ border: `1px solid ${exportError ? C.red : C.border}`,
                     color: exportError ? C.red : C.muted }}>
            <Download size={14} />
            {exporting ? 'Exporting…' : exportError ? 'Retry PDF' : 'PDF'}
          </button>
        )}
      </div>

      <div ref={reportRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {!ticker && (
          <div className="flex items-center justify-center h-64">
            <p className="text-sm" style={{ color: C.muted }}>Search for a ticker to begin</p>
          </div>
        )}

        {ticker && (
          <>
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-semibold font-mono" style={{ color: C.text }}>{ticker}</h1>
              <div className="px-4 py-2 rounded-none" style={{ background: `${signalColor}15`, border: `1px solid ${signalColor}30` }}>
                <span className="text-lg font-semibold" style={{ color: signalColor }}>{signal}</span>
                <span className="ml-3 text-sm" style={{ color: C.muted }}>
                  {alpha.signal === 'INSUFFICIENT_DATA' ? (
                    <span title={alpha.signal_note} style={{ color: C.orange }}>
                      Insufficient evidence ({alpha.coverage?.live_count ?? 0}/{alpha.coverage?.total_count ?? 0} sources)
                    </span>
                  ) : (
                    <>Score: {alpha.alpha_score != null ? `${alpha.alpha_score >= 0 ? '+' : ''}${alpha.alpha_score}` : '--'}</>
                  )}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <div className="flex items-center gap-2 mb-3">
                  <Users size={14} style={{ color: C.purple }} />
                  <span className="text-xs font-bold" style={{ color: C.muted }}>Insider Trades</span>
                </div>
                <div className="text-2xl font-semibold" style={{ color: alpha?.components?.insider?.score > 0 ? C.green : C.red }}>
                  {alpha?.components?.insider?.score != null ? `${alpha.components.insider.score >= 0 ? '+' : ''}${alpha.components.insider.score}` : '--'}
                </div>
                <div className="text-xs mt-1" style={{ color: C.muted }}>
                  {data.insider?.trades?.length || 0} filings
                </div>
              </div>
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <div className="flex items-center gap-2 mb-3">
                  <BarChart2 size={14} style={{ color: C.orange }} />
                  <span className="text-xs font-bold" style={{ color: C.muted }}>Short Interest</span>
                </div>
                <div className="text-2xl font-semibold" style={{ color: alpha?.components?.short_interest?.score > 0 ? C.green : C.red }}>
                  {alpha?.components?.short_interest?.score != null ? `${alpha.components.short_interest.score >= 0 ? '+' : ''}${alpha.components.short_interest.score}` : '--'}
                </div>
              </div>
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <div className="flex items-center gap-2 mb-3">
                  <Activity size={14} style={{ color: C.blue }} />
                  <span className="text-xs font-bold" style={{ color: C.muted }}>Technical</span>
                </div>
                <div className="text-2xl font-semibold" style={{ color: alpha?.components?.technical?.score > 0 ? C.green : C.red }}>
                  {alpha?.components?.technical?.score != null ? `${alpha.components.technical.score >= 0 ? '+' : ''}${alpha.components.technical.score}` : '--'}
                </div>
              </div>
            </div>

            {data.sentiment && (
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <h3 className="text-sm font-bold mb-3" style={{ color: C.text }}>Retail Sentiment</h3>
                <div className="flex gap-6">
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Bullish</span>
                    <div className="text-lg font-bold" style={{ color: C.green }}>{data.sentiment.bullish_pct || 0}%</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Bearish</span>
                    <div className="text-lg font-bold" style={{ color: C.red }}>{data.sentiment.bearish_pct || 0}%</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Mentions</span>
                    <div className="text-lg font-bold" style={{ color: C.text }}>{data.sentiment.total_mentions || 0}</div>
                  </div>
                </div>
              </div>
            )}

            {data.tech && (
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <h3 className="text-sm font-bold mb-3" style={{ color: C.text }}>Technical Indicators</h3>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Price</span>
                    <div className="text-lg font-bold font-mono" style={{ color: C.text }}>${data.tech.price || '--'}</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>RSI</span>
                    <div className="text-lg font-bold" style={{ color: (data.tech.rsi || 50) > 70 ? C.red : (data.tech.rsi || 50) < 30 ? C.green : C.text }}>
                      {data.tech.rsi || '--'}
                    </div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Signals</span>
                    <div className="text-sm font-bold" style={{ color: C.text }}>
                      {(data.tech.signals || []).slice(0, 3).join(', ') || 'None'}
                    </div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Score</span>
                    <div className="text-lg font-bold" style={{ color: (alpha?.components?.technical?.score || 0) > 0 ? C.green : C.red }}>
                      {alpha?.components?.technical?.score != null ? `${alpha.components.technical.score >= 0 ? '+' : ''}${alpha.components.technical.score}` : '--'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {data.fund && (
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <h3 className="text-sm font-bold mb-3" style={{ color: C.text }}>Fundamentals</h3>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>P/E</span>
                    <div className="text-lg font-bold font-mono" style={{ color: C.text }}>{data.fund.pe_ratio || '--'}</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Forward P/E</span>
                    <div className="text-lg font-bold font-mono" style={{ color: C.text }}>{data.fund.forward_pe || '--'}</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>EPS</span>
                    <div className="text-lg font-bold font-mono" style={{ color: C.text }}>${data.fund.eps || '--'}</div>
                  </div>
                  <div>
                    <span className="text-xs" style={{ color: C.muted }}>Revenue Growth</span>
                    <div className="text-lg font-bold" style={{ color: (data.fund.revenue_growth || 0) > 0 ? C.green : C.red }}>
                      {data.fund.revenue_growth != null ? `${(data.fund.revenue_growth * 100).toFixed(1)}%` : '--'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {alpha?.active_signals && alpha.active_signals.length > 0 && (
              <SignalTimeline signals={alpha.active_signals} ticker={ticker} />
            )}

            {data.insider?.trades?.length > 0 && (
              <div className="rounded-none p-4 border" style={{ background: C.card, borderColor: C.border }}>
                <h3 className="text-sm font-bold mb-3" style={{ color: C.text }}>Recent Insider Filings</h3>
                <div className="space-y-2">
                  {data.insider.trades.slice(0, 5).map((t, i) => (
                    <div key={i} className="flex justify-between items-center py-2 px-3 rounded-none" style={{ background: `${C.bg}` }}>
                      <span className="text-xs font-mono" style={{ color: C.muted }}>{t.filing_date || t.trade_date}</span>
                      <span className="text-xs" style={{ color: C.text }}>{t.insider_name}</span>
                      <span className="text-xs font-bold" style={{ color: t.transaction_type === 'BUY' || t.transaction_type === 'PURCHASE' ? C.green : C.red }}>
                        {t.transaction_type}
                      </span>
                      <span className="text-xs font-mono" style={{ color: C.muted }}>{t.shares ? `${(t.shares / 1000).toFixed(0)}K` : '--'}</span>
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
