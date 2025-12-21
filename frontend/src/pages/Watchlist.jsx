
import React, { useState, useEffect } from 'react'
import { Plus, Trash2, ArrowUpRight, ArrowDownRight, RefreshCw } from 'lucide-react'

export default function Watchlist() {
    const [watchlist, setWatchlist] = useState([])
    const [loading, setLoading] = useState(true)
    const [tickerInput, setTickerInput] = useState('')
    const [adding, setAdding] = useState(false)

    const fetchWatchlist = async () => {
        try {
            setLoading(true)
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/watchlist`)
            const data = await res.json()
            if (data.status === 'success') {
                setWatchlist(data.data)
            }
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchWatchlist()
        const interval = setInterval(fetchWatchlist, 30000) // Refresh every 30s
        return () => clearInterval(interval)
    }, [])

    const handleAdd = async (e) => {
        e.preventDefault()
        if (!tickerInput) return

        setAdding(true)
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/watchlist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker: tickerInput })
            })
            if (res.ok) {
                setTickerInput('')
                fetchWatchlist()
            }
        } catch (err) {
            console.error(err)
        } finally {
            setAdding(false)
        }
    }

    const handleRemove = async (ticker) => {
        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/watchlist/${ticker}`, {
                method: 'DELETE'
            })
            if (res.ok) {
                fetchWatchlist()
            }
        } catch (err) {
            console.error(err)
        }
    }

    return (
        <div className="p-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-2xl font-bold">Watchlist</h2>
                    <p className="text-gray-400">Track your favorite assets</p>
                </div>
                <button onClick={fetchWatchlist} className="p-2 hover:bg-darkBorder rounded-lg">
                    <RefreshCw size={20} />
                </button>
            </div>

            <div className="bg-darkBg border border-darkBorder rounded-xl p-6 mb-8">
                <form onSubmit={handleAdd} className="flex gap-4">
                    <input
                        type="text"
                        value={tickerInput}
                        onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                        placeholder="Enter Ticker (e.g. TSLA, MSFT)"
                        className="flex-1 bg-dark border border-darkBorder rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500"
                    />
                    <button
                        type="submit"
                        disabled={adding || !tickerInput}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
                    >
                        <Plus size={18} />
                        Add to Watchlist
                    </button>
                </form>
            </div>

            {loading && watchlist.length === 0 ? (
                <div className="text-center py-20 text-gray-500">Loading watchlist...</div>
            ) : watchlist.length === 0 ? (
                <div className="text-center py-20 bg-darkBg border border-darkBorder rounded-xl border-dashed">
                    <p className="text-gray-400">Your watchlist is empty.</p>
                    <p className="text-sm text-gray-500 mt-2">Add tickers above to start tracking.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {watchlist.map((item) => (
                        <div key={item.ticker} className="bg-darkBg border border-darkBorder rounded-xl p-6 hover:border-gray-600 transition-colors">
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <h3 className="text-xl font-bold">{item.ticker}</h3>
                                    <p className="text-xs text-gray-400">{item.company || 'Stock'}</p>
                                </div>
                                <button
                                    onClick={() => handleRemove(item.ticker)}
                                    className="text-gray-500 hover:text-red-400 p-1"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>

                            <div className="flex items-end justify-between">
                                <div>
                                    <div className="text-2xl font-mono font-bold">
                                        ${item.current_price?.toFixed(2) || '---'}
                                    </div>
                                    {item.change_percent !== undefined && (
                                        <div className={`flex items-center gap-1 text-sm font-medium mt-1 ${item.change_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {item.change_percent >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                                            {Math.abs(item.change_percent).toFixed(2)}%
                                        </div>
                                    )}
                                </div>
                                {/* Mini chart placeholder */}
                                <div className="w-24 h-12 bg-dark/50 rounded flex items-center justify-center text-xs text-gray-600">
                                    CHART
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
