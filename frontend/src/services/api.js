/**
 * API Service - Backend Integration
 * Connects frontend to FastAPI backend (http://localhost:8000)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000');

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

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

export { API_BASE_URL };
