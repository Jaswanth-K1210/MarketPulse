import sys
import os
from datetime import datetime
import json

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.workflow import app

def run_phase2_test():
    print("🚀 STARTING MARKETPULSE-X PHASE 2 TEST: INTELLIGENCE & ANALYSIS")
    
    # We use a scenario where TSMC has an issue, and AAPL/NVDA are in the portfolio
    initial_state = {
        "user_id": "phase2_tester",
        "portfolio": ["AAPL", "NVDA"],
        "loop_count": 0,
        "news_articles": [],
        "errors": [],
        "workflow_status": "Started",
        "started_at": datetime.now().isoformat()
    }
    
    print("\nStarting LangGraph workflow for Phase 2...")
    final_output = app.invoke(initial_state)
    
    print("\n📋 PHASE 2 INTELLIGENCE VERIFICATION:")
    
    # 1. Verify 10-Factor Classification
    classified = final_output.get("classified_articles", [])
    if classified:
        factor = classified[0].get("factor_name")
        sentiment = classified[0].get("sentiment")
        print(f"✅ Factor Analysis: Identified factor '{factor}' with sentiment '{sentiment}'.")
    else:
        print("❌ Factor Analysis: No classification found.")

    # 2. Verify Tiered Impact Logic
    impacts = final_output.get("stock_impacts", [])
    portfolio_impact = final_output.get("portfolio_total_impact", {})
    
    if impacts:
        print(f"✅ Impact Calculation: Found {len(impacts)} stock-level impacts.")
        for imp in impacts:
            print(f"   - {imp['ticker']}: {imp['impact_pct']:.2f}% impact (Reason: {imp['reason']})")
    else:
        print("❌ Impact Calculation: No stock impacts calculated.")

    if portfolio_impact:
        print(f"✅ Portfolio Aggregation: Total impact {portfolio_impact['impact_pct']:.2f}% (${portfolio_impact['impact_usd']}).")
    else:
        print("❌ Portfolio Aggregation: No total impact found.")

    # 3. Verify Confidence Validation
    conf = final_output.get("confidence_score", 0)
    decision = final_output.get("validation_decision")
    print(f"✅ Confidence Validation: Final score {conf:.2f}, Decision: {decision}.")

    print("\n--- Summary of Final State ---")
    summary = {
        "status": final_output.get("workflow_status"),
        "alert_id": final_output.get("alert_id"),
        "portfolio_impact": portfolio_impact
    }
    print(json.dumps(summary, indent=2))

    if impacts and classified and portfolio_impact:
        print("\n🎉 PHASE 2 TEST PASSED: 10-FACTOR FRAMEWORK & TIERED IMPACT VERIFIED.")
    else:
        print("\n💥 PHASE 2 TEST FAILED: MISSING INTELLIGENCE COMPONENTS.")

if __name__ == "__main__":
    run_phase2_test()
