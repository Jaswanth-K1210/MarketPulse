# MarketPulse OSINT — Complete Implementation Blueprint

## What We're Building

**MarketPulse OSINT** transforms the existing supply-chain intelligence platform into a comprehensive investment research terminal — combining alternative data (insider trades, short interest, retail sentiment), technical analysis, and financial fundamentals with the existing news/macro/conflict pipeline into a single **Alpha Score** per ticker.

## Architecture

```
                    ┌─────────────────────────────┐
                    │   Existing Pipeline (v2)     │
                    │   News → FinBERT → GNN → MC  │
                    └──────────┬──────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────┐
│           NEW OSINT LAYER    │                              │
│                              ▼                              │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Insider     │  │ Short        │  │ Retail            │  │
│  │ Trades     │  │ Interest     │  │ Sentiment         │  │
│  │ (Form 4)   │  │ (FINRA)      │  │ (Reddit/StockTwits)│  │
│  └─────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│        │                │                    │             │
│  ┌─────▼────────────────▼────────────────────▼──────────┐  │
│  │              Alpha Aggregator                        │  │
│  │  Weighted combination → Alpha Score (-10 to +10)     │  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────▼───────────────────────────────┐  │
│  │              API Layer (FastAPI)                    │  │
│  │  /api/intelligence/insider-trades                   │  │
│  │  /api/intelligence/short-interest                   │  │
│  │  /api/intelligence/retail-sentiment                 │  │
│  │  /api/intelligence/technical-analysis               │  │
│  │  /api/intelligence/fundamentals                      │  │
│  │  /api/intelligence/alpha-score                      │  │
│  └─────────────────────┬───────────────────────────────┘  │
│                        │                                   │
│  ┌─────────────────────▼───────────────────────────────┐  │
│  │  Frontend (React)                                   │  │
│  │  - New API functions in api.js                      │  │
│  │  - IntelligencePanel enhancements                   │  │
│  │  - Company Detail page (future)                      │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Implementation Order

### Phase A: Core OSINT Services (Today)

| # | File | What It Does | Data Sources | Lines |
|---|------|-------------|--------------|-------|
| 1 | `app/services/data/insider_trades.py` | Form 4 insider trading via SEC EDGAR + OpenInsider | SEC EDGAR API (free) | ~150 |
| 2 | `app/services/data/short_interest.py` | FINRA short interest + volume | FINRA CDN (free) | ~80 |
| 3 | `app/services/data/retail_sentiment.py` | Reddit + StockTwits sentiment per ticker | PRAW + StockTwits API (free) | ~120 |
| 4 | `app/services/data/technical_analysis.py` | RSI, MACD, Bollinger, SMA from yfinance | yfinance (free) | ~80 |
| 5 | `app/services/data/financial_fundamentals.py` | Income statement, balance sheet, ratios | yfinance (free) | ~100 |
| 6 | `app/services/intelligence/alpha_aggregator.py` | Combine 5+ signals → single Alpha Score | Internal | ~80 |
| 7 | Update `app/routers/intelligence.py` | 6 new API endpoints | — | ~200 |
| 8 | Update `app/config.py` | Add new config vars | — | ~20 |
| 9 | Update `requirements.txt` | Add 3 packages | — | ~5 |

### Phase B: Frontend Wiring (Today)

| # | File | What It Does |
|---|------|-------------|
| 10 | Update `frontend/src/services/api.js` | 6 new API functions |
| 11 | Update `.env.example` | Document new env vars |

### Phase C: Commit & Verify (Today)

| # | Action |
|---|--------|
| 12 | Commit all 63 untracked v2 files |
| 13 | Commit all new OSINT code |
| 14 | Verify with `git status` |

## Data Flow

```
User requests /api/intelligence/alpha-score?ticker=AAPL
  │
  ├─→ insider_trades.get_insider_activity("AAPL")
  │     └─→ SEC EDGAR / Form 4 → score (-5 to +5)
  │
  ├─→ short_interest.get_short_interest("AAPL")
  │     └─→ FINRA → score (-5 to +5)
  │
  ├─→ retail_sentiment.get_sentiment("AAPL")
  │     └─→ Reddit + StockTwits → score (-5 to +5)
  │
  ├─→ technical_analysis.get_indicators("AAPL")
  │     └─→ yfinance → RSI/MACD → score (-5 to +5)
  │
  └─→ financial_fundamentals.get_fundamentals("AAPL")
        └─→ yfinance → PE/ratios → score (-5 to +5)
           │
           ▼
     alpha_aggregator.combine({
       insider: 3.2,
       short_interest: -1.5,
       sentiment: 2.1,
       technical: 1.8,
       fundamentals: 0.5
     }) → Alpha Score: 6.1 / 10 (BULLISH)
```

## Scoring System

Each signal normalized to -5 to +5, then weighted:

| Signal | Weight | Source |
|--------|--------|--------|
| Insider Activity | 0.25 (25%) | SEC Form 4 filings |
| Short Interest | 0.15 (15%) | FINRA bi-monthly |
| Retail Sentiment | 0.15 (15%) | Reddit + StockTwits |
| Technical Analysis | 0.20 (20%) | RSI, MACD, Trends |
| Fundamentals | 0.25 (25%) | PE, Earnings, Growth |

**Final Alpha Score = -10 (Strong Sell) to +10 (Strong Buy)**

## Data Verification Strategy

| Source | Cross-Validate With | Fallback |
|--------|-------------------|----------|
| Insider Trades | SEC EDGAR (authoritative) | OpenInsider scrape |
| Short Interest | FINRA (authoritative) | yfinance estimate |
| Retail Sentiment | Average both Reddit + StockTwits | Either alone |
| Technical | All from yfinance OHLCV | Calculated locally |
| Fundamentals | yfinance (authoritative) | Calculated from price |

## Final Product

After this implementation, MarketPulse will be a **multi-signal investment OSINT terminal** that:

1. **Monitors 110+ news sources** for supply chain disruptions (existing)
2. **Tracks insider trading** via SEC Form 4 (new)
3. **Measures short interest** from FINRA (new)
4. **Analyzes retail sentiment** from Reddit + StockTwits (new)
5. **Computes technical indicators** from market data (new)
6. **Pulls financial fundamentals** from SEC XBRL (new)
7. **Combines all signals** into a single Alpha Score (new)
8. **Delivers everything** through existing API + frontend (existing)

All data sources are **100% free**. No paid subscriptions required.
