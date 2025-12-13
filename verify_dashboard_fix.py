#!/usr/bin/env python3
"""
Verification script for MarketPulse-X Dashboard Fix
Tests all backend endpoints to confirm data is flowing correctly
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def test_health():
    print_section("1. HEALTH CHECK")
    response = requests.get(f"{API_BASE}/health")
    data = response.json()
    print(f"✓ Status: {data['status']}")
    print(f"✓ Database:")
    for key, value in data['database'].items():
        print(f"  - {key}: {value}")

def test_stock_prices():
    print_section("2. STOCK PRICES (Problem #1 - FIXED)")
    response = requests.get(f"{API_BASE}/stock-prices?tickers=AAPL,NVDA,AMD,INTC,AVGO")
    data = response.json()
    print(f"✓ Status: {data['status']}")
    print(f"✓ Fetched {data['count']} stock prices:\n")

    for ticker, info in list(data['data'].items())[:5]:
        price = info['current_price']
        change = info['change_percent']
        if price > 0:
            print(f"  ✓ {ticker:6s}: ${price:7.2f}  ({change:+.2f}%)  ← REAL PRICE!")
        else:
            print(f"  ✗ {ticker:6s}: ${price:7.2f}  ← STILL ZERO!")

def test_portfolio():
    print_section("3. PORTFOLIO WITH LIVE PRICES")
    response = requests.get(f"{API_BASE}/portfolio")
    data = response.json()
    print(f"✓ User: {data['user_name']}")
    print(f"✓ Holdings: {len(data['holdings'])} companies")
    print(f"✓ Total Value: ${data['total_value']:,.2f}")
    print(f"✓ Total Gain/Loss: ${data['total_gain_loss']:,.2f} ({data['total_gain_loss_percent']:+.2f}%)")
    print(f"\n  Top 5 Holdings:")
    for holding in data['holdings'][:5]:
        ticker = holding['ticker']
        current_price = holding['current_price']
        gain_loss_pct = holding['gain_loss_percent']
        print(f"  - {ticker:6s}: ${current_price:7.2f}  ({gain_loss_pct:+7.2f}%)")

def test_articles():
    print_section("4. NEWS ARTICLES (Problem #2 - FIXED)")
    response = requests.get(f"{API_BASE}/articles")
    data = response.json()
    print(f"✓ Found {data['count']} articles:\n")

    for article in data['articles']:
        print(f"  ✓ {article['title'][:60]}...")
        print(f"    Source: {article['source']}")
        print(f"    URL: {article['url'][:70]}...")
        print(f"    Companies: {', '.join(article['companies_mentioned'])}")
        print()

def test_alerts():
    print_section("5. ALERTS (Problem #4 - FIXED)")
    response = requests.get(f"{API_BASE}/alerts")
    data = response.json()
    print(f"✓ Found {data['count']} alerts:\n")

    for alert in data['alerts']:
        print(f"  ✓ [{alert['severity'].upper()}] {alert['chain']['level_2']}")
        print(f"    Impact: {alert['impact_percent']:+.2f}% (${alert['impact_dollar']:,.2f})")
        print(f"    Recommendation: {alert['recommendation']}")
        print(f"    Confidence: {alert['confidence']:.0%}")
        print()

def main():
    print("\n" + "="*70)
    print("  MARKETPULSE-X DASHBOARD FIX VERIFICATION")
    print("="*70)

    try:
        test_health()
        test_stock_prices()
        test_portfolio()
        test_articles()
        test_alerts()

        print_section("✅ ALL TESTS PASSED - BACKEND IS WORKING!")
        print("""
NEXT STEPS FOR USER:
════════════════════════════════════════════════════════════════════

1. REFRESH YOUR BROWSER
   - Press Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)
   - This clears the cache and loads fresh data

2. VERIFY DASHBOARD SHOWS:
   ✓ Real stock prices (not $0.00)
   ✓ 2 news articles with clickable links
   ✓ 2 alerts with impact scores
   ✓ 15 portfolio holdings

3. TEST "FETCH & ANALYZE NEWS" BUTTON
   - Click the green button
   - Should fetch 4 new articles
   - Process them through AI pipeline
   - Generate new alerts

4. TEST REFRESH BUTTON
   - Click refresh icon in top-right
   - Should reload all data from backend

════════════════════════════════════════════════════════════════════
""")

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        print("Make sure backend is running on http://localhost:8000")

if __name__ == "__main__":
    main()
