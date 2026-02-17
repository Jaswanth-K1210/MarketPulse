#!/usr/bin/env python3
"""
COMPREHENSIVE TEST: All Phases (1, 2, 3) with DYNAMIC DATA ONLY
Validates the complete system integration with real-time data
"""

import json
from datetime import datetime
from app.agents.workflow import app
from app.agents.state import SupplyChainState

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)

def print_section(title: str):
    """Print a section divider"""
    print("\n" + "-" * 100)
    print(f"  {title}")
    print("-" * 100)

def verify_dynamic_data(state: dict) -> dict:
    """
    Verify that all data is DYNAMIC, not static
    Returns validation results
    """
    validations = {
        "phase1_orchestration": False,
        "phase2_10_factor_classification": False,
        "phase3_dynamic_discovery": False,
        "real_news_data": False,
        "real_classification": False,
        "real_sec_data": False,
        "autonomous_looping": False
    }
    
    issues = []
    
    # Check Phase 1: Real News Data
    news_articles = state.get("news_articles", [])
    if news_articles:
        # Check if news has real sources and not hardcoded content
        first_article = news_articles[0]
        if first_article.get("source") in ["Reuters", "Bloomberg", "Finnhub", "Google News RSS"]:
            validations["real_news_data"] = True
        else:
            issues.append("News articles don't have real sources")
            
        # Check for actual content (not "Detailed summary...")
        if len(first_article.get("content", "")) > 100:
            validations["real_news_data"] = validations["real_news_data"] and True
        else:
            issues.append("News content appears to be mocked/minimal")
    else:
        issues.append("No news articles found")
    
    # Check Phase 2: Real 10-Factor Classification
    classified = state.get("classified_articles", [])
    if classified:
        first_class = classified[0]
        # Check if we have proper factor classification (not just hardcoded factor_type=3)
        if "factor_name" in first_class and "sentiment_score" in first_class:
            validations["real_classification"] = True
            validations["phase2_10_factor_classification"] = True
        else:
            issues.append("Classification missing factor_name or sentiment_score")
        
        # Verify sentiment analysis is real (not always the same value)
        sentiments = [c.get("sentiment_score", 0) for c in classified]
        if len(set(sentiments)) > 1 or (len(sentiments) == 1 and sentiments[0] != 0):
            validations["real_classification"] = True
        else:
            issues.append("All sentiment scores are identical - likely static")
    else:
        issues.append("No classified articles found")
    
    # Check Phase 3: Dynamic Discovery
    discovered = state.get("discovered_relationships", [])
    if discovered:
        # Check if relationships have proper sources (SEC, news, LLM)
        has_sources = False
        for disc in discovered:
            for rel in disc.get("relationships", []):
                if "source" in rel and rel["source"] in ["sec_filing", "news_report", "llm_inference"]:
                    has_sources = True
                    break
        
        if has_sources:
            validations["phase3_dynamic_discovery"] = True
            validations["real_sec_data"] = True
        else:
            issues.append("Discovered relationships don't have proper sources")
    else:
        # Discovery might not run if no cache misses, that's OK
        if state.get("cache_misses"):
            issues.append("Cache misses exist but no relationships discovered")
    
    # Check Autonomous Looping
    if state.get("loop_count", 0) > 0:
        validations["autonomous_looping"] = True
    
    # Check Phase 1 Orchestration
    if state.get("workflow_status") and state.get("alert_created"):
        validations["phase1_orchestration"] = True
    
    return {
        "validations": validations,
        "issues": issues,
        "all_dynamic": len(issues) == 0 and all(validations.values())
    }

def test_all_phases_dynamic():
    """
    Test ALL phases (1, 2, 3) together with DYNAMIC data only
    """
    
    print_header("🚀 COMPREHENSIVE DYNAMIC TEST: PHASES 1, 2, 3 INTEGRATION")
    
    print("""
    This test validates:
    
    ✅ PHASE 1: Core Agentic Orchestration
       - LangGraph state management
       - 6-Agent coordination
       - Autonomous looping (confidence validation)
    
    ✅ PHASE 2: Intelligence & Analysis Engine
       - 10-Factor classification (using real Gemini AI)
       - Tiered impact logic (TIER 1/2/3)
       - Real sentiment analysis
    
    ✅ PHASE 3: Dynamic Relationship Discovery
       - SEC EDGAR integration
       - Multi-source fusion
       - Confidence boosting
       - LLM fallback
    
    ⚠️  CRITICAL: ALL DATA MUST BE DYNAMIC (No Static/Mocked Data)
    """)
    
    # Initial state
    initial_state = {
        "user_id": "integration_test_001",
        "portfolio": ["AAPL", "NVDA", "MSFT"],
        "loop_count": 0,
        "started_at": datetime.now().isoformat(),
        "errors": []
    }
    
    print_section("📋 TEST CONFIGURATION")
    print(f"User ID: {initial_state['user_id']}")
    print(f"Portfolio: {', '.join(initial_state['portfolio'])}")
    print(f"Test Started: {initial_state['started_at']}")
    print(f"\n⚡ Expected Data Sources:")
    print(f"  - News: Finnhub API, RSS Feeds (Reuters, Bloomberg)")
    print(f"  - Classification: Gemini AI 10-Factor Analysis")
    print(f"  - Relationships: SEC EDGAR + Multi-Source Fusion")
    print(f"  - Impact: Real-time calculation with TIER 1/2/3 propagation")
    
    print_section("🔄 EXECUTING INTEGRATED WORKFLOW")
    print("Starting LangGraph orchestration with all agents...")
    
    try:
        # Run the complete workflow
        final_state = app.invoke(initial_state)
        
        print_section("✅ WORKFLOW EXECUTION COMPLETED")
        
        # Validate dynamic data
        print_section("🔍 DYNAMIC DATA VALIDATION")
        validation_results = verify_dynamic_data(final_state)
        
        print("\n📊 Validation Results:")
        for check, passed in validation_results["validations"].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check.replace('_', ' ').title()}")
        
        if validation_results["issues"]:
            print("\n⚠️  Issues Found:")
            for issue in validation_results["issues"]:
                print(f"  - {issue}")
        
        # Display detailed results
        print_section("📰 PHASE 1: NEWS MONITORING (Dynamic Data)")
        news = final_state.get("news_articles", [])
        print(f"Total Articles Fetched: {len(news)}")
        for i, article in enumerate(news[:3], 1):  # Show first 3
            print(f"\n  {i}. {article.get('title', 'No title')[:80]}...")
            print(f"     Source: {article.get('source', 'Unknown')}")
            print(f"     Companies: {', '.join(article.get('companies', []))}")
            content_preview = article.get('content', '')[:150]
            print(f"     Content: {content_preview}...")
        
        print_section("🏷️  PHASE 2: 10-FACTOR CLASSIFICATION (AI Analysis)")
        classified = final_state.get("classified_articles", [])
        print(f"Total Classified: {len(classified)}")
        
        # Show factor distribution
        factor_counts = {}
        for c in classified:
            factor = c.get("factor_name", "Unknown")
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        print("\n  Factor Distribution:")
        for factor, count in sorted(factor_counts.items()):
            print(f"    - {factor}: {count} article(s)")
        
        print("\n  Detailed Classifications:")
        for i, c in enumerate(classified[:3], 1):  # Show first 3
            print(f"\n  {i}. Article: {c.get('article_id', 'Unknown')[:60]}...")
            print(f"     Factor: {c.get('factor_name', 'Unknown')}")
            print(f"     Sentiment Score: {c.get('sentiment_score', 0):.2f}")
            print(f"     Confidence: {c.get('confidence', 0):.2%}")
        
        print_section("🔗 PHASE 3: DYNAMIC RELATIONSHIP DISCOVERY")
        print(f"Cache Hits: {len(final_state.get('cache_hits', []))}")
        print(f"Cache Misses: {len(final_state.get('cache_misses', []))}")
        
        discovered = final_state.get("discovered_relationships", [])
        print(f"Relationships Discovered: {len(discovered)}")
        
        for disc in discovered:
            print(f"\n  📍 {disc['ticker']}:")
            for rel in disc.get("relationships", [])[:3]:  # Show first 3 per ticker
                print(f"     → {rel.get('related_company', 'Unknown')}")
                print(f"        Type: {rel.get('type', 'Unknown')}")
                print(f"        Source: {rel.get('source', 'Unknown')}")
                print(f"        Confidence: {rel.get('confidence', 0):.2%}")
        
        print_section("💰 IMPACT CALCULATION (Tiered Propagation)")
        impacts = final_state.get("stock_impacts", [])
        print(f"Stock Impacts Calculated: {len(impacts)}")
        
        for impact in impacts[:5]:  # Show first 5
            print(f"\n  📊 {impact.get('ticker', 'Unknown')}:")
            print(f"     Impact: {impact.get('impact_pct', 0):+.2f}%")
            print(f"     Confidence: {impact.get('confidence', 0):.2%}")
            print(f"     Reason: {impact.get('reason', 'N/A')}")
        
        total_impact = final_state.get("portfolio_total_impact", {})
        print(f"\n  💵 Portfolio Total Impact: {total_impact.get('impact_pct', 0):+.2f}%")
        
        print_section("🧠 CONFIDENCE VALIDATION & LOOPING")
        print(f"Loop Count: {final_state.get('loop_count', 0)}")
        print(f"Final Confidence: {final_state.get('confidence_score', 0):.2%}")
        print(f"Decision: {final_state.get('validation_decision', 'N/A')}")
        
        if final_state.get('gaps_identified'):
            print(f"Gaps Identified: {', '.join(final_state['gaps_identified'])}")
        if final_state.get('refined_search_queries'):
            print(f"Refined Queries: {', '.join(final_state['refined_search_queries'])}")
        
        print_section("🚨 ALERT GENERATION")
        print(f"Alert Created: {final_state.get('alert_created', False)}")
        print(f"Alert ID: {final_state.get('alert_id', 'N/A')}")
        
        # Final verdict
        print_section("🎯 FINAL VERDICT")
        
        if validation_results["all_dynamic"]:
            print("\n✅✅✅ SUCCESS: ALL PHASES WORKING WITH 100% DYNAMIC DATA ✅✅✅")
            print("\n  Phase 1: ✅ Orchestration & Looping Working")
            print("  Phase 2: ✅ AI Classification & Analysis Working")
            print("  Phase 3: ✅ Dynamic Discovery & Fusion Working")
            print("\n  🎉 The system is production-ready with real-time data!")
        else:
            print("\n⚠️  PARTIAL SUCCESS: Some Components Using Static Data")
            print("\n  Review the issues above and ensure all services are properly configured.")
            print("  Common issues:")
            print("    - API keys not set or quota exceeded (Gemini, NewsAPI, Finnhub)")
            print("    - Fallback to mock data when APIs fail")
            print("    - Network connectivity issues")
        
        # Save results
        print("\n💾 Saving comprehensive results to test_all_phases_dynamic_results.json...")
        result_data = {
            "test_timestamp": datetime.now().isoformat(),
            "validation_results": validation_results,
            "final_state": final_state,
            "test_config": initial_state
        }
        
        with open('test_all_phases_dynamic_results.json', 'w') as f:
            json.dump(result_data, f, indent=2, default=str)
        print("✅ Results saved!")
        
        return final_state, validation_results
        
    except Exception as e:
        print(f"\n❌ ERROR DURING EXECUTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    test_all_phases_dynamic()
