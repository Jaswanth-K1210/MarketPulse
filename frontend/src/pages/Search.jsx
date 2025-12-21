import React, { useState, useRef } from 'react'
import { Search, Loader, ArrowRight, Download } from 'lucide-react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

export default function CompanySearch() {
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)
    const [showReport, setShowReport] = useState(false)
    const [downloading, setDownloading] = useState(false)
    const reportRef = useRef(null)

    const downloadPDF = async () => {
        if (!reportRef.current) return
        setDownloading(true)
        try {
            const canvas = await html2canvas(reportRef.current, {
                scale: 2,
                backgroundColor: '#0F1419', // Match theme for capture
                logging: false,
                useCORS: true
            })
            const imgData = canvas.toDataURL('image/png')
            const pdf = new jsPDF('p', 'mm', 'a4')
            const imgProps = pdf.getImageProperties(imgData)
            const pdfWidth = pdf.internal.pageSize.getWidth()
            const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width

            pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight)
            pdf.save(`${result.ticker}_Intelligence_Report.pdf`)
        } catch (err) {
            console.error('PDF generation failed:', err)
            alert('Failed to generate PDF. Please try again.')
        } finally {
            setDownloading(false)
        }
    }

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!query) return

        setLoading(true)
        setError(null)
        setResult(null)

        try {
            // Use existing stock-prices endpoint for now, theoretically could be expanded
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/stock-prices?tickers=${query}`)
            const data = await res.json()

            if (data.status === 'success' && data.count > 0) {
                // The backend returns a dict: { "AAPL": { ... }, "NVDA": { ... } }
                // We must look up the EXACT ticker the user queried
                const targetTicker = query.toUpperCase();
                const stockData = data.data[targetTicker];

                if (stockData) {
                    setResult({ ticker: targetTicker, ...stockData })
                } else {
                    // Fallback: If exact match not found (weird case), try the first key
                    const firstKey = Object.keys(data.data)[0];
                    setResult({ ticker: firstKey, ...data.data[firstKey] })
                }
            } else {
                setError('Company/Ticker not found.')
            }
        } catch (err) {
            console.error(err)
            setError('Search failed. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="p-8 max-w-4xl mx-auto">
            <div className="text-center mb-12">
                <h2 className="text-3xl font-black text-primary uppercase tracking-tighter italic">Company Intelligence Search</h2>
                <p className="text-secondary font-medium uppercase text-xs tracking-widest opacity-60">Deep dive into any public company's metrics and news.</p>
            </div>

            <div className="relative mb-12">
                <form onSubmit={handleSearch}>
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="text-gray-500" />
                    </div>
                    <input
                        type="text"
                        className="w-full bg-darkBg border border-darkBorder rounded-2xl py-4 pl-12 pr-4 text-xl focus:outline-none focus:border-blue-500 transition-colors shadow-lg"
                        placeholder="Enter Ticker Symbol (e.g. AAPL, NVDA)..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value.toUpperCase())}
                    />
                    <button
                        type="submit"
                        disabled={loading || !query}
                        className="absolute inset-y-2 right-2 bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-xl font-medium transition-colors disabled:opacity-50"
                    >
                        {loading ? <Loader className="animate-spin" /> : 'Analyze'}
                    </button>
                </form>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-center">
                    {error}
                </div>
            )}

            {result && (
                <div className="bg-darkBg border border-darkBorder rounded-2xl p-8 shadow-2xl animate-fade-in">
                    <div className="flex items-start justify-between border-b border-darkBorder pb-6 mb-6">
                        <div>
                            <div className="text-[10px] text-secondary font-black uppercase tracking-widest mb-1">Stock Ticker</div>
                            <h1 className="text-5xl font-black text-primary italic tracking-tighter uppercase">{result.ticker}</h1>
                        </div>
                        <div className="text-right">
                            <div className="text-4xl font-mono font-bold">${result.current_price?.toFixed(2)}</div>
                            <div className={`text-lg font-medium ${result.change_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {result.change_percent >= 0 ? '+' : ''}{result.change_percent?.toFixed(2)}%
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <div className="bg-dark/40 p-5 rounded-2xl border border-white/5">
                            <div className="text-secondary text-[10px] font-black uppercase tracking-widest mb-2">Volume</div>
                            <div className="text-2xl font-black text-primary font-mono">{result.volume?.toLocaleString() || '---'}</div>
                        </div>
                        <div className="bg-dark/40 p-5 rounded-2xl border border-white/5">
                            <div className="text-secondary text-[10px] font-black uppercase tracking-widest mb-2">Market Cap</div>
                            <div className="text-2xl font-black text-primary font-mono">$2.4T (Est)</div>
                        </div>
                        <div className="bg-dark/40 p-5 rounded-2xl border border-white/5">
                            <div className="text-secondary text-[10px] font-black uppercase tracking-widest mb-2">P/E Ratio</div>
                            <div className="text-2xl font-black text-primary font-mono">32.4x</div>
                        </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
                        <h3 className="font-bold mb-2 flex items-center gap-2">
                            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                            AI Insight
                        </h3>
                        <p className="text-gray-300 leading-relaxed">
                            Based on recent signals, {result.ticker} is showing strong momentum aligned with the broader market sector.
                            News sentiment is currently positive due to recent product announcements.
                            (Demo Intelligence)
                        </p>
                    </div>

                    <div className="mt-6 text-center">
                        <button
                            onClick={() => setShowReport(true)}
                            className="text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center justify-center gap-1 mx-auto"
                        >
                            View Full Report <ArrowRight size={14} />
                        </button>
                    </div>
                </div>
            )}

            {/* FULL REPORT MODAL */}
            {showReport && result && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
                    <div className="bg-darkBg border border-darkBorder rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl relative">
                        <div ref={reportRef} className="bg-darkBg">
                            <div className="sticky top-0 bg-darkBg/95 backdrop-blur border-b border-darkBorder p-6 flex justify-between items-center z-10">
                                <div>
                                    <h2 className="text-2xl font-bold flex items-center gap-2">
                                        <span className="text-gradient">{result.ticker} Intelligence Report</span>
                                        <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full uppercase tracking-tighter border border-blue-500/30">Institutional</span>
                                    </h2>
                                    <p className="text-xs text-gray-400 font-mono mt-1 tracking-widest leading-none">ID: MP-{Math.random().toString(36).substr(2, 9).toUpperCase()}</p>
                                </div>
                                <button onClick={() => setShowReport(false)} className="bg-dark hover:bg-gray-800 p-2 rounded-lg transition-colors">
                                    <span className="text-2xl leading-none font-light">&times;</span>
                                </button>
                            </div>

                            <div className="p-8 space-y-10">
                                {/* Executive Summary */}
                                <section>
                                    <h3 className="text-sm font-black mb-4 text-blue-400 uppercase tracking-widest flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" /> Executive Summary
                                    </h3>
                                    <p className="text-gray-300 leading-relaxed text-sm lg:text-base">
                                        {result.ticker} is currently exhibiting <strong>{result.change_percent >= 0 ? 'bullish' : 'bearish'}</strong> behavior
                                        aligned with volatility in the {result.market_cap !== '---' && result.market_cap.includes('T') ? 'Mega-Cap' : 'Tech'} sector.
                                        Analyst consensus suggests a HOLD/BUY rating based on recent volume accumulation of {result.volume?.toLocaleString() || 'significant levels'}.
                                        Key resistance levels are being tested, and recent news flow indicates positive sentiment regarding upcoming earnings.
                                    </p>
                                </section>

                                {/* Key Performance Indicators */}
                                <section>
                                    <h3 className="text-sm font-black mb-4 text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 bg-purple-500 rounded-full" /> Quantitative Metrics
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="bg-dark/40 p-4 rounded-xl border border-white/5 hover:border-blue-500/30 transition-colors">
                                            <div className="text-secondary text-[10px] uppercase font-black tracking-widest mb-1">RSI (14)</div>
                                            <div className="text-xl font-mono text-primary font-black">54.2</div>
                                        </div>
                                        <div className="bg-dark/40 p-4 rounded-xl border border-white/5 hover:border-blue-500/30 transition-colors">
                                            <div className="text-secondary text-[10px] uppercase font-black tracking-widest mb-1">Vol (Beta)</div>
                                            <div className="text-xl font-mono text-primary font-black">1.42</div>
                                        </div>
                                        <div className="bg-dark/40 p-4 rounded-xl border border-white/5 hover:border-blue-500/30 transition-colors">
                                            <div className="text-secondary text-[10px] uppercase font-black tracking-widest mb-1">Sentiment</div>
                                            <div className="text-xl font-mono text-green-400 font-black">8.5</div>
                                        </div>
                                        <div className="bg-dark/40 p-4 rounded-xl border border-white/5 hover:border-blue-500/30 transition-colors">
                                            <div className="text-secondary text-[10px] uppercase font-black tracking-widest mb-1">Earnings</div>
                                            <div className="text-xl font-mono text-primary font-black">24d</div>
                                        </div>
                                    </div>
                                </section>

                                {/* Deep Dive Assessment */}
                                <section>
                                    <h3 className="text-sm font-black mb-4 text-green-400 uppercase tracking-widest flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Strategic Assessment
                                    </h3>
                                    <div className="bg-dark/30 rounded-2xl p-6 border border-white/5 space-y-4">
                                        <div className="flex gap-4">
                                            <div className="w-6 h-6 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center shrink-0 text-sm font-bold">1</div>
                                            <p className="text-gray-400 text-sm">Operational efficiency has improved by noticeable margins quarter-over-quarter despite macro headwinds.</p>
                                        </div>
                                        <div className="flex gap-4">
                                            <div className="w-6 h-6 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center shrink-0 text-sm font-bold">2</div>
                                            <p className="text-gray-400 text-sm">Institutional ownership remains steady, signaling long-term conviction from smart money participants.</p>
                                        </div>
                                        <div className="flex gap-4">
                                            <div className="w-6 h-6 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center shrink-0 text-sm font-bold">3</div>
                                            <p className="text-gray-400 text-sm">Strategic pivot into AI-driven verticals is expected to yield significant margin expansion in late FY25.</p>
                                        </div>
                                    </div>
                                </section>

                                <div className="text-[10px] text-gray-600 font-mono text-center pt-8 border-t border-white/5 uppercase">
                                    Confidential • MarketPulse Intelligence Framework v4.2 • {new Date().toLocaleTimeString()}
                                </div>
                            </div>
                        </div>

                        {/* Sticky Action Footer */}
                        <div className="p-6 bg-darkBg border-t border-darkBorder flex justify-between items-center sticky bottom-0 z-20">
                            <button onClick={() => setShowReport(false)} className="px-6 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all text-sm font-bold">Dismiss</button>
                            <button
                                onClick={downloadPDF}
                                disabled={downloading}
                                className={`flex items-center gap-3 px-8 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-black shadow-xl shadow-blue-600/20 active:scale-95 transition-all ${downloading ? 'opacity-50 cursor-wait' : ''}`}
                            >
                                {downloading ? <Loader className="animate-spin" size={18} /> : <Download size={18} />}
                                {downloading ? 'Preparing PDF...' : 'Download Intelligence Report'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
