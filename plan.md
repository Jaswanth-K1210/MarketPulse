# MarketPulse — OSINT for Investors & Traders Plan

## Phase 1: Alternative Data Integration (Highest Impact)

### 1.1 Insider Trading & Institutional Holdings (2-3 days)
- **Form 4 parser**: SEC EDGAR already integrated. Add `form4` endpoint for insider transactions (buy/sell, volume, relation)
  - New: `app/services/data/insider_trades.py`
  - Modify: `app/services/sec_parser.py`, `app/services/data/__init__.py`
- **13F filings**: Institutional holdings quarter-over-quarter
  - New: `app/services/data/institutional_holdings.py`
- **API endpoint**: `GET /api/intelligence/insider-trades?ticker=AAPL` + `GET /api/intelligence/institutional-holdings?ticker=AAPL`
  - Modify: `app/routers/intelligence.py`

### 1.2 Options Flow & Short Interest (2-3 days)
- **Unusual options activity**: CBOE Livevol or PolyMarket API — detect call/put sweeps, block trades, OI spikes
  - New: `app/services/data/options_flow.py`
- **Short interest**: FINRA weekly short sale data
  - New: `app/services/data/short_interest.py`
- **API endpoint**: `GET /api/intelligence/options-flow` + `GET /api/intelligence/short-interest`
  - Modify: `app/routers/intelligence.py`

### 1.3 Retail Sentiment (2-3 days)
- **Reddit**: Pushshift API → wallstreetbets, stocks, investing → mention count + sentiment per ticker
  - New: `app/services/data/reddit_sentiment.py`
- **StockTwits**: `api.stocktwits.com` real-time message streams per ticker
  - New: `app/services/data/stocktwits_sentiment.py`
- **Twitter/X**: Hashtag volume + sentiment
  - New: `app/services/data/twitter_sentiment.py`
- **Aggregation endpoint**: `GET /api/intelligence/retail-sentiment?ticker=GME`
  - Modify: `app/routers/intelligence.py`, `app/services/intelligence/signal_aggregator.py`

### 1.4 Earnings Transcript & Regulatory (2-3 days)
- **Earnings call parser**: Transcripts from SeekingAlpha/Fool → FinBERT on forward guidance tone
  - New: `app/services/data/earnings_transcripts.py`
- **FDA / Clinical Trials**: `clinicaltrials.gov` API → pipeline drugs, phase changes
  - New: `app/services/data/fda_trials.py`
- **Patent filings**: USPTO bulk data → patent grants by assignee
  - New: `app/services/data/patents.py`
- **API endpoints**: `GET /api/intelligence/earnings` + `GET /api/intelligence/regulatory`
  - Modify: `app/routers/intelligence.py`

---

## Phase 2: Predictive Alpha Signals

### 2.1 New LangGraph Agent Nodes (3-4 days)
Add 2 new agents to existing 6-node pipeline:
```
Current:  news_monitor → classifier → matcher → impact_calc → validator → alert_gen
Proposed: news_monitor → classifier → matcher → impact_calc → alpha_score → signal_convergence → validator → alert_gen
```
- **Alpha Score Agent**: Combine FinBERT + insider activity + options flow + retail sentiment into single `alpha` float (-10 to +10)
  - New: `app/agents/alpha_scorer.py`
  - Modify: `app/agents/state.py`, `app/agents/nodes.py`, `app/agents/workflow.py`
- **Signal Convergence Agent**: Multi-source convergence detection → confidence boost
  - New: `app/agents/convergence_detector.py`
  - Modify: `app/agents/state.py`, `app/agents/nodes.py`, `app/agents/workflow.py`

### 2.2 Earnings Quality & Fraud Detection (2 days)
- **Beneish M-Score**: 8 financial ratios to detect earnings manipulation
  - New: `app/ml/m_score.py`
- **Altman Z-Score**: Bankruptcy prediction from financial statements
  - New: `app/ml/z_score.py`
- **API endpoint**: `GET /api/intelligence/fundamental-health?ticker=AAPL`
  - Modify: `app/routers/intelligence.py`

### 2.3 Macro Factor Rotation (1 day)
- **Regime → Factor mapping**: Bull→momentum, Bear→defensive, Sideways→value, Volatile→cash/hedge
  - New: `app/services/intelligence/factor_rotation.py`

---

## Phase 3: Trading Toolkit

### 3.1 Technical Analysis Engine (2 days)
- **Indicators**: RSI, MACD, Bollinger Bands, SMA/EMA crossovers, Volume Profile, VWAP
  - New: `app/services/trading/technical_analysis.py`
- **Pattern detection**: Head & Shoulders, Double Top/Bottom, Flag/Pennant (rule-based)
  - New: `app/services/trading/pattern_detection.py`
- **API endpoint**: `GET /api/intelligence/technical-analysis?ticker=AAPL&indicators=rsi,macd,bb`
  - Modify: `app/routers/intelligence.py`

### 3.2 Portfolio Optimization (1 day)
- **Black-Litterman**: Market equilibrium + Alpha Score → optimized weights
  - New: `app/services/trading/portfolio_optimizer.py`
- **Risk metrics**: VaR, CVaR, Sharpe, Sortino, Max Drawdown, Beta
  - Modify: `app/services/monte_carlo_service.py`
- **API endpoint**: `POST /api/portfolio/optimize`
  - Modify: `app/api/routes.py`

### 3.3 Backtesting Engine (2-3 days)
- **Backtester**: `vectorbt` — test "buy when Alpha Score > 7" → P&L, Sharpe, max DD
  - New: `app/services/trading/backtester.py`
- **API endpoint**: `POST /api/backtest`
  - New: `app/routers/backtest.py`

---

## Phase 4: UX & Frontend Upgrades

### 4.1 New Pages & Components (3-4 days)
- **Company Deep Dive**: Unifies all signals per ticker
  - New: `frontend/src/pages/CompanyDetail.jsx`
- **Signal Timeline**: Horizontal timeline overlaying price + insider trades + options + news
  - New: `frontend/src/components/SignalTimeline.jsx`
  - Modify: `frontend/src/pages/Dashboard.jsx`
- **Sector Heatmap**: Treemap colored by Alpha Score / CII risk
  - New: `frontend/src/components/SectorHeatmap.jsx`
  - Modify: `frontend/src/pages/Trends.jsx`
- **Portfolio Optimizer UI**: Input holdings → recommended weights as pie chart
  - New: `frontend/src/components/OptimizerPanel.jsx`
  - Modify: `frontend/src/pages/Dashboard.jsx`

### 4.2 Real-time Alert Channels (1-2 days)
- **Telegram bot**: Push high-severity alerts, insider trades, alpha signals
  - New: `app/services/infrastructure/telegram_bot.py`
  - Modify: `app/services/background_scheduler.py`

### 4.3 PDF Dossier Reports (1-2 days)
- **Python-side PDF**: Generate "OSINT Dossier for $TSLA" with all signals, risk score, supply chain
  - New: `app/services/infrastructure/report_generator.py`
- **API endpoint**: `POST /api/reports/generate-dossier?ticker=TSLA`
  - Modify: `app/api/routes.py`

---

## Phase 5: Data Quality & International Coverage

### 5.1 International Markets (2-3 days)
- Add BSE/NSE (`.NS`), LSE (`.L`), ASX (`.AX`), HKEX (`.HK`), TSE (`.T`), TSX (`.TO`)
  - Modify: `app/services/data/macro_economic.py`

### 5.2 Corporate Actions Calendar (1 day)
- Dividends, splits, M&A from Yahoo Finance calendar
  - New: `app/services/data/corporate_actions.py`

### 5.3 Bond & FX Markets (1 day)
- Yield curve spreads, credit spreads (LQD, HYG, EMB), major FX pairs
  - Modify: `app/services/data/macro_economic.py`

---

## Phase 6: Infrastructure & AI Polish

### 6.1 Data Agent for Queries (1-2 days)
- Chat endpoint for natural language: "What is sentiment and insider activity for NVDA?"
  - Modify: `app/agents/researcher_agent.py`
  - New: `app/routers/chat.py`

### 6.2 Agent Memory & Personalization (1 day)
- User signal preferences in MongoDB user_profile
  - Modify: `app/db/user_profile.py`

### 6.3 Caching & Performance (1 day)
- Redis for new OSINT data with appropriate TTLs
  - Modify: `app/services/infrastructure/cache_manager.py`

---

## Effort Summary

| Phase | Effort | Impact |
|-------|--------|--------|
| 1. Alternative Data | 10-14 days | 🔥🔥🔥🔥🔥 |
| 2. Alpha Signals | 5-7 days | 🔥🔥🔥🔥 |
| 3. Trading Toolkit | 5-6 days | 🔥🔥🔥🔥 |
| 4. UX & Frontend | 6-8 days | 🔥🔥🔥🔥 |
| 5. International | 4-5 days | 🔥🔥🔥 |
| 6. Infrastructure | 3-4 days | 🔥🔥🔥 |
| **Total** | **~35-45 days** | |

### Quick Wins (< 2 days each)
1. **Insider Trading** — SEC already wired, just add Form 4 parsing
2. **Earnings Calendar** — scrape Yahoo Finance
3. **Telegram Bot** — push alerts without frontend changes
4. **Reddit Sentiment** — Pushshift is free, WSB signal
5. **Technical Analysis** — `pandas-ta` one-liners
