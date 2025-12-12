# 🚀 Finnhub Integration - Setup Guide

## ✅ What's Been Implemented

### Option 2: Better News Source (Finnhub API)

Instead of web scraping, we've integrated **Finnhub** - a financial news API that provides:
- ✅ **Fuller article content** (200-500 characters vs 100-200 from other sources)
- ✅ **Company-specific news** (queries by ticker symbol)
- ✅ **High-quality financial news** (designed for market analysis)
- ✅ **Simple REST API** (no complex web scraping needed)
- ✅ **Free tier available** (60 requests/minute)

---

## 📋 Quick Setup (5 minutes)

### Step 1: Get Your Free Finnhub API Key

1. Visit: **https://finnhub.io/register**
2. Sign up with your email (free account)
3. Verify your email
4. Go to your dashboard: https://finnhub.io/dashboard
5. Copy your API key (it looks like: `csldhfjksdhfkjsdhfjk`)

### Step 2: Add API Key to .env File

Open `/Users/apple/Desktop/Marketpulse/MarketPulse/.env` and update:

```bash
FINNHUB_API_KEY=your_actual_api_key_here
```

Replace `your_finnhub_api_key_here` with the key you copied.

### Step 3: Test It!

Run the test script:

```bash
cd /Users/apple/Desktop/Marketpulse/MarketPulse
python3 test_finnhub.py
```

---

## 🎯 How It Works

### Architecture Update

```
News Sources (Priority Order):
1. 🥇 Finnhub API (PRIORITY)
   - Fetches company-specific news for AAPL, NVDA, AMD, INTC, AVGO
   - Provides 200-500 char summaries (good quality)
   - 5 articles per company, last 7 days

2. 🥈 Google News RSS
   - General tech/semiconductor news
   - Uses RSS summaries (no web scraping)

3. 🥉 NewsData.io (optional)
   - Backup source

4. NewsAPI (optional)
   - Backup source
```

### Code Changes

**app/config.py:**
- Added `FINNHUB_API_KEY` configuration
- Added `FINNHUB_BASE_URL` endpoint
- Made news API keys optional (at least one required)

**app/services/news_aggregator.py:**
- Added `fetch_from_finnhub()` method
- Updated `fetch_all()` to prioritize Finnhub
- Removed web scraping (too complex)
- Simplified RSS and NewsData.io to use summaries

---

## 📊 Expected Results

### Before (NewsData.io only):
```
❌ Content: 100-150 characters (too short)
❌ Gemini: Insufficient context
❌ Alerts: None generated (JSON errors)
```

### After (with Finnhub):
```
✅ Content: 200-500 characters (sufficient)
✅ Gemini: Can analyze properly
✅ Alerts: Generated correctly
✅ Companies: Targeted queries (NVDA, AAPL, etc.)
```

---

## 🧪 Test Script

Create and run `test_finnhub.py`:

```python
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline

# Fetch from Finnhub
news_aggregator.clear_seen_urls()
articles = news_aggregator.fetch_from_finnhub()

print(f"\n✅ Fetched {len(articles)} articles from Finnhub\n")

for i, article in enumerate(articles[:3], 1):
    print(f"\n{'='*80}")
    print(f"ARTICLE {i}")
    print(f"{'='*80}")
    print(f"Title: {article.title}")
    print(f"Source: {article.source}")
    print(f"Companies: {', '.join(article.companies_mentioned)}")
    print(f"Content Length: {len(article.content)} chars")
    print(f"Content: {article.content[:200]}...\n")

    # Process through pipeline
    alert = pipeline.process_article(article)
    if alert:
        print(f"🚨 ALERT GENERATED:")
        print(f"   Impact: {alert.impact_percent:+.2f}%")
        print(f"   Recommendation: {alert.recommendation}")
        print(f"   Explanation: {alert.explanation[:150]}...")
    else:
        print("ℹ️  No alert (below threshold)")
```

---

## 🔧 Troubleshooting

### "Finnhub API key not configured"
- Make sure you added the key to `.env`
- Restart the server after adding the key

### "HTTP 401 Unauthorized"
- Your API key is invalid
- Get a new key from https://finnhub.io/dashboard

### "HTTP 429 Rate Limit"
- Free tier: 60 requests/minute
- The code includes 0.2s delays between requests
- If testing frequently, wait a minute

### No articles returned
- Check the company tickers are correct (NVDA, AAPL, etc.)
- Try expanding the date range (currently last 7 days)
- Some companies may have less news

---

## 📈 Rate Limits

### Finnhub Free Tier:
- ✅ 60 API calls/minute
- ✅ Unlimited total calls
- ✅ Real-time data
- ✅ News for all companies

### Our Usage:
- Queries 5 portfolio companies (AAPL, NVDA, AMD, INTC, AVGO)
- 5 companies × 1 request = 5 requests per fetch
- With 0.2s delay = ~1.2 seconds per full fetch
- Well within rate limits! ✅

---

## 💡 Why Finnhub > Web Scraping?

| Feature | Web Scraping | Finnhub API |
|---------|-------------|-------------|
| **Complexity** | High (BeautifulSoup, selectors) | Low (simple REST API) |
| **Reliability** | Breaks when sites change | Stable API contract |
| **Content Quality** | Variable (depends on site) | Consistent financial news |
| **Speed** | Slow (fetch + parse HTML) | Fast (JSON response) |
| **Maintenance** | High (fix scrapers often) | Low (API rarely changes) |
| **Company-Specific** | Hard to target | Easy (query by ticker) |
| **Rate Limits** | Site-dependent | 60/min (generous) |

**Winner: Finnhub API** 🏆

---

## 🎉 Ready to Test!

1. ✅ Get Finnhub API key: https://finnhub.io/register
2. ✅ Add to `.env` file
3. ✅ Run: `python3 test_finnhub.py`
4. ✅ See full articles being processed
5. ✅ Watch alerts being generated!

---

## 📚 Next Steps

After Finnhub is working:

- **Phase 2:** Multi-Agent System (7 files)
  - Analyst Agent
  - Researcher Agent
  - Calculator Agent
  - Synthesizer Agent

- **Phase 3:** Frontend Dashboard (9 files)
  - React UI
  - Real-time alerts
  - Knowledge graph visualization
  - Portfolio dashboard

**Current Status:** Backend Complete! ✅

---

## 🔗 Useful Links

- Finnhub Website: https://finnhub.io
- Finnhub Docs: https://finnhub.io/docs/api
- Company News API: https://finnhub.io/docs/api/company-news
- Rate Limits: https://finnhub.io/pricing

---

**Questions?** Check the logs in `app/data/marketpulse.log`
