# MarketPulse OSINT — Free Data Sources, Tools & Implementation Guide

## Executive Summary

MarketPulse already has **137+ data sources** (all free). This document identifies:
1. What's missing (data gaps)
2. Free sources to fill them (43+ additional providers)
3. GitHub repos that can be directly integrated
4. Data verification strategies

---

## 1. Current State (Already Have)

| Category | Sources | Free? |
|----------|---------|-------|
| RSS News Feeds | 110 (Reuters, Bloomberg, FT, WSJ, CNBC, etc.) | ✅ All free |
| Commercial News APIs | 5 (NewsAPI, NewsData.io, Finnhub, GNews, MediaStack) | ✅ Free tiers |
| Macro (FRED) | 15 economic series | ✅ Free key |
| Markets (yfinance) | 8 commodities, 11 ETFs, 5 indices | ✅ Free |
| Crypto (CoinGecko) | BTC, ETH, SOL | ✅ Free |
| Conflict (ACLED/UCDP/GDELT) | 3 conflict sources | ✅ Free |
| Stock Prices (Alpaca) | Real-time IEX feed | ✅ Free |
| SEC EDGAR | 10-K, 10-Q, 8-K filings | ✅ Free |
| ML Models | FinBERT, HMM Regime Detector | ✅ Free |
| LLM Providers | Groq, OpenRouter, Gemini, Ollama | ✅ Free tiers |
| Databases | SQLite, MongoDB, Redis, Upstash | ✅ Free tiers |

---

## 2. Critical Data Gaps (What's Missing)

### Gap 1: Insider Trading (Form 4, 13D, 13F)
**Why**: Insider buys/sells predict 5-10% alpha over 3-6 months (academic research).
**Current**: SEC parser only handles 10-K, not Form 4/13F.

### Gap 2: Short Interest & Borrow Rate
**Why**: Short squeeze detection, institutional positioning.
**Current**: None.

### Gap 3: Options Flow / Unusual Activity
**Why**: Leading indicator for institutional positioning.
**Current**: None.

### Gap 4: Retail Sentiment (Reddit, StockTwits)
**Why**: WSB sentiment drives meme stocks, contrary indicator for professionals.
**Current**: Only Reddit RSS headlines (no sentiment).

### Gap 5: Institutional Holdings (13F)
**Why**: Track what Buffett, Ackman, Cathie Wood are buying/selling.
**Current**: None.

### Gap 6: Earnings Transcripts & Guidance
**Why**: Forward guidance tone predicts post-earnings drift.
**Current**: None.

### Gap 7: Technical Analysis
**Why**: Traders need RSI, MACD, Bollinger for execution.
**Current**: None (only fundamental).

### Gap 8: Financial Fundamentals (XBRL)
**Why**: Current SEC parser doesn't do structured XBRL (only narrative text).
**Current**: Text-only SEC parsing via Gemini.

### Gap 9: Corporate Actions Calendar
**Why**: Dividends, splits, earnings dates are essential for event-driven trading.
**Current**: None.

### Gap 10: Bond Markets & Yield Curves
**Why**: 2-10 spread inversion predicts recessions.
**Current**: Only raw FRED rates, no spread calculations.

---

## 3. Free Data Sources to Fill the Gaps

### 3.1 Insider Trading (Free)

| Source | URL | Key Needed | Rate Limit | Data |
|--------|-----|-----------|------------|------|
| **OpenInsider** | openinsider.com | No | Polite scraping | Form 4 filings, insider buys/sells |
| **SEC EDGAR Form 4** | data.sec.gov/submissions/CIK... | No | 10 req/sec | Raw Form 4 XML/JSON |
| **sec-edgar-downloader** | pypi.org/project/sec-edgar-downloader/ | No | 1 req/sec | Bulk Form 4, 13F, 13D |
| **CapitalTrades** | capitoltrades.com | No | Polite scraping | Congressional STOCK Act trades |
| **TrumpTracker** | trumptracker.com | No | Polite scraping | Executive branch OGE filings |
| **UnusualWhales** | unusualwhales.com | No | Polite scraping | Options flow + insider cross-ref |
| **FinancialModelingPrep** | financialmodelingprep.com | Free key | 250 req/day | Form 4, 13F, analyst estimates, insider trades |
| **BusinessQuant** | businessquant.com | Free key | 100 req/min | Insider transactions, 13F, financial statements |
| **SecuritiesDB** | securitiesdb.com | No | 100 req/min | Insider flow, Altman Z, Piotroski, M-Score |
| **Valyu API** | valyu.ai | Free tier | Unknown | SEC search (13F, 13D/G, Form 4 via AI) |

### 3.2 Short Interest & Borrow (Free)

| Source | URL | Key Needed | Rate Limit |
|--------|-----|-----------|------------|
| **FINRA Short Interest** | finra.org (bi-monthly) | No | Free |
| **FINRA Daily Short Volume** | finra.org (Reg SHO) | No | Free |
| **SEC Failures-to-Deliver** | sec.gov/data | No | Free |
| **yfinance** | Via `yfinance` library | No | Unlimited |
| **FinancialModelingPrep** | financialmodelingprep.com | Free key | 250 req/day |

### 3.3 Options Flow (Free)

| Source | URL | Key Needed | Rate Limit |
|--------|-----|-----------|------------|
| **CBOE DataShop** | datashop.cboe.com | Free | Historical only |
| **yfinance options** | Via `yfinance` library | No | Rate-limited |
| **Tradier** | tradier.com | Free dev account | 60 req/min |
| **UnusualWhales** | unusualwhales.com | No | Polite scraping |

### 3.4 Retail Sentiment (Free)

| Source | URL | Key Needed | Rate Limit |
|--------|-----|-----------|------------|
| **Reddit (PRAW)** | praw.readthedocs.io | Free API key | 60 req/min |
| **StockTwits API** | api.stocktwits.com | No | 200 req/hr |
| **GDELT** | gdeltproject.org | No | Unlimited |
| **pytrends** | Google Trends | No | Rate-limited |
| **CNN Fear & Greed** | cnn.com/markets/fear-and-greed | No | Unlimited |
| **AAII Sentiment Survey** | via FRED (AAIISEN) | FRED key | Weekly |
| **Polymarket** | polymarket.com | No | Unlimited (prediction markets) |

### 3.5 Financial Fundamentals & XBRL (Free)

| Source | URL | Key Needed | Rate Limit |
|--------|-----|-----------|------------|
| **edgartools** | github.com/dgunning/edgartools | No | 10 req/sec |
| **sec-edgar-downloader** | pypi.org/project/sec-edgar-downloader/ | No | 1 req/sec |
| **SEC XBRL API** | data.sec.gov/api/xbrl/companyfacts | No | 10 req/sec |
| **SimFin** | simfin.com | Free key | 2000 req/day |
| **FinancialModelingPrep** | financialmodelingprep.com | Free key | 250 req/day |
| **BusinessQuant** | businessquant.com | Free key | 100 req/min |
| **SecuritiesDB** | securitiesdb.com | No | 100 req/min |
| **OpenBB** | github.com/OpenBB-finance/OpenBB | Free | Unlimited local |

### 3.6 Technical Analysis (Free)

| Source | URL | Key Needed | Notes |
|--------|-----|-----------|-------|
| **TA-Lib** | github.com/TA-Lib/ta-lib-python | No | 150+ indicators |
| **pandas-ta** | github.com/twopirllc/pandas-ta | No | 130+ indicators |
| **finta** | github.com/peerchemist/finta | No | 60+ indicators |
| **yfinance** | Via `yfinance` library | No | OHLCV data for indicators |

### 3.7 Earnings & Corporate Actions (Free)

| Source | URL | Key Needed | Data |
|--------|-----|-----------|------|
| **Yahoo Finance Calendar** | finance.yahoo.com/calendar | No | Earnings dates, splits, dividends |
| **SeekingAlpha RSS** | seekingalpha.com | No | Earnings transcripts |
| **NasdaqTrader** | nasdaqtrader.com | No | Corporate actions |
| **FinancialModelingPrep** | financialmodelingprep.com | Free key | Earnings calendar, transcripts |

### 3.8 Patents & FDA (Free)

| Source | URL | Key Needed | Data |
|--------|-----|-----------|------|
| **USPTO** | developer.uspto.gov | Free key | Patent grants, applications |
| **ClinicalTrials.gov** | clinicaltrials.gov/api | No | Drug trials, phases, results |
| **openFDA** | open.fda.gov | No | FDA approvals, adverse events |
| **Orange Book** | FDA | No | Patent exclusivity data |

---

## 4. GitHub Repos to Integrate (Ranked by Impact)

### Tier 1: Direct Additions (Copy Code)

| Repo | Stars | What it does | Integration |
|------|-------|-------------|-------------|
| **[OpenInsider-MCP](https://github.com/btopn/openinsider-mcp)** | 94 | 16 tools: Form 4, short interest, SEC filings, Yahoo quotes — all free | Port Python logic directly into `app/services/data/insider_trades.py`. The scraper + parser is ~300 lines. |
| **[finverse](https://github.com/Nityahapani/finverse)** | 7 | DCF, LBO, options pricing, GARCH, credit risk, Beneish M-Score, portfolio optimization — 58 modules | Extract DCF, M-Score, Black-Litterman into `app/ml/`. They're pure math — no API keys. |
| **[alphasig](https://github.com/sushaan-k/alphasig)** | 2 | Causal signal extraction from SEC filings: supply chain graph, risk diffs, M&A detection | Import the risk differ engine into `app/services/intelligence/`. LLM-powered 10-K diffing. |
| **[InsiderTrader](https://github.com/tuhinmallick/InsiderTrader)** | 51 | ML-based insider trading detection from price/volume patterns | Add anomaly detection to `app/ml/`. Works on price data only (no API needed). |
| **[Feather Data Fetcher](https://github.com/markzephyr/feather-data-fetcher)** | 0 | Production-grade data ingestion with retry logic, rate-limit handling, whale tracking | Use the parallel fetch + retry patterns to harden your existing scrapers. MIT license. |

### Tier 2: Libraries to Install (pip)

| Repo/Library | pip Install | What it adds |
|-------------|-------------|-------------|
| **[OpenBB](https://github.com/OpenBB-finance/OpenBB)** | `pip install openbb` | 100+ financial data providers (stocks, options, crypto, macro, fixed income) in one SDK. 68K stars. |
| **[edgartools](https://github.com/dgunning/edgartools)** | `pip install edgar-tools` | SEC filings as Python objects. 20+ form types (10-K, 13F, Form 4). MCP server included. |
| **[sec-edgar-downloader](https://github.com/jadchaar/sec-edgar-downloader)** | `pip install sec-edgar-downloader` | Bulk SEC filing downloader. Better than your current manual SEC parser. |
| **[Parsimony](https://github.com/ockham-sh/parsimony)** | `pip install parsimony-core` | Typed connectors for FRED, SDMX (macro data). Agent-friendly. |
| **[FinPipe](https://github.com/MwkosP/Finpipe)** | `pip install finpipe` | 43 providers across technicals, fundamentals, macro, derivatives, sentiment. All free tiers. |
| **[pandas-ta](https://github.com/twopirllc/pandas-ta)** | `pip install pandas-ta` | 130+ technical indicators. One-liner RSI/MACD/Bollinger. Already partially used. |

### Tier 3: Reference Architectures

| Project | Stars | What to learn |
|---------|-------|-------------|
| **[OpenWhales](https://github.com/unicodeveloper/openwhales)** | New | Full 13F + Form 4 AI analysis platform. How they structure SEC data → AI narratives. Frontend patterns for "smart money" dashboards. |
| **[Catalyst-Detector](https://github.com/Harsh-Daga/Catalyst-Detector)** | New | Multi-LLM pipeline for detecting investment catalysts from SEC filings, earnings calls, press releases. 10+ data sources. Architecture directly transferable. |
| **[OpenQuant](https://github.com/mitchellbernstein/openquant)** | New | AI agents + risk engine + insider monitor + backtesting. All free data (yfinance + SEC). Compare to MarketPulse's agent architecture. |
| **[Alt Data Alpha Engine](https://github.com/Vansh-Coder/alt-data-alpha-engine)** | New | End-to-end: Yahoo + Reddit + SEC → sentiment → signals → backtesting → Streamlit dashboard. Good pipeline template. |
| **[Trading Agents Swarm](https://github.com/visionKinger/trading-agents-swarm)** | New | Multi-agent debate system (bull vs bear). Can add as new LangGraph pattern to your workflow. |
| **[Insider-Signal](https://github.com/karanhumber007-ctrl/insider-signal)** | 1 | 4-tier insider trading intelligence CLI (Congress, Cabinet, Corporate). Multi-source scoring + convergence detection. Directly implementable. |
| **[TerraFin](https://github.com/KiUngSong/TerraFin)** | New | Agent-ready financial research toolkit. DCF, SEC filings, sentiment, guru portfolios. |
| **[Agentic Investing Framework](https://github.com/Abelian-Analysis/Agentic-Investing-Framework)** | New | 60+ MCP tools, 6 autonomous workflows. Bull vs Bear debate, Monte Carlo DCF, pharma pipeline analysis. Reference for agent orchestration. |

---

## 5. Data Verification Strategy

Getting free data is easy. Getting *correct* data requires these strategies:

### 5.1 Cross-Source Validation

| Signal | Validate Against | Method |
|--------|-----------------|--------|
| Stock Price | yfinance ↔ Alpaca ↔ Finnhub | If 2 of 3 agree, trust. Flag if >1% divergence. |
| Insider Trade | OpenInsider ↔ SEC EDGAR direct ↔ FinancialModelingPrep | If sources disagree, use SEC EDGAR as ground truth (it's the legal filing) |
| Sentiment | FinBERT ↔ FinPipe sentiment ↔ GDELT tone | Average scores; flag if opposite directions |
| Macro Data | FRED ↔ SimFin ↔ BusinessQuant | FRED is authoritative for US macro |
| SEC Filings | SEC EDGAR (always canonical) | All other sources derive from this |

### 5.2 Staleness Detection

- **Market data**: Reject if >15 minutes stale (for real-time) or >24h (for EOD)
- **Insider trades**: SEC requires filing within 2 business days — flag if delay >5 days
- **SEC filings**: Direct EDGAR query for latest CIK filings; compare with cached data
- **News**: Reject articles with no date, or date >7 days old (unless in historical analysis)

### 5.3 Anomaly Detection

- **Price jumps**: Flag >10% moves without news/article correlation
- **Sentiment spikes**: Flag sudden sentiment changes >3σ from 30-day rolling mean
- **Insider clusters**: Flag >3 insiders trading same direction in 1 week (significant)
- **Volume anomalies**: Compare current volume to 20-day average; flag >3x

### 5.4 Free Data Reliability Rankings

| Tier | Sources | Reliability | Update Frequency |
|------|---------|------------|------------------|
| **Gold** | SEC EDGAR direct, FINRA, FRED, UCDP | 100% (regulatory filings) | Minutes to days |
| **Silver** | OpenInsider, yfinance, Alpaca IEX, ACLED | 95-99% | 15 min to 1 day |
| **Bronze** | StockTwits, Reddit (PRAW), Free-tier APIs | 80-95% | Real-time to hours |
| **Watch** | Web scraping (no API), free-tier with tight rate limits | Variable | Unreliable |

### 5.5 Graceful Degradation

Every new data source should follow MarketPulse's existing pattern:

```
Primary source → Cache → Stale cache fallback → Keyword/rule fallback → Graceful null
```

---

## 6. Implementation Priority Matrix

| Feature | Effort | Alpha Impact | Free Data Ready? | Dependencies |
|---------|--------|-------------|-----------------|-------------|
| **Insider Trading (Form 4)** | 2 days | 🔥🔥🔥🔥🔥 | ✅ OpenInsider + SEC + FMP | None — standalone service |
| **Short Interest** | 1 day | 🔥🔥🔥🔥 | ✅ FINRA + yfinance | None |
| **Financial Fundamentals (XBRL)** | 3 days | 🔥🔥🔥🔥 | ✅ edgartools + SEC XBRL API | Install edgar-tools |
| **Reddit Sentiment** | 1 day | 🔥🔥🔥 | ✅ PRAW | Create Reddit app |
| **Technical Analysis** | 2 days | 🔥🔥🔥🔥 | ✅ pandas-ta (already in reqs?) | None — pure math |
| **Options Flow** | 2 days | 🔥🔥🔥🔥 | ✅ Tradier + yfinance | Tradier free account |
| **Earnings Transcript Analysis** | 2 days | 🔥🔥🔥🔥 | ✅ SeekingAlpha + FinBERT | None |
| **Beneish M-Score / Altman Z** | 1 day | 🔥🔥🔥 | ✅ finverse (pure math) | None |
| **Congressional Trading** | 1 day | 🔥🔥🔥 | ✅ CapitalTrades + TrumpTracker | None |
| **Patents / FDA** | 2 days | 🔥🔥 | ✅ USPTO + ClinicalTrials.gov | Free API keys |
| **13F Institutional Holdings** | 2 days | 🔥🔥🔥🔥 | ✅ SEC EDGAR + edgartools | edgar-tools |
| **Portfolio Optimization** | 1 day | 🔥🔥🔥 | ✅ PyPortfolioOpt (already in reqs) | None |
| **Backtesting Engine** | 2 days | 🔥🔥🔥 | ✅ vectorbt or backtrader | pip install |
| **Polymarket Integration** | 0.5 day | 🔥🔥 | ✅ Polymarket API | None |

---

## 7. Recommended Architecture Additions

### New Service Files

```
app/services/data/
├── insider_trades.py        ← Form 4 from OpenInsider + SEC EDGAR
├── short_interest.py        ← FINRA short interest + volume
├── options_flow.py          ← Unusual options activity 
├── retail_sentiment.py      ← Reddit + StockTwits aggregation
├── congressional_trades.py  ← STOCK Act + OGE filings
├── financial_fundamentals.py ← XBRL via edgartools
├── technical_analysis.py    ← pandas-ta indicators
── patents.py                ← USPTO
├── fda_trials.py            ← ClinicalTrials.gov + openFDA
├── corporate_actions.py     ← Earnings calendar, dividends, splits
├── institutional_holdings.py ← 13F filings

app/ml/
├── m_score.py               ← Beneish M-Score
├── z_score.py               ← Altman Z-Score  
├── options_pricing.py        ← Black-Scholes, Greeks

app/services/intelligence/
├── alpha_aggregator.py      ← Combine all signals → one Alpha Score per ticker
```

### Data Flow

```
Insider Trades ─┐
Short Interest ─┤
Options Flow ───┤
Retail Sentiment┤──→ Alpha Aggregator ──→ Score -10 to +10 → Portfolio Impact
Financials ─────┤
Technical ──────┘
```

---

## 8. Quick Wins (Implement This Week)

### Day 1: Insider Trading + Short Interest
```python
# app/services/data/insider_trades.py
# - Scrape OpenInsider for Form 4 (80 lines)
# - Cross-validate with SEC EDGAR direct (30 lines)
# - Score buys vs sells: officer > director, size-weighted
# Endpoint: GET /api/intelligence/insider-trades?ticker=AAPL
```

### Day 2: Technical Analysis + Financial Fundamentals
```python
# app/services/data/technical_analysis.py
# - pandas-ta on yfinance OHLCV (20 lines)
# - RSI, MACD, Bollinger, SMA crossovers
# Endpoint: GET /api/intelligence/technical-analysis?ticker=AAPL

# app/services/data/financial_fundamentals.py
# - edgartools for XBRL financials (40 lines)
# - Income statement, balance sheet, ratios
# Endpoint: GET /api/intelligence/fundamentals?ticker=AAPL
```

### Day 3: Reddit Sentiment + Alpha Score
```python
# app/services/data/retail_sentiment.py
# - PRAW for Reddit (r/wallstreetbets, r/stocks) (50 lines)
# - VADER sentiment per ticker mention
# Endpoint: GET /api/intelligence/retail-sentiment?ticker=GME

# app/services/intelligence/alpha_aggregator.py  
# - Weighted average of all signals (30 lines)
# - Insider 0.3 + Sentiment 0.2 + Technical 0.2 + Fundamentals 0.3
# Endpoint: GET /api/intelligence/alpha-score?ticker=AAPL
```

---

## 9. Key Takeaways

1. **Everything is free** — every data source listed here has a zero-cost tier. MarketPulse needs zero paid subscriptions.

2. **SEC EDGAR is the motherlode** — 10-K, 10-Q, 8-K, Form 4, 13F, 13D. All free. Add `edgartools` and you unlock structured XBRL with 3 lines of code.

3. **Fastest path to alpha** — Insider Trading + Short Interest + Technical Analysis = 3 days of work, immediate trader value.

4. **Agent pipeline is ready** — your existing 6-agent LangGraph already has the orchestration layer. Just add nodes.

5. **Data verification is built-in** — MarketPulse's 4-layer cache + circuit breaker pattern is exactly right. Apply the same pattern to new OSINT sources.
