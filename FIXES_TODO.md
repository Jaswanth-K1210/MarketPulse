# MarketPulse-X - Critical Fixes Implementation Plan

## Priority 1: Onboarding & Discovery (IN PROGRESS)
- [x] **Trigger Agent 3B during portfolio creation** - Added background task
- [ ] **Store discovered relationships in database** - Need to verify persistence
- [ ] **Show discovery progress in TerminalLoader** - Update UI to show "Discovering relationships..."

## Priority 2: Dashboard Performance
- [ ] **Optimize initial data loading** - Reduce API calls, use parallel fetching
- [ ] **Cache stock prices** - Avoid repeated yfinance calls
- [ ] **Lazy load news feed** - Don't block dashboard render

## Priority 3: Portfolio Display
- [ ] **Show live stock prices on portfolio cards** - Already have stock_prices endpoint
- [ ] **Display current value, gain/loss** - Calculate from live prices
- [ ] **Add company logos/icons** - Optional enhancement

## Priority 4: News Feed (DONE ✅)
- [x] **Fetch live from News API** - Using NewsIngestionLayer
- [x] **Filter by portfolio companies** - Only show relevant news
- [x] **Display affected companies** - Red warning badges

## Priority 5: Alerts System
- [ ] **Add detailed reasoning trail** - Show agent decision process
- [ ] **Include source links** - News articles, SEC filings used
- [ ] **Show AI analysis explanation** - Why this matters to portfolio
- [ ] **Add confidence scores** - How certain is the analysis

## Priority 6: Alert Trend Graph
- [ ] **Fix data accuracy** - Ensure correct historical data
- [ ] **Add real trend calculation** - Based on actual alerts over time
- [ ] **Improve visualization** - Make it more readable

## Implementation Order:
1. Fix onboarding discovery (30 min)
2. Optimize dashboard loading (20 min)
3. Add stock prices to portfolio (15 min)
4. Enhance alerts with reasoning (45 min)
5. Fix alert trend graph (20 min)

**Total Estimated Time: ~2 hours**
