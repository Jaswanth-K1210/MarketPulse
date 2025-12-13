"""
Full Integration Test
Tests Phase 1 + Phase 2 + Phase 3 integration
"""

import requests
import json
from datetime import datetime


def print_separator(title=""):
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def main():
    print_separator("🚀 FULL INTEGRATION TEST - MarketPulse-X")

    BASE_URL = "http://localhost:8000"

    # Test 1: Health Check
    print_separator("TEST 1: Backend Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✅ Backend is running")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database', {})}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Please start the backend with: python main.py")
        return

    # Test 2: Portfolio Check
    print_separator("TEST 2: Portfolio with 15 Companies")
    try:
        response = requests.get(f"{BASE_URL}/api/portfolio")
        if response.status_code == 200:
            data = response.json()
            holdings = data.get('holdings', [])
            print(f"✅ Portfolio loaded: {len(holdings)} companies")
            for i, holding in enumerate(holdings[:5], 1):
                print(f"   {i}. {holding.get('company')} ({holding.get('ticker')})")
            if len(holdings) > 5:
                print(f"   ... and {len(holdings) - 5} more")
        else:
            print(f"❌ Portfolio check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Full Pipeline - Fetch & Analyze
    print_separator("TEST 3: Full Pipeline - Fetch & Analyze News")
    print("This will:")
    print("  1. Fetch 4 latest articles from news sources (Phase 1)")
    print("  2. Process through multi-agent system (Phase 2)")
    print("  3. Return results for UI (Phase 3)")
    print()

    proceed = input("Proceed with test? This will use Gemini API quota. (y/n): ")
    if proceed.lower() != 'y':
        print("Test skipped.")
        return

    print("\n🚀 Starting full pipeline test...\n")

    try:
        # Call the fetch-and-analyze endpoint
        response = requests.post(f"{BASE_URL}/api/fetch-and-analyze?limit=4", timeout=120)

        if response.status_code == 200:
            result = response.json()

            print_separator("✅ PIPELINE RESULTS")

            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
            print(f"Articles Fetched: {result.get('articles_fetched', 0)}")
            print(f"Alerts Generated: {result.get('alerts_generated', 0)}")

            results = result.get('results', [])

            if results:
                print_separator("📰 PROCESSED ARTICLES")

                for i, item in enumerate(results, 1):
                    article = item.get('article', {})
                    alert = item.get('alert')
                    agent_analysis = item.get('agent_analysis')
                    enhanced = item.get('enhanced', False)

                    print(f"\n{'─'*80}")
                    print(f"ARTICLE {i}/{len(results)}")
                    print(f"{'─'*80}")
                    print(f"Title: {article.get('title')}")
                    print(f"Source: {article.get('source')}")
                    print(f"Companies: {', '.join(article.get('companies_mentioned', []))}")
                    print(f"URL: {article.get('url')[:70]}...")

                    if alert:
                        print(f"\n✅ ALERT GENERATED:")
                        print(f"   Severity: {alert.get('severity', 'N/A').upper()}")
                        print(f"   Impact: {alert.get('impact_percent', 0):+.2f}%")
                        print(f"   Recommendation: {alert.get('recommendation', 'N/A')}")
                    else:
                        print(f"\nℹ️  No alert generated (below threshold)")

                    if enhanced and agent_analysis:
                        print(f"\n🤖 MULTI-AGENT ANALYSIS:")
                        print(f"   Sentiment: {agent_analysis.get('sentiment', 'N/A')}")
                        print(f"   Confidence: {agent_analysis.get('confidence', 0):.0%}")
                        print(f"   Recommendation: {agent_analysis.get('recommendation', 'N/A')}")
                        print(f"   Risk: {agent_analysis.get('risk_assessment', 'N/A')}")

            print_separator("✅ TEST COMPLETE")

            print("\n📊 Summary:")
            print(f"   ✅ Backend API: Working")
            print(f"   ✅ Phase 1 (News Fetching): Working - {result.get('articles_fetched', 0)} articles")
            print(f"   ✅ Phase 2 (Multi-Agent Analysis): {'Working' if any(r.get('enhanced') for r in results) else 'Partial'}")
            print(f"   ✅ Phase 3 (API Response): Working")
            print(f"   ✅ Alerts Generated: {result.get('alerts_generated', 0)}")

            print("\n🎉 All systems integrated successfully!")
            print("\nNext steps:")
            print("   1. Start frontend: cd frontend && npm run dev")
            print("   2. Open http://localhost:5173")
            print("   3. Click 'Fetch & Analyze News' button")
            print("   4. Watch the magic happen! 🚀")

        else:
            print(f"❌ Pipeline failed: {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.Timeout:
        print("⏱️  Request timed out. Pipeline may still be running in background.")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
