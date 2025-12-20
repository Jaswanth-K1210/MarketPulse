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
  const [articlesLimit, setArticlesLimit] = useState(10)

  // WebSocket connection for real-time updates
  const { isConnected, alerts: wsAlerts } = useWebSocket()

  // Load initial data from backend
  useEffect(() => {
    loadData()
    loadStockPrices()
  }, [])

  // Auto-refresh stock prices every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadStockPrices()
    }, 30000) // 30 seconds
    
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

      // Fetch data from backend in parallel
      const [alertsData, articlesData, portfolioData, statsData] = await Promise.all([
        getAlerts().catch(() => ({ alerts: [] })),
        getArticles(articlesLimit).catch(() => ({ articles: [] })),
        getPortfolio().catch(() => ({ holdings: [] })),
        getStats().catch(() => ({}))
      ])

      // Transform backend data to frontend format
      const transformedAlerts = (alertsData.alerts || alertsData || []).map(transformAlert)
      const fetchedArticles = articlesData.articles || articlesData || []
      
      // Use backend portfolio if available, otherwise use dummy data
      let transformedPortfolio
      if (portfolioData.holdings && portfolioData.holdings.length > 0) {
        transformedPortfolio = transformPortfolio(portfolioData)
      } else {
        // Dummy portfolio data for display
        transformedPortfolio = {
          user: { name: "Jaswanth", role: "Portfolio Manager" },
          holdings: [
            { id: 1, company: "Apple Inc.", ticker: "AAPL", quantity: 150, purchasePrice: 145.50, currentPrice: 198.75, impact: 0 },
            { id: 2, company: "NVIDIA Corporation", ticker: "NVDA", quantity: 80, purchasePrice: 420.00, currentPrice: 875.50, impact: 0 },
            { id: 3, company: "Advanced Micro Devices", ticker: "AMD", quantity: 120, purchasePrice: 95.00, currentPrice: 168.30, impact: 0 },
            { id: 4, company: "Intel Corporation", ticker: "INTC", quantity: 200, purchasePrice: 42.50, currentPrice: 36.45, impact: 0 },
            { id: 5, company: "Broadcom Inc.", ticker: "AVGO", quantity: 60, purchasePrice: 540.00, currentPrice: 795.20, impact: 0 },
          ],
          totalValue: 150000,
          totalChange: 12500,
          changePercent: 8.3
        }
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
      if (result.alerts_generated > 0) {
        alert(`✅ Success! Fetched ${result.articles_fetched} articles and generated ${result.alerts_generated} new alerts.`)
      } else {
        alert(`✅ Fetched ${result.articles_fetched} fresh articles! ${result.alerts_generated > 0 ? `Generated ${result.alerts_generated} alerts.` : 'No alerts generated (may be due to Gemini API limit).'}`)
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
    <div className="flex-1 bg-gradient-to-br from-dark to-darkBg">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gradient-to-r from-darkBg via-darkBg to-darkBg/95 backdrop-blur border-b border-darkBorder">
        <div className="px-8 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">Dashboard</h1>
            <div className="flex items-center gap-3">
              <p className="text-gray-400 text-sm">Real-time market intelligence at a glance</p>
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
              <span className="text-xs text-gray-500">Auto-Refresh Every 5 Min</span>
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
      <div className="p-8 space-y-8">
        {/* Live Stock Prices */}
        {stockPrices && Object.keys(stockPrices).length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <TrendingUp size={24} className="text-blue-500" />
                Live Stock Prices
              </h2>
              <div className="flex items-center gap-3">
                {lastPriceUpdate && (
                  <span className="text-xs text-gray-400">
                    Updated {Math.floor((new Date() - lastPriceUpdate) / 1000)}s ago
                  </span>
                )}
                <button
                  onClick={loadStockPrices}
                  disabled={priceLoading}
                  className="text-xs px-3 py-1 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 
                            text-blue-300 rounded-lg transition-colors disabled:opacity-50"
                >
                  {priceLoading ? 'Updating...' : 'Refresh Prices'}
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
            <div className="bg-darkBg border border-darkBorder rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">🔔 Recent Alerts</h2>
                <a href="#" className="text-blue-500 text-sm hover:underline">View all</a>
              </div>
              <div className="space-y-4">
                {alerts.length > 0 ? (
                  alerts.slice(0, 4).map(alert => (
                    <AlertCard key={alert.id} alert={alert} onExplain={handleExplain} />
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <AlertCircle size={48} className="mx-auto mb-3 opacity-30" />
                    <p>No alerts yet</p>
                    <p className="text-sm mt-2">Alerts will appear here when news impacts your portfolio</p>
                  </div>
                )}
              </div>
            </div>

            {/* News Feed */}
            <div className="bg-darkBg border border-darkBorder rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Newspaper className="text-blue-400" size={20} />
                  <h2 className="text-xl font-bold text-white">📰 Recent News ({articles.length} articles)</h2>
                </div>
                <span className="text-sm text-gray-400">Updated 2 min ago</span>
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
                        className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 text-center text-sm font-medium text-gray-300 transition-all hover:bg-gray-700 hover:text-white"
                      >
                        Load More News
                      </button>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <Newspaper size={48} className="mx-auto mb-3 opacity-30" />
                    <p>No news articles yet</p>
                    <p className="text-sm mt-2">Click "Fetch & Analyze News" to load articles</p>
                  </div>
                )}
              </div>
            </div>

            {/* Portfolio Holdings */}
            <div className="bg-darkBg border border-darkBorder rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">Portfolio Holdings</h2>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-400">{portfolio.holdings?.length || 0} companies</span>
                  {stockPrices && (
                    <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full animate-pulse">
                      Live
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
            <div className="bg-darkBg border border-darkBorder rounded-lg p-6">
              <h3 className="font-bold mb-4">Alert Trend (7 days)</h3>
              <AlertTrendChart data={stats.alertTrendData} />
            </div>

            {/* Fetch & Analyze Button */}
            <div className="bg-gradient-to-br from-green-600/20 to-blue-600/20 border border-green-500/30 rounded-lg p-6">
              <h3 className="font-bold mb-3 text-green-300">🤖 AI Analysis</h3>
              <p className="text-sm text-gray-400 mb-4">
                Fetch latest news and run full multi-agent analysis
              </p>
              <button
                onClick={handleFetchAndAnalyze}
                disabled={analyzing || !isConnected}
                className="w-full bg-gradient-to-r from-green-500 to-blue-500 hover:from-green-600 hover:to-blue-600 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 mb-2"
              >
                {analyzing ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Zap size={18} />
                    Fetch & Analyze News (10 articles)
                  </>
                )}
              </button>
              <button
                onClick={handleFetchNewsOnly}
                disabled={analyzing || !isConnected}
                className="w-full bg-gradient-to-r from-blue-500/80 to-purple-500/80 hover:from-blue-500 hover:to-purple-500 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 text-sm"
                title="Fetch news only (no AI processing) - useful when Gemini API limit is reached"
              >
                {analyzing ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    Fetching...
                  </>
                ) : (
                  <>
                    <Newspaper size={16} />
                    Fetch News Only (No AI)
                  </>
                )}
              </button>
              {analysisResult && (
                <div className="mt-3 p-3 bg-green-500/10 border border-green-500/30 rounded text-sm text-green-300">
                  ✅ {analysisResult.message}
                </div>
              )}
            </div>

            {/* System Info */}
            <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-lg p-6">
              <h3 className="font-bold mb-2 text-blue-300">System Status</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Backend</span>
                  {isConnected ? (
                    <span className="text-green-400 flex items-center gap-1">
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                      Connected
                    </span>
                  ) : (
                    <span className="text-red-400 flex items-center gap-1">
                      <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                      Disconnected
                    </span>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Active Alerts</span>
                  <span className="text-white font-bold">{alerts.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Portfolio Holdings</span>
                  <span className="text-white font-bold">{portfolio.holdings?.length || 0}</span>
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
