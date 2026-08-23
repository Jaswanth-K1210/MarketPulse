/**
 * API Service - Backend Integration
 * Connects frontend to FastAPI backend (http://localhost:8000)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000');

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 12000) // 12s timeout
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
    clearTimeout(timer)
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    clearTimeout(timer)
    console.error(`API Error [${endpoint}]:`, error.name === 'AbortError' ? 'timeout' : error.message)
    throw error
  }
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function authRegister(username, password, email = null) {
  return fetchAPI('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, email }),
  });
}

export async function authLogin(username, password) {
  return fetchAPI('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function authMe(token) {
  return fetchAPI('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function authGoogle(accessToken) {
  return fetchAPI('/api/auth/google', {
    method: 'POST',
    body: JSON.stringify({ access_token: accessToken }),
  });
}

// ── Alerts ───────────────────────────────────────────────────────────────────

/**
 * Get all alerts
 * GET /api/alerts
 */
export async function getAlerts() {
  return fetchAPI('/api/alerts');
}

/**
 * Get portfolio holdings
 * GET /api/portfolio
 */
export async function getPortfolio() {
  const userName = localStorage.getItem('marketpulse_user');
  const endpoint = userName ? `/api/portfolio?user_name=${encodeURIComponent(userName)}` : '/api/portfolio';
  return fetchAPI(endpoint);
}

/**
 * Get all articles
 * GET /api/articles?limit=10
 */
export async function getArticles(limit = 10, portfolio = null) {
  const portfolioParam = portfolio ? `&portfolio=${portfolio.join(',')}` : '';
  return fetchAPI(`/api/articles?limit=${limit}${portfolioParam}`);
}

/**
 * Get all relationships
 * GET /api/relationships
 */
export async function getRelationships() {
  return fetchAPI('/api/relationships');
}

/**
 * Get knowledge graphs
 * GET /api/knowledge-graphs
 */
export async function getKnowledgeGraphs() {
  return fetchAPI('/api/knowledge-graphs');
}

/**
 * Get system statistics
 * GET /api/stats
 */
export async function getStats() {
  return fetchAPI('/api/stats');
}

/**
 * Trigger manual news fetch
 * POST /api/fetch-news
 */
export async function triggerNewsFetch() {
  return fetchAPI('/api/fetch-news', { method: 'POST' });
}

/**
 * Trigger manual pipeline run
 * POST /api/run-pipeline
 */
export async function triggerPipeline() {
  return fetchAPI('/api/run-pipeline', { method: 'POST' });
}

/**
 * Get health status
 * GET /api/health
 */
export async function getHealth() {
  return fetchAPI('/api/health');
}

/**
 * Get Gemini budget status
 * GET /api/gemini-budget
 */
export async function getGeminiBudget() {
  return fetchAPI('/api/gemini-budget');
}

/**
 * Fetch and analyze news (Full Pipeline)
 * POST /api/fetch-and-analyze
 */
export async function fetchAndAnalyzeNews(limit = 4) {
  return fetchAPI(`/api/fetch-and-analyze?limit=${limit}`, { method: 'POST' });
}

/**
 * Get live stock prices
 * GET /api/stock-prices
 */
export async function getStockPrices(tickers = null) {
  const endpoint = tickers ? `/api/stock-prices?tickers=${tickers}` : '/api/stock-prices';
  return fetchAPI(endpoint);
}

/**
 * Get news fetch processing status
 * GET /api/news/fetch-status
 */
export async function getNewsFetchStatus() {
  return fetchAPI('/api/news/fetch-status');
}

/**
 * Add tickers to watchlist
 * POST /api/watchlist
 */
export async function addToWatchlist(tickers) {
  const tickersArray = Array.isArray(tickers) ? tickers : [tickers];
  return fetchAPI('/api/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tickers: tickersArray })
  });
}

// ── Pipeline Intelligence (Phase 2-5) ───────────────────────────────────────

/**
 * Run the full 13-node LangGraph intelligence pipeline
 * POST /api/run-intelligence
 */
export async function runIntelligencePipeline(portfolio, userId = 'frontend') {
  return fetchAPI('/api/run-intelligence', {
    method: 'POST',
    body: JSON.stringify({ portfolio, user_id: userId }),
  });
}

/**
 * Get audit trail for a pipeline run
 * GET /api/audit/:pipelineId
 */
export async function getAuditTrail(pipelineId) {
  return fetchAPI(`/api/audit/${encodeURIComponent(pipelineId)}`).catch(() => ({ records: [] }));
}

/**
 * Get temporal memory (streaks, trends) for a ticker
 * GET /api/memory/:ticker
 */
export async function getTemporalMemory(ticker) {
  return fetchAPI(`/api/memory/${encodeURIComponent(ticker)}`).catch(() => ({ streak: {}, trend: {} }));
}

/**
 * Get knowledge graph context for a ticker
 * GET /api/kg/:ticker
 */
export async function getKGContext(ticker) {
  return fetchAPI(`/api/kg/${encodeURIComponent(ticker)}`).catch(() => ({ neighbors: [], found: false }));
}

// ── Intelligence Layer v2 ────────────────────────────────────────────────────
export async function getRiskScores(countries = null) {
  const q = countries ? `?countries=${countries}` : '';
  return fetchAPI(`/api/intelligence/risk-scores${q}`).catch(() => null);
}
export async function getSignals() {
  return fetchAPI('/api/intelligence/signals').catch(() => null);
}
export async function getMacroData() {
  return fetchAPI('/api/intelligence/macro').catch(() => null);
}
export async function getMarketOverview() {
  return fetchAPI('/api/intelligence/market-overview').catch(() => null);
}
export async function getConflictData() {
  return fetchAPI('/api/intelligence/conflict').catch(() => null);
}
export async function getCorrelations() {
  return fetchAPI('/api/intelligence/correlations').catch(() => null);
}

// ── OSINT Signals ────────────────────────────────────────────────────────────
export async function getInsiderTrades(ticker) {
  return fetchAPI(`/api/intelligence/insider-trades/${ticker}`).catch(() => null);
}
export async function getShortInterest(ticker) {
  return fetchAPI(`/api/intelligence/short-interest/${ticker}`).catch(() => null);
}
export async function getRetailSentiment(ticker) {
  return fetchAPI(`/api/intelligence/retail-sentiment/${ticker}`).catch(() => null);
}
export async function getTechnicalAnalysis(ticker) {
  return fetchAPI(`/api/intelligence/technical-analysis/${ticker}`).catch(() => null);
}
export async function getFundamentals(ticker) {
  return fetchAPI(`/api/intelligence/fundamentals/${ticker}`).catch(() => null);
}
export async function getAlphaScore(ticker) {
  return fetchAPI(`/api/intelligence/alpha-score/${ticker}`).catch(() => null);
}

// ── Institutional Holdings ────────────────────────────────────────────────────
export async function getInstitutionalHoldings(ticker) {
  return fetchAPI(`/api/intelligence/institutional-holdings/${ticker}`).catch(() => null);
}

// ── Options Flow ──────────────────────────────────────────────────────────────
export async function getOptionsFlow(ticker) {
  return fetchAPI(`/api/intelligence/options-flow/${ticker}`).catch(() => null);
}

// ── Twitter Sentiment ─────────────────────────────────────────────────────────
export async function getTwitterSentiment(ticker) {
  return fetchAPI(`/api/intelligence/twitter-sentiment/${ticker}`).catch(() => null);
}

// ── Earnings Transcripts ──────────────────────────────────────────────────────
export async function getEarningsTranscripts(ticker) {
  return fetchAPI(`/api/intelligence/earnings-transcripts/${ticker}`).catch(() => null);
}

// ── FDA Trials ────────────────────────────────────────────────────────────────
export async function getFDATrials(company) {
  return fetchAPI(`/api/intelligence/fda-trials/${encodeURIComponent(company)}`).catch(() => null);
}

// ── Patents ───────────────────────────────────────────────────────────────────
export async function getPatents(company) {
  return fetchAPI(`/api/intelligence/patents/${encodeURIComponent(company)}`).catch(() => null);
}

// ── Beneish M-Score ───────────────────────────────────────────────────────────
export async function getMScore(ticker) {
  return fetchAPI(`/api/intelligence/m-score/${ticker}`).catch(() => null);
}

// ── Altman Z-Score ────────────────────────────────────────────────────────────
export async function getZScore(ticker) {
  return fetchAPI(`/api/intelligence/z-score/${ticker}`).catch(() => null);
}

// ── Factor Rotation ───────────────────────────────────────────────────────────
export async function getFactorRotation(regime = null) {
  const q = regime ? `?regime=${regime}` : '';
  return fetchAPI(`/api/intelligence/factor-rotation${q}`).catch(() => null);
}

// ── Technical Patterns ────────────────────────────────────────────────────────
export async function getTechnicalPatterns(ticker) {
  return fetchAPI(`/api/intelligence/technical-patterns/${ticker}`).catch(() => null);
}

// ── Portfolio Optimize ────────────────────────────────────────────────────────
export async function optimizePortfolio(holdings) {
  return fetchAPI('/api/intelligence/portfolio/optimize', {
    method: 'POST',
    body: JSON.stringify(holdings),
  }).catch(() => null);
}

// ── Portfolio Risk Metrics ────────────────────────────────────────────────────
export async function getRiskMetrics(tickers) {
  return fetchAPI('/api/intelligence/portfolio/risk-metrics', {
    method: 'POST',
    body: JSON.stringify(tickers),
  }).catch(() => null);
}

// ── Backtest ──────────────────────────────────────────────────────────────────
export async function runBacktest(ticker, strategy = 'alpha_momentum', start_date = null, end_date = null, initial_capital = 10000) {
  const params = new URLSearchParams({ strategy, initial_capital })
  if (start_date) params.append('start_date', start_date)
  if (end_date) params.append('end_date', end_date)
  return fetchAPI(`/api/intelligence/backtest/${ticker}?${params}`).catch(() => null);
}

// ── Walk-Forward Backtest ──────────────────────────────────────────────────────
export async function runWalkForward(ticker, strategy = 'alpha_momentum', train_days = 252, test_days = 63) {
  const params = new URLSearchParams({ strategy, train_days, test_days })
  return fetchAPI(`/api/intelligence/walk-forward/${ticker}?${params}`).catch(() => null);
}

// ── Anomaly Detection ─────────────────────────────────────────────────────────
export async function getAnomalyDetection(ticker) {
  return fetchAPI(`/api/intelligence/anomaly/${ticker}`).catch(() => null);
}

// ── Risk Feedback ──────────────────────────────────────────────────────────────
export async function submitRiskFeedback(ticker, predictedRisk, actualOutcome, features = {}) {
  return fetchAPI('/api/intelligence/ml/feedback', {
    method: 'POST',
    body: JSON.stringify({ ticker, predicted_risk: predictedRisk, actual_outcome: actualOutcome, features }),
  }).catch(() => null);
}

// ── Corporate Actions ─────────────────────────────────────────────────────────
export async function getCorporateActions(ticker) {
  return fetchAPI(`/api/intelligence/corporate-actions/${ticker}`).catch(() => null);
}

// ── Generate Report Dossier ───────────────────────────────────────────────────
export async function generateDossier(ticker) {
  return fetchAPI('/api/intelligence/reports/generate-dossier', {
    method: 'POST',
    body: JSON.stringify({ ticker }),
  }).catch(() => null);
}

// ── Telegram Test ─────────────────────────────────────────────────────────────
export async function testTelegramAlert(ticker = 'AAPL', signal = 'NEUTRAL', score = 0) {
  return fetchAPI('/api/intelligence/alerts/telegram-test', {
    method: 'POST',
    body: JSON.stringify({ ticker, signal, score }),
  }).catch(() => null);
}

// ── Chat Query ────────────────────────────────────────────────────────────────
export async function chatQuery(query) {
  return fetchAPI(`/api/chat/query?q=${encodeURIComponent(query)}`).catch(() => null);
}

export { API_BASE_URL };
