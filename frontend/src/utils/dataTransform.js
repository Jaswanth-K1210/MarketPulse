/**
 * Data transformation utilities
 * Converts backend data models to frontend format
 */

/**
 * Transform backend alert to frontend format
 */
export function transformAlert(backendAlert) {
  // Handle new format with affected_holdings
  const affectedHoldings = backendAlert.affected_holdings || []
  const primaryHolding = affectedHoldings[0] || {}

  // Build title from alert data
  let title = backendAlert.title
  if (!title) {
    if (backendAlert.type === 'positive_impact') {
      title = `✨ POSITIVE: ${primaryHolding.company || 'Portfolio'} Impact`
    } else if (backendAlert.type === 'relationship_based') {
      title = `🔴 CRITICAL: ${primaryHolding.company || 'Supply Chain'} Disruption`
    } else {
      title = `🟡 MEDIUM: ${primaryHolding.company || 'Market'} Event`
    }
  }

  // Determine icon based on severity and type
  let icon = '⚠️'
  if (backendAlert.type === 'positive_impact') {
    icon = '✨'
  } else if (backendAlert.severity === 'high' || backendAlert.severity === 'critical') {
    icon = '🔴'
  } else if (backendAlert.severity === 'medium') {
    icon = '🟡'
  }

  return {
    id: backendAlert.id,
    title: title,
    company: primaryHolding.company || backendAlert.affected_companies?.[0] || 'Multiple',
    ticker: primaryHolding.ticker || backendAlert.affected_tickers?.[0] || 'N/A',
    severity: backendAlert.severity || 'medium',
    impact: backendAlert.impact_percent || backendAlert.portfolio_impact_percent || 0,
    impact_percent: backendAlert.impact_percent || backendAlert.portfolio_impact_percent || 0,
    description: backendAlert.explanation || backendAlert.event_summary || backendAlert.title,
    timestamp: backendAlert.created_at,
    created_at: backendAlert.created_at,
    confidence: backendAlert.confidence || 0.85,
    recommendation: backendAlert.recommendation || 'MONITOR',
    impactChain: backendAlert.chain || {
      level1: backendAlert.cascade_chain?.[0]?.description || 'Initial event',
      level2: backendAlert.cascade_chain?.[1]?.description || 'Secondary impact',
      level3: backendAlert.cascade_chain?.[2]?.description || `Expected ${backendAlert.impact_percent || 0}% impact`
    },
    chain: backendAlert.chain ?
      `${backendAlert.chain.level1 || ''} → ${backendAlert.chain.level2 || ''} → ${backendAlert.chain.level3 || ''}` :
      null,
    sources: backendAlert.sources || backendAlert.source_urls || [],
    explanation: backendAlert.full_reasoning || backendAlert.ai_analysis || backendAlert.explanation || backendAlert.description || '',
    ai_analysis: backendAlert.ai_analysis || '',
    full_reasoning: backendAlert.full_reasoning || '',
    affected_holdings: affectedHoldings.map(h => ({
      company: h.company,
      impact_percent: h.impact_percent,
      shares: h.quantity,
      impact_value: h.impact_dollar || (h.impact_percent * h.current_price * h.quantity / 100)
    })),
    icon: icon,
    tags: backendAlert.tags || []
  };
}

/**
 * Transform backend portfolio to frontend format
 */
export function transformPortfolio(backendPortfolio) {
  const holdings = backendPortfolio.holdings || [];

  const transformedHoldings = holdings.map((holding, index) => ({
    id: index + 1,
    company: holding.company_name || holding.company,
    ticker: holding.ticker,
    quantity: holding.quantity,
    purchasePrice: holding.purchasePrice || holding.purchase_price || holding.avg_price || 0,
    currentPrice: holding.currentPrice || holding.current_price || 0,
    impact: 0 // Will be calculated from alerts
  }));

  const totalValue = transformedHoldings.reduce(
    (sum, h) => sum + (h.quantity * h.currentPrice),
    0
  );

  const totalCost = transformedHoldings.reduce(
    (sum, h) => sum + (h.quantity * h.purchasePrice),
    0
  );

  const totalChange = totalValue - totalCost;
  const changePercent = totalCost > 0 ? (totalChange / totalCost) * 100 : 0;

  return {
    user: {
      name: backendPortfolio.user_name || "Jaswanth",
      role: "Portfolio Manager"
    },
    holdings: transformedHoldings,
    totalValue,
    totalChange,
    changePercent
  };
}

/**
 * Transform backend stats to frontend format
 */
export function transformStats(backendStats) {
  // API returns: active_alerts, watched_companies, articles_processed, relationships_mapped
  return {
    activeAlerts:      backendStats.active_alerts      ?? backendStats.total_alerts      ?? 0,
    alertsToday:       backendStats.alerts_today       ?? 0,
    watchedCompanies:  backendStats.watched_companies  ?? backendStats.companies_tracked ?? 0,
    companiesThisWeek: backendStats.new_companies_this_week ?? 0,
    marketImpactScore: calculateMarketImpactScore(backendStats),
    scoreChange:       0.5,
    eventsDetected:    backendStats.articles_processed ?? backendStats.total_events      ?? 0,
    eventsThisWeek:    backendStats.events_this_week   ?? 0,
  };
}

/**
 * Calculate market impact score from stats
 */
function calculateMarketImpactScore(stats) {
  // Simple scoring: average of absolute impact percentages.
  // No average means no score: return null rather than inventing one (a real 0 is still a score).
  if (typeof stats.average_impact !== 'number' || Number.isNaN(stats.average_impact)) return null;
  return Math.abs(stats.average_impact * 10).toFixed(1);
}

/**
 * Parse a backend timestamp. The backend writes naive datetime.now() strings
 * ("2026-10-06 22:42:03.394186"); servers run in UTC, so read them as UTC.
 * Returns a Date, or null when the value isn't a usable timestamp.
 */
export function parseTimestamp(ts) {
  if (ts == null || ts === '') return null;
  let v = ts;
  if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(v)) {
    v = v.replace(' ', 'T');
    if (!/(Z|[+-]\d{2}:?\d{2})$/.test(v)) v += 'Z';
  }
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Alert counts for the last 7 local days, oldest first, ending today.
 * Returns null when no alert has a usable timestamp, so callers can hide the chart.
 */
export function alertCountsLast7Days(alerts, now = new Date()) {
  const times = (alerts || []).map(a => parseTimestamp(a.created_at ?? a.timestamp)).filter(Boolean);
  if (times.length === 0) return null;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Array.from({ length: 7 }, (_, i) => {
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (6 - i));
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 1);
    return {
      label: start.toLocaleDateString('en-US', { weekday: 'short' }),
      count: times.filter(t => t >= start && t < end).length,
    };
  });
}

/**
 * Get severity from impact percentage
 */
export function getSeverityFromImpact(impact) {
  const absImpact = Math.abs(impact);
  if (absImpact >= 2) return 'critical';
  if (absImpact >= 1) return 'high';
  if (absImpact >= 0.5) return 'medium';
  return 'low';
}

/**
 * Get recommendation from impact
 */
export function getRecommendationFromImpact(impact) {
  if (impact <= -2) return 'SELL';
  if (impact <= -1) return 'REDUCE';
  if (impact >= 2) return 'BUY';
  if (impact >= 1) return 'INCREASE';
  return 'HOLD';
}
