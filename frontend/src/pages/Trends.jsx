
import React, { useState, useEffect } from 'react'
import { TrendingUp, ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react'

export default function MarketTrends() {
    const [trends, setTrends] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Determine trends from portfolio or watchlist
        const fetchTrends = async () => {
            setLoading(true)
            try {
                // Fetch "market" data - simply using stock prices of major indices or user watchlist as proxy
                // Since we don't have a dedicated trends endpoint, we'll derive it from watchlist/search
                // This is a "simulated" trends page based on real data points available
                const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/watchlist`)
                const data = await res.json()

                if (data.status === 'success') {
                    setTrends(data.data)
                }
            } catch (err) {
                console.error(err)
            } finally {
                setLoading(false)
            }
        }

        fetchTrends()
    }, [])

    return (
        <div className="p-8">
            <div className="mb-8">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                    <TrendingUp className="text-blue-500" /> Market Trends
                </h2>
                <p className="text-gray-400">Live momentum of tracked assets</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Market Overview Card */}
                <div className="bg-darkBg border border-darkBorder rounded-xl p-6">
                    <h3 className="font-bold mb-6 text-xl">Sector Performance (Simulated)</h3>
                    <div className="space-y-4">
                        {['Technology', 'Semiconductors', 'Consumer Electronics', 'AI Infrastructure'].map(sector => (
                            <div key={sector} className="flex items-center justify-between">
                                <span className="text-gray-300">{sector}</span>
                                <div className="flex items-center gap-4 w-1/2">
                                    <div className="flex-1 h-2 bg-dark rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-green-500 rounded-full"
                                            style={{ width: `${Math.random() * 40 + 40}%` }}
                                        ></div>
                                    </div>
                                    <span className="text-green-400 text-sm font-mono">+{Math.floor(Math.random() * 5)}.{Math.floor(Math.random() * 9)}%</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Top Movers from User Watchlist */}
                <div className="bg-darkBg border border-darkBorder rounded-xl p-6">
                    <h3 className="font-bold mb-6 text-xl">Top Movers (Your List)</h3>
                    {loading ? (
                        <div className="text-gray-500 text-center">Loading trends...</div>
                    ) : trends.length === 0 ? (
                        <div className="text-gray-500 text-center italic">Add items to watchlist to see trends</div>
                    ) : (
                        <div className="space-y-2">
                            {trends
                                .sort((a, b) => Math.abs(b.change_percent || 0) - Math.abs(a.change_percent || 0))
                                .slice(0, 5)
                                .map(item => (
                                    <div key={item.ticker} className="flex items-center justify-between p-3 bg-dark/50 rounded-lg">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${(item.change_percent || 0) >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                                                }`}>
                                                <Activity size={16} />
                                            </div>
                                            <div>
                                                <div className="font-bold">{item.ticker}</div>
                                                <div className="text-xs text-gray-400">${item.current_price?.toFixed(2)}</div>
                                            </div>
                                        </div>
                                        <div className={`font-mono font-bold ${(item.change_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                                            }`}>
                                            {(item.change_percent || 0) > 0 ? '+' : ''}{(item.change_percent || 0).toFixed(2)}%
                                        </div>
                                    </div>
                                ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
