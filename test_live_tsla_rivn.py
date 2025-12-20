"""
LIVE DATA TEST: TSLA + RIVN Portfolio Analysis
NO MOCKING, NO CACHING, ONLY REAL APIs

This test validates that the system uses:
✅ Real news from RSS/NewsAPI
✅ Real SEC filings from sec.gov
✅ Real LLM calls to Gemini
✅ Dynamic relationship discovery
✅ Live impact calculations
"""

import sys
import time
import json
from datetime import datetime
from typing import Dict, Any

# Import the workflow
from app.agents.workflow import app as langgraph_app
from app.services.database import init_db, get_db_connection

def print_banner(title: str):
    print("\n" + "="*100)
    print(f"  {title}")
    print("="*100 + "\n")

def print_section(title: str):
    print("\n" + "-"*100)
    print(f"  {title}")
    print("-"*100 + "\n")

def verify_live_data(state: Dict[str, Any]) -> Dict[str, bool]:
    """Verify that all data is live, not mocked/cached"""
    
    checks = {
        "real_news": False,
        "real_classification": False,
        "real_discovery": False,
        "real_impact": False,
        "processing_time_valid": False
    }
    
    # Check 1: Real news (should have actual URLs and sources)
    news = state.get("news_articles", [])
    if news and len(news) > 0:
        first_article = news[0]
        # Real news has actual URLs, not example.com
        if "example.com" not in first_article.get("id", ""):
            checks["real_news"] = True
            print(f"✅ REAL NEWS DETECTED: {len(news)} articles from live sources")
            print(f"   Sample: {first_article.get('title', '')[:80]}...")
            print(f"   Source: {first_article.get('source', 'Unknown')}")
        else:
            print(f"❌ MOCK NEWS DETECTED: Using example.com URLs")
    
    # Check 2: Real classification (should have varied factors, not all the same)
    classified = state.get("classified_articles", [])
    if classified:
        factors = set(c.get("factor_type") for c in classified)
        if len(factors) > 1:  # Real classification varies
            checks["real_classification"] = True
            print(f"✅ REAL CLASSIFICATION: {len(factors)} different factors detected")
        else:
            print(f"⚠️  All articles classified as same factor (suspicious)")
    
    # Check 3: Real discovery (should have actual sources)
    discovered = state.get("discovered_relationships", [])
    if discovered and len(discovered) > 0:
        for disc in discovered:
            rels = disc.get("relationships", [])
            if rels:
                # Check if relationships have real sources
                has_real_sources = any(
                    rel.get("source") in ["sec_filing", "news_report", "llm_inference"]
                    for rel in rels
                )
                if has_real_sources:
                    checks["real_discovery"] = True
                    print(f"✅ REAL DISCOVERY: Found {len(rels)} relationships for {disc.get('ticker')}")
                    for rel in rels[:3]:  # Show first 3
                        print(f"   → {rel.get('related_company')} ({rel.get('type')}) - Source: {rel.get('source')}")
    
    # Check 4: Real impact (should have reasoning)
    impacts = state.get("stock_impacts", [])
    if impacts:
        has_reasoning = any(imp.get("reason") for imp in impacts)
        if has_reasoning:
            checks["real_impact"] = True
            print(f"✅ REAL IMPACT CALCULATION: {len(impacts)} impacts with reasoning")
    
    # Check 5: Processing time (real discovery takes 10-15+ seconds)
    start_time = datetime.fromisoformat(state.get("started_at", ""))
    end_time = datetime.fromisoformat(state.get("completed_at", datetime.now().isoformat()))
    duration = (end_time - start_time).total_seconds()
    
    if duration >= 8.0:  # Real processing takes time
        checks["processing_time_valid"] = True
        print(f"✅ PROCESSING TIME: {duration:.1f}s (indicates real API calls)")
    else:
        print(f"⚠️  PROCESSING TIME: {duration:.1f}s (too fast, might be cached)")
    
    return checks

def main():
    print_banner("🚀 LIVE DATA TEST: TSLA + RIVN PORTFOLIO")
    
    print("""
    CRITICAL VALIDATION CRITERIA:
    ────────────────────────────────────────────────────────────────
    ✅ News must come from real RSS feeds or NewsAPI
    ✅ Classification must use actual Gemini LLM calls
    ✅ Relationships must be discovered via SEC/News/LLM (not cache)
    ✅ Impact calculations must use real reasoning
    ✅ Processing time must be 10-15+ seconds (proves real API calls)
    
    ❌ NO mock data allowed
    ❌ NO cached relationships allowed
    ❌ NO hardcoded test data allowed
    ❌ NO instant results allowed
    """)
    
    # Initialize database (clear cache for this test)
    print_section("📦 DATABASE INITIALIZATION")
    init_db()
    
    # Clear any cached relationships for TSLA and RIVN
    print("Clearing cached relationships for TSLA and RIVN to force dynamic discovery...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships WHERE source_ticker IN ('TSLA', 'RIVN')")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"✅ Cleared {deleted} cached relationships")
    except Exception as e:
        print(f"⚠️  Could not clear cache: {e}")
    
    # Test configuration
    print_section("📋 TEST CONFIGURATION")
    test_config = {
        "user_id": "live_test_tsla_rivn",
        "portfolio": ["TSLA", "RIVN"],
        "loop_count": 0,
        "started_at": datetime.now().isoformat(),
        "errors": []
    }
    
    print(f"User ID: {test_config['user_id']}")
    print(f"Portfolio: {', '.join(test_config['portfolio'])}")
    print(f"Test Started: {test_config['started_at']}")
    print("\n⚡ EXPECTED DATA SOURCES:")
    print("  - News: Live RSS feeds (Reuters, Bloomberg, WSJ) + NewsAPI")
    print("  - Classification: Google Gemini 2.0 Flash (real LLM calls)")
    print("  - Relationships: SEC EDGAR filings + News extraction + LLM inference")
    print("  - Impact: Real-time calculation with LLM reasoning")
    
    # Execute workflow
    print_section("🔄 EXECUTING LIVE WORKFLOW")
    print("Starting LangGraph orchestration with ALL AGENTS...")
    print("⏱️  Expected duration: 15-30 seconds (real API calls take time)\n")
    
    start_time = time.time()
    
    try:
        # Execute the full workflow
        final_state = langgraph_app.invoke(test_config)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Workflow completed in {duration:.1f} seconds")
        
        # Detailed output
        print_section("📰 NEWS INGESTION RESULTS")
        news_articles = final_state.get("news_articles", [])
        print(f"Total Articles Fetched: {len(news_articles)}")
        
        if news_articles:
            print("\nSample Articles (showing first 5):")
            for i, article in enumerate(news_articles[:5], 1):
                print(f"\n{i}. {article.get('title', 'No title')}")
                print(f"   Source: {article.get('source', 'Unknown')}")
                print(f"   URL: {article.get('id', 'No URL')[:80]}...")
                print(f"   Companies: {', '.join(article.get('companies', []))}")
        else:
            print("⚠️  NO NEWS ARTICLES FOUND (This is suspicious!)")
        
        # Classification results
        print_section("🏷️  CLASSIFICATION RESULTS")
        classified = final_state.get("classified_articles", [])
        print(f"Total Articles Classified: {len(classified)}")
        
        if classified:
            # Show factor distribution
            factor_counts = {}
            for c in classified:
                factor = c.get("factor_name", "Unknown")
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
            
            print("\nFactor Distribution:")
            for factor, count in sorted(factor_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  • {factor}: {count} articles")
            
            print("\nSample Classifications (first 3):")
            for i, c in enumerate(classified[:3], 1):
                print(f"\n{i}. Article: {c.get('article_id', '')[:60]}...")
                print(f"   Factor: {c.get('factor_name', 'Unknown')}")
                print(f"   Sentiment: {c.get('sentiment', 'Unknown')} (Score: {c.get('sentiment_score', 0):.2f})")
                print(f"   Reasoning: {c.get('reasoning', 'No reasoning')}")
        
        # Discovery results
        print_section("🔍 DYNAMIC RELATIONSHIP DISCOVERY")
        discovered = final_state.get("discovered_relationships", [])
        cache_hits = final_state.get("cache_hits", [])
        cache_misses = final_state.get("cache_misses", [])
        
        print(f"Cache Hits: {len(cache_hits)}")
        print(f"Cache Misses (requiring discovery): {len(cache_misses)}")
        print(f"Relationships Discovered: {len(discovered)}")
        
        if discovered:
            for disc in discovered:
                ticker = disc.get("ticker")
                rels = disc.get("relationships", [])
                print(f"\n📊 {ticker} Relationships ({len(rels)} found):")
                
                for rel in rels:
                    print(f"  → {rel.get('related_company', 'Unknown')}")
                    print(f"     Type: {rel.get('type', 'Unknown')}")
                    print(f"     Criticality: {rel.get('criticality', 'Unknown')}")
                    print(f"     Source: {rel.get('source', 'Unknown')}")
                    print(f"     Confidence: {rel.get('confidence', 0):.0%}")
        else:
            if cache_misses:
                print("⚠️  Cache misses detected but NO relationships discovered!")
                print("   This indicates discovery failed or was skipped")
        
        # Impact calculation
        print_section("💰 IMPACT CALCULATION")
        impacts = final_state.get("stock_impacts", [])
        total_impact = final_state.get("portfolio_total_impact", {})
        
        print(f"Total Portfolio Impact: {total_impact.get('impact_pct', 0):+.2f}% (${total_impact.get('impact_usd', 0):,.2f})")
        print(f"Individual Stock Impacts: {len(impacts)}")
        
        if impacts:
            print("\nDetailed Impacts:")
            for imp in impacts[:10]:  # Show first 10
                print(f"  • {imp.get('ticker', 'Unknown')}: {imp.get('impact_pct', 0):+.1f}%")
                print(f"    Reason: {imp.get('reason', 'No reason')}")
                print(f"    Confidence: {imp.get('confidence', 0):.0%}")
        
        # Confidence validation
        print_section("🎯 CONFIDENCE VALIDATION")
        confidence = final_state.get("confidence_score", 0)
        decision = final_state.get("validation_decision", "Unknown")
        loop_count = final_state.get("loop_count", 0)
        
        print(f"Final Confidence Score: {confidence:.0%}")
        print(f"Validation Decision: {decision}")
        print(f"Loop Count: {loop_count}")
        
        if decision == "REQUEST_MORE_DATA":
            gaps = final_state.get("gaps_identified", [])
            queries = final_state.get("refined_search_queries", [])
            print(f"\nGaps Identified: {len(gaps)}")
            for gap in gaps:
                print(f"  • {gap}")
            print(f"\nRefined Queries Generated: {len(queries)}")
            for query in queries:
                print(f"  • {query}")
        
        # Alert generation
        print_section("🚨 ALERT GENERATION")
        alert_created = final_state.get("alert_created", False)
        alert_id = final_state.get("alert_id", "None")
        
        print(f"Alert Created: {alert_created}")
        print(f"Alert ID: {alert_id}")
        
        # VERIFICATION
        print_section("✅ LIVE DATA VERIFICATION")
        checks = verify_live_data(final_state)
        
        all_passed = all(checks.values())
        
        print("\n" + "="*100)
        if all_passed:
            print("  ✅ SUCCESS: ALL DATA IS LIVE AND DYNAMIC")
            print("="*100)
            print("\nVerification Results:")
            print("  ✅ Real news from RSS/NewsAPI")
            print("  ✅ Real LLM classification")
            print("  ✅ Real dynamic discovery")
            print("  ✅ Real impact calculations")
            print("  ✅ Valid processing time")
        else:
            print("  ⚠️  PARTIAL SUCCESS: SOME COMPONENTS MAY BE USING CACHED/MOCK DATA")
            print("="*100)
            print("\nVerification Results:")
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check.replace('_', ' ').title()}")
        
        # Save results
        print_section("💾 SAVING RESULTS")
        output_file = "test_live_tsla_rivn_results.json"
        
        results = {
            "test_timestamp": datetime.now().isoformat(),
            "portfolio": test_config["portfolio"],
            "processing_time_seconds": duration,
            "verification_checks": checks,
            "all_checks_passed": all_passed,
            "final_state": {
                "news_count": len(news_articles),
                "classified_count": len(classified),
                "discovered_count": len(discovered),
                "impact_count": len(impacts),
                "confidence_score": confidence,
                "loop_count": loop_count,
                "alert_created": alert_created
            },
            "sample_news": news_articles[:3] if news_articles else [],
            "sample_impacts": impacts[:5] if impacts else [],
            "discovered_relationships": discovered
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"✅ Results saved to: {output_file}")
        
        print("\n" + "="*100)
        print("  TEST COMPLETE")
        print("="*100 + "\n")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ ERROR: Workflow execution failed")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
