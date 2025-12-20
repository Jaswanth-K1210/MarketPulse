#!/usr/bin/env python3
"""
Phase 1 Test: Core Agentic Orchestration
Tests the LangGraph multi-agent system with autonomous looping
"""

import json
from datetime import datetime
from app.agents.workflow import app
from app.agents.state import SupplyChainState

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_section(title: str):
    """Print a section divider"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80)

def test_phase1_orchestration():
    """
    Test Phase 1: Core Agentic Orchestration
    
    This demonstrates:
    1. LangGraph Infrastructure with StateGraph
    2. 6-Agent Framework (NewsMonitor, Classifier, Matcher, Discovery, Calculator, AlertGen)
    3. Agent 5 Confidence Validator (The Agentic Loop Brain)
    4. Autonomous Looping (loops back when confidence < 70%)
    """
    
    print_header("🚀 PHASE 1: CORE AGENTIC ORCHESTRATION TEST")
    
    # Initial state
    initial_state = {
        "user_id": "test_user_001",
        "portfolio": ["AAPL", "NVDA", "MSFT"],
        "loop_count": 0,
        "started_at": datetime.now().isoformat(),
        "errors": []
    }
    
    print_section("📋 INITIAL STATE")
    print(f"User ID: {initial_state['user_id']}")
    print(f"Portfolio: {', '.join(initial_state['portfolio'])}")
    print(f"Loop Count: {initial_state['loop_count']}")
    
    print_section("🎯 TESTING: Autonomous Looping with Confidence Validation")
    print("Expected behavior:")
    print("  - Loop 0: Agent 5 returns confidence=0.6 (< 70%) → REQUEST_MORE_DATA → Loop back")
    print("  - Loop 1: Agent 5 returns confidence=0.85 (> 70%) → ACCEPT → Generate alert")
    
    # Run the workflow
    print_section("🔄 EXECUTING LANGGRAPH WORKFLOW")
    
    try:
        # Invoke the compiled LangGraph app
        final_state = app.invoke(initial_state)
        
        # Display results
        print_section("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        
        print("\n📊 FINAL STATE SUMMARY:")
        print(f"  Total Loop Iterations: {final_state.get('loop_count', 0)}")
        print(f"  Final Confidence Score: {final_state.get('confidence_score', 0):.1%}")
        print(f"  Validation Decision: {final_state.get('validation_decision', 'N/A')}")
        print(f"  Alert Created: {final_state.get('alert_created', False)}")
        print(f"  Alert ID: {final_state.get('alert_id', 'N/A')}")
        
        print("\n📰 NEWS ARTICLES PROCESSED:")
        for i, article in enumerate(final_state.get('news_articles', []), 1):
            print(f"  {i}. [{article['id']}] {article['headline']}")
        
        print("\n🏷️  CLASSIFICATIONS:")
        for classification in final_state.get('classified_articles', []):
            print(f"  - {classification['article_id']}: {classification['factor_name']} "
                  f"({classification['sentiment']}, conf: {classification['confidence']:.0%})")
        
        print("\n🔗 RELATIONSHIP DISCOVERY:")
        cache_hits = final_state.get('cache_hits', [])
        cache_misses = final_state.get('cache_misses', [])
        print(f"  Cache Hits: {len(cache_hits)} ({', '.join(cache_hits) if cache_hits else 'None'})")
        print(f"  Cache Misses: {len(cache_misses)} ({', '.join(cache_misses) if cache_misses else 'None'})")
        
        discovered = final_state.get('discovered_relationships', [])
        if discovered:
            print(f"  Discovered Relationships:")
            for rel in discovered:
                print(f"    - {rel['ticker']}: {len(rel['relationships'])} relationships found")
                for r in rel['relationships']:
                    print(f"      → {r['related_company']} ({r['type']}, {r['criticality']})")
        
        print("\n💰 IMPACT ANALYSIS:")
        total_impact = final_state.get('portfolio_total_impact', {})
        print(f"  Portfolio Impact: ${total_impact.get('impact_usd', 0):,.0f} "
              f"({total_impact.get('impact_pct', 0):+.1f}%)")
        
        stock_impacts = final_state.get('stock_impacts', [])
        for stock in stock_impacts:
            print(f"    - {stock['ticker']}: {stock['impact_pct']:+.1f}%")
        
        print("\n🧠 CONFIDENCE VALIDATION (Agent 5):")
        gaps = final_state.get('gaps_identified', [])
        if gaps:
            print(f"  Gaps Identified: {', '.join(gaps)}")
        queries = final_state.get('refined_search_queries', [])
        if queries:
            print(f"  Refined Queries: {', '.join(queries)}")
        
        print("\n⏱️  WORKFLOW METADATA:")
        print(f"  Started: {final_state.get('started_at', 'N/A')}")
        print(f"  Completed: {final_state.get('completed_at', 'N/A')}")
        print(f"  Final Status: {final_state.get('workflow_status', 'N/A')}")
        
        # Phase 1 Success Criteria
        print_section("🎯 PHASE 1 SUCCESS CRITERIA CHECK")
        
        criteria = {
            "LangGraph Infrastructure": final_state.get('workflow_status') is not None,
            "6-Agent Framework": final_state.get('alert_created') == True,
            "Confidence Validator (Agent 5)": final_state.get('confidence_score') is not None,
            "Autonomous Looping": final_state.get('loop_count', 0) > 0,
            "70% Confidence Threshold": final_state.get('confidence_score', 0) >= 0.7
        }
        
        all_passed = all(criteria.values())
        
        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {criterion}")
        
        if all_passed:
            print_header("🎉 PHASE 1 TEST PASSED - ALL CRITERIA MET!")
        else:
            print_header("⚠️  PHASE 1 TEST INCOMPLETE - REVIEW FAILED CRITERIA")
        
        # Save detailed results
        print("\n💾 Saving detailed results to test_phase1_results.json...")
        with open('test_phase1_results.json', 'w') as f:
            json.dump(final_state, f, indent=2, default=str)
        print("✅ Results saved!")
        
        return final_state
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_phase1_orchestration()
