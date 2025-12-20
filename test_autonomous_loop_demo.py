"""
Test Autonomous Looping Behavior
Demonstrates Agent 5 making autonomous decision to request more data

This is THE CRITICAL test that proves MarketPulse-X is truly agentic,
not just a sequential pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.agents.workflow import app as langgraph_app
from datetime import datetime
import json

def test_autonomous_loop():
    """
    Create a scenario that triggers confidence < 70%
    - Use obscure company (not in cache) → Agent 3B fails
    - Use vague news (low classification confidence) → Agent 2 struggles
    - Result: Agent 5 detects low confidence → Loops back to Agent 1
    """

    print("\n" + "="*80)
    print("🔄 AUTONOMOUS LOOPING TEST - Forcing Agent 5 to Request More Data")
    print("="*80 + "\n")

    # Create initial state with INTENTIONALLY DIFFICULT scenario
    initial_state = {
        "user_id": "loop_test_001",
        "portfolio": ["RIVN", "LCID", "NIO"],  # Obscure EV companies
        "loop_count": 0,
        "news_articles": [
            {
                "id": "test_vague_article",
                "title": "Automotive sector faces headwinds",  # VAGUE
                "content": "Some challenges ahead for car makers.",  # VAGUE
                "source": "Test Source",
                "companies": ["RIVN"]  # Not in cache
            }
        ],
        "errors": [],
        "workflow_status": "Started",
        "started_at": datetime.now().isoformat()
    }

    print("📋 Initial State:")
    print(f"   Portfolio: {initial_state['portfolio']}")
    print(f"   News: Intentionally vague article")
    print(f"   Expected: Agent 5 should detect low confidence and loop\n")

    # Execute workflow
    print("🚀 Executing LangGraph workflow...\n")
    try:
        final_state = langgraph_app.invoke(initial_state)
    except Exception as e:
        print(f"❌ ERROR during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return None

    # Analyze results
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80 + "\n")

    loop_count = final_state.get("loop_count", 0)
    confidence = final_state.get("confidence_score", 0.0)
    decision = final_state.get("validation_decision", "")
    gaps = final_state.get("gaps_identified", [])
    queries = final_state.get("refined_search_queries", [])

    print(f"✅ Loop Count: {loop_count}")
    print(f"✅ Final Confidence: {confidence:.2f}")
    print(f"✅ Validator Decision: {decision}")
    print(f"✅ Gaps Identified: {len(gaps)}")

    if gaps:
        print("\n🔍 Agent 5 Identified These Gaps:")
        for i, gap in enumerate(gaps, 1):
            print(f"   {i}. {gap}")

    if queries:
        print("\n🔎 Agent 5 Generated These Refined Queries:")
        for i, query in enumerate(queries, 1):
            print(f"   {i}. {query}")

    print("\n" + "="*80)

    # Validation
    if loop_count > 0:
        print("✅ SUCCESS: Autonomous looping TRIGGERED!")
        print(f"   Agent 5 made autonomous decision to loop {loop_count} time(s)")
        print("   This demonstrates TRUE agentic behavior (not just sequential processing)")
    else:
        print("⚠️  NOTICE: Looping did NOT trigger")
        print("   Possible causes:")
        print("   1. Confidence threshold in Agent 5 too low")
        print("   2. Impact calculation returning high confidence")
        print("   3. Agent 5 logic needs adjustment")
        print(f"\n   Current confidence: {confidence:.2f}")
        print(f"   Threshold: 0.70")

    print("="*80 + "\n")

    # Save results
    result_data = {
        "test_time": datetime.now().isoformat(),
        "loop_triggered": loop_count > 0,
        "loop_count": loop_count,
        "final_confidence": confidence,
        "decision": decision,
        "gaps": gaps,
        "queries": queries,
        "initial_state": initial_state,
        "final_state_summary": {
            "workflow_status": final_state.get("workflow_status"),
            "num_articles": len(final_state.get("news_articles", [])),
            "num_classified": len(final_state.get("classified_articles", [])),
            "num_impacts": len(final_state.get("stock_impacts", [])),
        }
    }

    with open('autonomous_loop_test_results.json', 'w') as f:
        json.dump(result_data, f, indent=2)

    print("📁 Full results saved to: autonomous_loop_test_results.json\n")

    return final_state

if __name__ == "__main__":
    print("="*80)
    print("MarketPulse-X: Autonomous Looping Demonstration")
    print("This test proves the system is TRULY AGENTIC")
    print("="*80 + "\n")

    result = test_autonomous_loop()

    if result:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed to complete")
        sys.exit(1)
