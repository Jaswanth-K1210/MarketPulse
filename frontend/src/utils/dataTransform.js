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
    timestamp: formatTimestamp(backendAlert.created_at),
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
    explanation: backendAlert.explanation || backendAlert.description || '',
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
    purchasePrice: holding.purchase_price,
    currentPrice: holding.current_price,
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
  return {
    activeAlerts: backendStats.total_alerts || 0,
    alertsToday: backendStats.alerts_today || 0,
    watchedCompanies: backendStats.companies_tracked || 0,
    companiesThisWeek: backendStats.new_companies_this_week || 0,
    marketImpactScore: calculateMarketImpactScore(backendStats),
    scoreChange: 0.5, // Can be calculated from historical data
    eventsDetected: backendStats.total_events || 0,
    eventsThisWeek: backendStats.events_this_week || 0,
    alertTrendData: generateTrendData(backendStats.recent_alerts || [])
  };
}

/**
 * Calculate market impact score from stats
 */
function calculateMarketImpactScore(stats) {
  // Simple scoring: average of absolute impact percentages
  if (stats.average_impact) {
    return Math.abs(stats.average_impact * 10).toFixed(1);
  }
  return 7.2; // Default
}

/**
 * Generate trend data from recent alerts
 */
function generateTrendData(recentAlerts) {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const counts = new Array(7).fill(0);
  
  // Group alerts by day of week (simplified)
  recentAlerts.forEach(alert => {
    if (alert.created_at) {
      const date = new Date(alert.created_at);
      const dayIndex = date.getDay();
      counts[dayIndex] = (counts[dayIndex] || 0) + 1;
    }
  });

  return days.map((day, index) => ({
    day,
    alerts: counts[index] || 0
  }));
}

/**
 * Format timestamp to relative time
 */
export function formatTimestamp(timestamp) {
  if (!timestamp) return 'Unknown';
  
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString();
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
