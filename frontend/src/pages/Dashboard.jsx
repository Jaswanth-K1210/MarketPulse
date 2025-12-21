import React, { useState, useEffect } from 'react'
import { AlertCircle, TrendingUp, Building2, Zap, RefreshCw, Newspaper } from 'lucide-react'
import StatCard from '../components/StatCard'
import AlertCard from '../components/AlertCard'
import PortfolioCard from '../components/PortfolioCard'
import AlertTrendChart from '../components/AlertTrendChart'
import ExplanationModal from '../components/ExplanationModal'
import NewsCard from '../components/NewsCard'
import StockTicker from '../components/StockTicker'
import ProcessingStatus from '../components/ProcessingStatus'
import { getAlerts, getPortfolio, getStats, triggerNewsFetch, triggerPipeline, fetchAndAnalyzeNews, getArticles, getStockPrices } from '../services/api'
import { transformAlert, transformPortfolio, transformStats } from '../utils/dataTransform'
import { useWebSocket } from '../hooks/useWebSocket'

export default function Dashboard() {
  // State management
  const [alerts, setAlerts] = useState([])
  const [articles, setArticles] = useState([])
  const [portfolio, setPortfolio] = useState({ holdings: [], totalValue: 0, totalChange: 0, changePercent: 0 })
  const [stats, setStats] = useState({
    activeAlerts: 0,
    alertsToday: 0,
    watchedCompanies: 0,
    companiesThisWeek: 0,
    marketImpactScore: 0,
    scoreChange: 0,
    eventsDetected: 0,
    eventsThisWeek: 0,
    alertTrendData: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showExplanationModal, setShowExplanationModal] = useState(false)
  const [selectedAlertForExplain, setSelectedAlertForExplain] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [stockPrices, setStockPrices] = useState(null)
  const [lastPriceUpdate, setLastPriceUpdate] = useState(null)
  const [priceLoading, setPriceLoading] = useState(false)
  const [articlesLimit, setArticlesLimit] = useState(15)

  // WebSocket connection for real-time updates
  const { isConnected, alerts: wsAlerts } = useWebSocket()

  // Load initial data from backend
  useEffect(() => {
    loadData()
    loadStockPrices()
  }, [])

  // Auto-refresh stock prices every 10 seconds for real-time data
  useEffect(() => {
    const interval = setInterval(() => {
      loadStockPrices()
    }, 10000) // 10 seconds for live market feed

    return () => clearInterval(interval)
  }, [])

  // Handle WebSocket alerts
  useEffect(() => {
    if (wsAlerts.length > 0) {
      const latestAlert = wsAlerts[0]
      const transformedAlert = transformAlert(latestAlert)
      setAlerts(prev => [transformedAlert, ...prev])
    }
  }, [wsAlerts])

  async function loadStockPrices() {
    try {
      setPriceLoading(true)
      const pricesData = await getStockPrices()

      if (pricesData && pricesData.data) {
        setStockPrices(pricesData.data)
        setLastPriceUpdate(new Date())
      }
    } catch (err) {
      console.error('Failed to load stock prices:', err)
    } finally {
      setPriceLoading(false)
    }
  }

  async function loadData() {
    try {
      setLoading(true)
      setError(null)

      // First get portfolio to know which companies to filter for
      const portfolioData = await getPortfolio().catch(() => ({ holdings: [] }))
      const portfolioTickers = portfolioData.holdings?.map(h => h.ticker) || ['AAPL', 'NVDA', 'AMD', 'INTC', 'AVGO']

      // Fetch data from backend in parallel
      const [alertsData, articlesData, statsData] = await Promise.all([
        getAlerts().catch(() => ({ alerts: [] })),
        getArticles(articlesLimit, portfolioTickers).catch(() => ({ articles: [] })),
        getStats().catch(() => ({}))
      ])

      // Transform backend data to frontend format
      const transformedAlerts = (alertsData.alerts || alertsData || []).map(transformAlert)
      const fetchedArticles = articlesData.articles || articlesData || []

      // ALWAYS use backend portfolio data (no dummy fallback)
      const transformedPortfolio = portfolioData.holdings && portfolioData.holdings.length > 0
        ? transformPortfolio(portfolioData)
        : {
          user: { name: "User", role: "USER" }, // userName is not defined, using "User" as fallback
          holdings: [],
          totalValue: 0,
          totalChange: 0,
          changePercent: 0
        }

      const transformedStats = statsData ? transformStats(statsData) : stats

      setAlerts(transformedAlerts)
      setArticles(fetchedArticles)
      setPortfolio(transformedPortfolio)
      setStats(transformedStats)
    } catch (err) {
      console.error('Failed to load data:', err)
      setError('Failed to connect to backend. Please ensure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await Promise.all([loadData(), loadStockPrices()])
    setRefreshing(false)
  }

  const handleExplain = (alert) => {
    setSelectedAlertForExplain(alert)
    setShowExplanationModal(true)
  }

  const handleFetchAndAnalyze = async () => {
    try {
      setAnalyzing(true)
      setError(null)
      setAnalysisResult(null)

      // Call the API - fetch 10 articles
      const result = await fetchAndAnalyzeNews(10)

      setAnalysisResult(result)

      // CRITICAL: Always refresh articles from database to get fresh data
      // Articles are now saved immediately after fetching, even if processing fails
      await loadData()

      // Show success message
      // Show success message with detailed feedback
      if (result.alerts_generated > 0) {
        alert(`✅ Analysis Complete!\n\nFound ${result.articles_fetched} relevant articles.\nGenerated ${result.alerts_generated} NEW alerts affecting your portfolio.`)
      } else {
        alert(`✅ Analysis Complete!\n\nFetched ${result.articles_fetched} articles but found 0 direct impacts on your portfolio.\n\nPossible reasons:\n1. News is general market news (not company specific)\n2. AI filtered out low-impact events\n3. Gemini API rate limit reached (check logs)`)
      }
    } catch (err) {
      console.error('Failed to fetch and analyze:', err)
      setError('Failed to run analysis. Articles may still be saved. Please refresh to see new articles.')
      // Even if processing fails, try to refresh articles
      await loadData()
    } finally {
      setAnalyzing(false)
    }
  }

  const handleFetchNewsOnly = async () => {
    try {
      setAnalyzing(true)
      setError(null)

      // Fetch news only (no Gemini processing) - useful when API limit is reached
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/fetch-news?limit=10`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      if (!response.ok) throw new Error('Failed to fetch news')

      const result = await response.json()

      // Refresh articles to show new ones
      await loadData()

      alert(`✅ Fetched and saved ${result.articles_saved || result.articles_fetched} fresh articles!`)
    } catch (err) {
      console.error('Failed to fetch news:', err)
      setError('Failed to fetch news. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="flex-1 bg-darkBg">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-darkBg/95 backdrop-blur border-b border-darkBorder">
        <div className="px-8 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-black text-primary uppercase tracking-tighter italic">Dashboard</h1>
            <div className="flex items-center gap-3">
              <p className="text-secondary text-sm">Real-time market intelligence at a glance</p>
              {isConnected ? (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  Live
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-red-400">
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  Offline
                </span>
              )}
              <span className="text-xs text-gray-500">Live Updates Every 10s</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <input
              type="text"
              placeholder="Search companies, events..."
              className="px-4 py-2 bg-darkBorder border border-darkBorder rounded-lg text-sm focus:outline-none focus:border-blue-500 w-96"
            />
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="relative p-2 hover:bg-darkBorder rounded-lg disabled:opacity-50"
              title="Refresh data"
            >
              <RefreshCw size={20} className={refreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
        {error && (
          <div className="px-8 pb-4">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg px-4 py-2 text-yellow-400 text-sm">
              ⚠️ {error}
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading data...</p>
          </div>
        </div>
      )}

      {/* Main Content */}
      {!loading && (
        <div className="p-8 space-y-8 animate-fade-in relative z-10">
          {/* Live Stock Prices */}
          {stockPrices && Object.keys(stockPrices).length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-black text-primary flex items-center gap-2 uppercase tracking-widest">
                  <TrendingUp size={24} className="text-blue-500" />
                  Live Market Feed
                </h2>
                <div className="flex items-center gap-3">
                  {lastPriceUpdate && (
                    <span className="text-[10px] text-gray-500 font-mono uppercase tracking-tighter">
                      Synced {Math.floor((new Date() - lastPriceUpdate) / 1000)}s ago
                    </span>
                  )}
                  <button
                    onClick={loadStockPrices}
                    disabled={priceLoading}
                    className="text-[10px] px-4 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 
                            text-blue-400 rounded-full transition-all disabled:opacity-50 uppercase font-black"
                  >
                    {priceLoading ? 'Updating Hub...' : 'Sync Raw Data'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-5 gap-4">
                {Object.values(stockPrices).map((stock) => (
                  <StockTicker
                    key={stock.ticker}
                    ticker={stock.ticker}
                    price={stock.current_price}
                    change={stock.change}
                    changePercent={stock.change_percent}
                    companyName={stock.company_name}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-4 gap-4">
            <StatCard
              title="Active Alerts"
              value={stats.activeAlerts}
              change={`+${stats.alertsToday} today`}
              changeType="negative"
              icon={<AlertCircle className="text-red-500" />}
            />
            <StatCard
              title="Watched Companies"
              value={stats.watchedCompanies}
              change={`+${stats.companiesThisWeek} this week`}
              changeType="positive"
              icon={<Building2 className="text-blue-500" />}
            />
            <StatCard
              title="Market Impact Score"
              value={stats.marketImpactScore}
              change={`+${stats.scoreChange} from yesterday`}
              changeType="positive"
              icon={<TrendingUp className="text-green-500" />}
            />
            <StatCard
              title="Events Detected"
              value={stats.eventsDetected}
              change={`+${stats.eventsThisWeek} this week`}
              changeType="neutral"
              icon={<Zap className="text-yellow-500" />}
            />
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-3 gap-6">
            {/* Left Column - Alerts, News & Portfolio */}
            <div className="col-span-2 space-y-6">
              {/* Recent Alerts */}
              <div className="glass-card rounded-2xl p-6 shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-black text-primary flex items-center gap-3">
                    <span className="w-1.5 h-6 bg-red-500 rounded-full"></span>
                    Recent Intelligence Alerts
                  </h2>
                  <a href="#" className="text-blue-400 text-xs font-bold uppercase hover:text-blue-300 transition-colors">Audit All</a>
                </div>

                {/* Check if all alerts have zero impact */}
                {alerts.length > 0 && alerts.every(a => Math.abs(a.impact || 0) === 0) && (
                  <div className="mb-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                    <p className="text-sm text-blue-300 font-medium">
                      💡 There are no alerts that affect your portfolio right now.
                      Just watch these when you're free — sounds interesting!
                    </p>
                  </div>
                )}

                <div className="space-y-4">
                  {alerts.length > 0 ? (
                    alerts.slice(0, 4).map(alert => (
                      <AlertCard key={alert.id} alert={alert} onExplain={handleExplain} />
                    ))
                  ) : (
                    <div className="text-center py-12 text-gray-500 bg-dark/20 rounded-xl border border-dashed border-white/5">
                      <AlertCircle size={48} className="mx-auto mb-4 opacity-10" />
                      <p className="font-bold tracking-tight">No anomalies detected</p>
                      <p className="text-xs mt-1">Intelligence engine is scanning market signals...</p>
                    </div>
                  )}
                </div>
              </div>

              {/* News Feed */}
              <div className="glass-card rounded-2xl p-6 shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                      <Newspaper className="text-blue-400" size={20} />
                    </div>
                    <h2 className="text-xl font-black text-primary">Market Sentiment Feed</h2>
                  </div>
                  <span className="text-[10px] font-mono text-secondary uppercase">Live Index • {articles.length} Blobs</span>
                </div>
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {articles.length > 0 ? (
                    <>
                      {articles.slice(0, articlesLimit).map((article, idx) => (
                        <NewsCard key={article.id || idx} article={article} />
                      ))}
                      {articles.length > articlesLimit && (
                        <button
                          onClick={() => setArticlesLimit(prev => prev + 10)}
                          className="w-full rounded-xl border border-white/5 bg-white/5 py-3 text-center text-xs font-black text-secondary uppercase tracking-widest transition-all hover:bg-white/10 hover:text-primary mt-4"
                        >
                          Load Historical Data
                        </button>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-12 text-gray-500 bg-dark/20 rounded-xl border border-dashed border-white/5">
                      <Newspaper size={48} className="mx-auto mb-4 opacity-10" />
                      <p className="font-bold tracking-tight">Feed is empty</p>
                      <p className="text-xs mt-1">Initialize AI Analysis to populate market sentiment.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Portfolio Holdings */}
              <div className="glass-card rounded-2xl p-6 shadow-2xl overflow-hidden relative">
                <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/5 blur-3xl rounded-full -mr-16 -mt-16"></div>
                <div className="flex items-center justify-between mb-8">
                  <div>
                    <h2 className="text-xl font-black text-primary">Portfolio Command Center</h2>
                    <p className="text-xs text-secondary mt-1 uppercase tracking-tighter">Monitoring {portfolio.holdings?.length || 0} Assets</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {stockPrices && (
                      <span className="text-[10px] px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full font-black uppercase tracking-widest flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                        Neural Link Active
                      </span>
                    )}
                  </div>
                </div>
                <div className="space-y-2">
                  {portfolio.holdings?.map(holding => {
                    // Merge live price data with holding
                    const livePrice = stockPrices?.[holding.ticker]
                    const enrichedHolding = livePrice ? {
                      ...holding,
                      currentPrice: livePrice.current_price,
                      current_price: livePrice.current_price,
                      day_change_percent: livePrice.change_percent
                    } : holding

                    return <PortfolioCard key={holding.id} holding={enrichedHolding} />
                  })}
                </div>
              </div>
            </div>

            {/* Right Column - Stats & Trigger */}
            <div className="space-y-6">
              {/* Processing Status */}
              <ProcessingStatus />

              {/* Alert Trend */}
              <div className="glass-card rounded-2xl p-6 shadow-2xl">
                <h3 className="font-bold mb-4 text-gray-400 uppercase text-xs tracking-widest">Volatility Trend (7D)</h3>
                <AlertTrendChart data={stats.alertTrendData} />
              </div>

              {/* Fetch & Analyze Button */}
              <div className="bg-gradient-to-br from-blue-600/10 via-purple-600/10 to-blue-600/5 border border-white/5 rounded-2xl p-6 shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 blur-3xl rounded-full -mr-32 -mt-32 group-hover:bg-blue-600/20 transition-all duration-700"></div>
                <h3 className="text-lg font-black mb-1 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent uppercase tracking-tight">Execute Neural Analysis</h3>
                <p className="text-xs text-gray-500 mb-6 leading-relaxed font-medium">
                  Triggers multi-agent swarm to parse sentiment and generate portfolio-specific risk reports.
                </p>
                <div className="space-y-3">
                  <button
                    onClick={handleFetchAndAnalyze}
                    disabled={analyzing || !isConnected}
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 disabled:from-gray-700 disabled:to-gray-800 disabled:opacity-50 text-white font-black py-4 px-4 rounded-xl shadow-lg shadow-blue-600/20 transition-all active:scale-95 flex items-center justify-center gap-3"
                  >
                    {analyzing ? (
                      <>
                        <RefreshCw size={20} className="animate-spin" />
                        <span className="uppercase tracking-widest text-xs">Computing...</span>
                      </>
                    ) : (
                      <>
                        <Zap size={20} fill="currentColor" />
                        <span className="uppercase tracking-widest text-xs">Deep Analysis (v4.2)</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleFetchNewsOnly}
                    disabled={analyzing || !isConnected}
                    className="w-full bg-dark/40 hover:bg-dark/60 text-secondary hover:text-primary border border-white/5 font-bold py-3 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-xs uppercase tracking-tighter"
                  >
                    {analyzing ? (
                      <RefreshCw size={14} className="animate-spin" />
                    ) : (
                      <Newspaper size={14} />
                    )}
                    Raw Data Sync Only
                  </button>
                </div>
                {analysisResult && (
                  <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-[10px] text-green-400 font-bold uppercase tracking-widest text-center animate-pulse">
                    Neural Batch Success
                  </div>
                )}
              </div>

              {/* System Info */}
              <div className="glass-card rounded-2xl p-6 shadow-2xl relative overflow-hidden border-blue-500/20">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="font-black text-gray-400 uppercase text-xs tracking-widest">Protocol Status</h3>
                  <div className="h-1.5 w-1.5 bg-blue-500 rounded-full animate-ping"></div>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl border border-white/5">
                    <span className="text-gray-500 text-xs font-bold uppercase">Mainframe</span>
                    {isConnected ? (
                      <span className="text-[10px] font-black uppercase tracking-widest text-green-400 bg-green-400/10 px-2 py-0.5 rounded">
                        Online
                      </span>
                    ) : (
                      <span className="text-[10px] font-black uppercase tracking-widest text-red-400 bg-red-400/10 px-2 py-0.5 rounded">
                        Offline
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-white/5 rounded-xl border border-white/5 text-center">
                      <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">Signals</div>
                      <div className="text-xl font-mono text-primary">{alerts.length}</div>
                    </div>
                    <div className="p-3 bg-white/5 rounded-xl border border-white/5 text-center">
                      <div className="text-[10px] text-gray-500 font-bold uppercase mb-1">Exposure</div>
                      <div className="text-xl font-mono text-primary">{portfolio.holdings?.length || 0}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Explanation Modal */}
      {showExplanationModal && selectedAlertForExplain && (
        <ExplanationModal
          alert={selectedAlertForExplain}
          onClose={() => {
            setShowExplanationModal(false)
            setSelectedAlertForExplain(null)
          }}
        />
      )}
    </div>
  )
}
