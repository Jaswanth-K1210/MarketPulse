#!/usr/bin/env python3
"""
Test Frontend Data Flow
Simulates what the frontend receives from the backend
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_dashboard_data():
    print("\n" + "="*80)
    print("  TESTING FRONTEND DATA FLOW")
    print("="*80)

    # Test 1: Portfolio with Live Prices
    print("\n📊 TEST 1: PORTFOLIO DATA (What Dashboard sees)")
    print("-" * 80)
    response = requests.get(f"{API_BASE}/portfolio")
    portfolio = response.json()

    print(f"✓ User: {portfolio['user_name']}")
    print(f"✓ Total Holdings: {len(portfolio['holdings'])}")
    print(f"✓ Total Value: ${portfolio['total_value']:,.2f}")
    print(f"✓ Total Gain/Loss: ${portfolio['total_gain_loss']:,.2f} ({portfolio['total_gain_loss_percent']:+.2f}%)")

    print(f"\n  First 5 Holdings (with LIVE prices):")
    for i, holding in enumerate(portfolio['holdings'][:5], 1):
        current = holding['current_price']
        purchase = holding['purchase_price']
        gain_loss_pct = holding['gain_loss_percent']
        day_change = holding.get('day_change_percent', 0)

        # Check if price is real (not $0.00)
        price_status = "✓ REAL PRICE" if current > 0 else "✗ ZERO PRICE"

        print(f"  {i}. {holding['ticker']:6s} - ${current:7.2f} (bought @ ${purchase:6.2f})")
        print(f"     Gain/Loss: {gain_loss_pct:+7.2f}%  |  Day Change: {day_change:+.2f}%  |  {price_status}")

    # Test 2: Stock Prices Endpoint
    print("\n\n💹 TEST 2: STOCK PRICES ENDPOINT")
    print("-" * 80)
    response = requests.get(f"{API_BASE}/stock-prices?tickers=AAPL,NVDA,AMD,INTC,AVGO")
    stock_data = response.json()

    print(f"✓ Status: {stock_data['status']}")
    print(f"✓ Count: {stock_data['count']} tickers")
    print(f"\n  Live Prices:")
    for ticker, data in list(stock_data['data'].items())[:5]:
        price = data['current_price']
        change = data['change_percent']
        company = data['company_name']
        status = "✓" if price > 0 else "✗"
        print(f"  {status} {ticker:6s}: ${price:7.2f}  ({change:+.2f}%)  - {company[:30]}")

    # Test 3: News Articles
    print("\n\n📰 TEST 3: NEWS ARTICLES")
    print("-" * 80)
    response = requests.get(f"{API_BASE}/articles?limit=5")
    articles_data = response.json()

    print(f"✓ Total Articles: {articles_data['count']}")
    print(f"\n  Recent Articles:")
    for i, article in enumerate(articles_data['articles'][:5], 1):
        print(f"\n  {i}. {article['title'][:70]}")
        print(f"     Source: {article['source']} | Published: {article['published_at'][:10]}")
        print(f"     URL: {article['url'][:80]}...")
        print(f"     Companies: {', '.join(article['companies_mentioned'][:3])}")

    # Test 4: Alerts
    print("\n\n🚨 TEST 4: ALERTS")
    print("-" * 80)
    response = requests.get(f"{API_BASE}/alerts?limit=5")
    alerts_data = response.json()

    print(f"✓ Total Alerts: {alerts_data['count']}")
    print(f"\n  Active Alerts:")
    for i, alert in enumerate(alerts_data['alerts'][:5], 1):
        severity = alert['severity'].upper()
        impact = alert['impact_percent']
        recommendation = alert['recommendation']

        # Color coding
        severity_icon = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(severity, '⚪')

        print(f"\n  {i}. {severity_icon} [{severity}] {alert['chain']['level_2'][:60]}")
        print(f"     Impact: {impact:+.2f}% | Recommendation: {recommendation}")
        print(f"     Confidence: {alert['confidence']:.0%}")

    # Summary
    print("\n\n" + "="*80)
    print("  ✅ FRONTEND DATA TEST SUMMARY")
    print("="*80)

    # Check for issues
    issues = []

    # Check stock prices
    zero_prices = [h for h in portfolio['holdings'] if h['current_price'] == 0]
    if zero_prices:
        issues.append(f"⚠️  {len(zero_prices)} holdings have $0.00 price")
    else:
        print("✓ All stock prices are REAL (no $0.00)")

    # Check articles
    if articles_data['count'] == 0:
        issues.append("⚠️  No news articles found")
    else:
        print(f"✓ {articles_data['count']} news articles available")

    # Check alerts
    if alerts_data['count'] == 0:
        issues.append("⚠️  No alerts found")
    else:
        print(f"✓ {alerts_data['count']} alerts available")

    # Check portfolio
    if len(portfolio['holdings']) < 15:
        issues.append(f"⚠️  Only {len(portfolio['holdings'])} holdings (expected 15)")
    else:
        print(f"✓ All 15 portfolio holdings loaded")

    if issues:
        print("\n🔧 ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n🎉 ALL TESTS PASSED - FRONTEND SHOULD DISPLAY CORRECTLY!")

    print("\n" + "="*80)
    print("  Frontend URL: http://localhost:5173")
    print("  Backend URL:  http://localhost:8000")
    print("="*80)
    print("\nNext Step: Open http://localhost:5173 in your browser")
    print("Expected: Dashboard with live prices, news, and alerts\n")

if __name__ == "__main__":
    try:
        test_dashboard_data()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend at http://localhost:8000")
        print("Make sure the backend server is running with: python3 run.py")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
